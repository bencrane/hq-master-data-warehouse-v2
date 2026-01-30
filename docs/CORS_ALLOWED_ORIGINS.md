# CORS Allowed Origins

This document lists all domains/subdomains allowed to make requests to the Railway API (`api.revenueinfra.com`).

## How to Add a New Domain

Edit `hq-api/main.py` and add the domain to the `ALLOWED_ORIGINS` list. Commit and push - Railway auto-deploys.

---

## Allowed Domains

### revenueactivation.com
| Subdomain | URL | Purpose |
|-----------|-----|---------|
| root | `https://revenueactivation.com` | Marketing site |
| app | `https://app.revenueactivation.com` | Main app |
| admin | `https://admin.revenueactivation.com` | Admin panel |
| hq | `https://hq.revenueactivation.com` | HQ dashboard |
| demo | `https://demo.revenueactivation.com` | Demo environment |

### radarrevenue.com
| Subdomain | URL | Purpose |
|-----------|-----|---------|
| root | `https://radarrevenue.com` | Marketing site |
| app | `https://app.radarrevenue.com` | Main app |
| admin | `https://admin.radarrevenue.com` | Admin panel |
| hq | `https://hq.radarrevenue.com` | HQ dashboard |
| demo | `https://demo.radarrevenue.com` | Demo environment |

### opsinternal.com
| Subdomain | URL | Purpose |
|-----------|-----|---------|
| root | `https://opsinternal.com` | Internal ops |
| www | `https://www.opsinternal.com` | Internal ops |
| app | `https://app.opsinternal.com` | Internal app |
| admin | `https://admin.opsinternal.com` | Admin tools |

### Other
| URL | Purpose |
|-----|---------|
| `https://find-similar-companies-admin.vercel.app` | Similar companies admin tool (Vercel) |

### Local Development
| URL | Purpose |
|-----|---------|
| `http://localhost:3000` | Next.js dev server |
| `http://localhost:5173` | Vite dev server |

---

## Notes

- All origins must use HTTPS (except localhost)
- Wildcard subdomains are NOT supported - each must be explicitly listed
- Changes require commit + push to deploy
