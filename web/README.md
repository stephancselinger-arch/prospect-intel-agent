# prospect-intel-web

Next.js 14 frontend for the prospect-intel-agent.

```bash
cd web
npm install
npm run dev          # http://localhost:3007
```

The dev server proxies `/api/*` to the FastAPI backend (default
`http://localhost:8007`). Override with `API_BASE_URL=https://api.example.com`.

For Vercel: set `NEXT_PUBLIC_API_BASE` to the public backend URL (e.g. the
Fly/Railway deployment of the API) and remove the rewrite, or point the
rewrite at the production backend.
