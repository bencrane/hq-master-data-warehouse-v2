import modal

app = modal.App("list-gemini-models")

@app.function(secrets=[modal.Secret.from_name("gemini-secret")])
def list_models():
    import google.generativeai as genai
    import os

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    for model in genai.list_models():
        if hasattr(model, 'supported_generation_methods'):
            methods = [m for m in model.supported_generation_methods]
            if "generateContent" in methods:
                print(model.name)

@app.local_entrypoint()
def main():
    list_models.remote()
