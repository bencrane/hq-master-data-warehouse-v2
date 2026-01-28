# Building MCP Servers with FastMCP + FastAPI

This guide details how to integrate the Model Context Protocol (MCP) with FastAPI applications using the `fastmcp` library. It covers two primary patterns: generating an MCP server *from* an existing FastAPI app, and mounting an MCP server *into* a FastAPI app.

## Setup & Installation

**Requirements:**
- Python 3.10+
- FastAPI
- FastMCP

**Installation:**

```bash
pip install fastmcp fastapi uvicorn
```

## Integration Patterns

### 1. Generating MCP from FastAPI (`FastMCP.from_fastapi`)

This pattern is ideal for quickly exposing an existing REST API to LLMs. FastMCP converts your FastAPI endpoints into MCP Tools (and Resources) automatically.

**Method:**
```python
mcp = FastMCP.from_fastapi(app=app)
```

**Parameters:**
- `app`: The FastAPI application instance.
- `name`: (Optional) Name of the MCP server.
- `route_maps`: (Optional) List of `RouteMap` objects to customize how endpoints are converted (e.g., GET -> Resource).
- `httpx_client_kwargs`: (Optional) Dictionary of arguments for the internal HTTP client (e.g., authentication headers).

### 2. Mounting MCP into FastAPI (`mcp.http_app`)

This pattern allows you to serve an MCP endpoint alongside your regular REST API within the same application. This is useful for "LLM-friendly" interfaces.

**Method:**
```python
mcp_app = mcp.http_app(path="/mcp")
app.mount("/mcp", mcp_app)
```

**Key Requirement:**
You must manage **lifespans**. The MCP server often requires a startup/shutdown sequence (e.g., for SSE sessions). You must pass the MCP lifespan to the parent FastAPI app.

---

## Example 1: Generating MCP from Existing API

This example converts a standard FastAPI app into an MCP server.

```python
# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastmcp import FastMCP

# --- Existing FastAPI App ---
app = FastAPI(title="E-commerce API")

class Product(BaseModel):
    name: str
    price: float

db = {}

@app.post("/products", operation_id="create_product")
def create_product(product: Product):
    """Create a new product in the catalog."""
    db[product.name] = product
    return product

@app.get("/products/{name}", operation_id="get_product")
def get_product(name: str):
    """Get product details by name."""
    if name not in db:
        raise HTTPException(status_code=404, detail="Not found")
    return db[name]

# --- MCP Generation ---
# Creates an MCP server that exposes 'create_product' and 'get_product' as tools
mcp = FastMCP.from_fastapi(app)

# Run with: fastmcp run main.py:mcp
if __name__ == "__main__":
    mcp.run()
```

---

## Example 2: Mounting MCP into FastAPI (Combined)

This example serves both a regular REST API and an MCP endpoint (`/mcp`) from the same server, handling lifespan coordination.

```python
# server.py
from fastapi import FastAPI
from fastmcp import FastMCP
from fastmcp.utilities.lifespan import combine_lifespans
from contextlib import asynccontextmanager

# 1. Define MCP Server
mcp = FastMCP("My Tools")

@mcp.tool
def calculate_roi(investment: float, return_amount: float) -> float:
    """Calculate Return on Investment percentage."""
    return ((return_amount - investment) / investment) * 100

# 2. Create MCP ASGI App
# 'path' must match the mount path below (relative to the mount point usually, but here path='/' if mounting the app itself)
# Actually, if mounting, the mcp_app usually handles the sub-path logic. 
# Best practice: use path="/" for the mcp_app and mount it at "/mcp"
mcp_app = mcp.http_app(path="/") 

# 3. Define Main App Lifespan
@asynccontextmanager
async def main_lifespan(app: FastAPI):
    print("Main app starting...")
    yield
    print("Main app shutting down...")

# 4. Create Main FastAPI App with Combined Lifespans
app = FastAPI(
    lifespan=combine_lifespans(main_lifespan, mcp_app.lifespan)
)

# 5. Mount the MCP App
app.mount("/mcp", mcp_app)

@app.get("/")
def home():
    return {"status": "online", "mcp_endpoint": "/mcp/sse"}

# Run with: uvicorn server:app --reload
```

---

## Configuration Options

### Custom Route Mapping (`RouteMap`)

By default, `from_fastapi` converts endpoints to **Tools**. You can map GET requests to **Resources** instead.

```python
from fastmcp.server.openapi import RouteMap, MCPType

mcp = FastMCP.from_fastapi(
    app=app,
    route_maps=[
        # Map all GET requests with path parameters to Resource Templates
        RouteMap(
            methods=["GET"],
            pattern=r".*\{.*\}.*",
            mcp_type=MCPType.RESOURCE_TEMPLATE
        ),
        # Map all other GET requests to Resources
        RouteMap(
            methods=["GET"],
            pattern=r".*",
            mcp_type=MCPType.RESOURCE
        )
    ]
)
```

### Authentication Headers

If your FastAPI endpoints require authentication, provide credentials via `httpx_client_kwargs`. The MCP server uses an internal HTTP client to call your endpoints.

```python
mcp = FastMCP.from_fastapi(
    app=app,
    httpx_client_kwargs={
        "headers": {
            "Authorization": "Bearer my-secret-token"
        },
        "timeout": 30.0
    }
)
```

---

## Lifespan Management

When mounting an MCP server, correct lifespan handling is critical for SSE (Server-Sent Events) and internal cleanup.

**The Issue:** FastAPI apps only support one `lifespan` handler. If you define one for your main app, it overwrites the MCP app's lifespan, breaking the MCP server.

**The Solution:** Use `combine_lifespans`.

```python
from fastmcp.utilities.lifespan import combine_lifespans

app = FastAPI(
    lifespan=combine_lifespans(my_db_lifespan, mcp_app.lifespan)
)
```

`combine_lifespans` ensures that:
1. Contexts are entered in order (1 -> 2).
2. Contexts are exited in reverse order (2 -> 1).

---

## Limitations & Gotchas

1.  **CORS Conflicts**:
    If your main FastAPI app uses `CORSMiddleware`, it might conflict with FastMCP's internal CORS handling for the `/mcp` routes.
    *   **Fix**: Do not apply global CORS middleware if mounting an OAuth-protected MCP server. Instead, use the sub-app pattern or apply CORS only to specific non-MCP routers.

2.  **Operation IDs**:
    FastMCP uses the FastAPI `operation_id` as the Tool/Resource name.
    *   **Fix**: Explicitly set `operation_id` in your FastAPI decorators to ensure clean tool names (e.g., `create_user` instead of `create_user_users_post`).
    ```python
    @app.post("/users", operation_id="create_user") # Tool name: create_user
    ```

3.  **Performance**:
    `from_fastapi` works by making internal HTTP requests to your own API.
    *   **Impact**: This adds a slight overhead compared to calling functions directly.
    *   **Recommendation**: For high-performance needs, define native FastMCP tools (`@mcp.tool`) that call your service logic directly, rather than routing through the FastAPI layer.
