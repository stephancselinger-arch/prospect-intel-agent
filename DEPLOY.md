# Deploy

Two-piece deploy: FastAPI backend on **Fly.io** (Toronto region), Next.js frontend on **Vercel**.

End state:
- backend: `https://prospect-intel-agent.fly.dev`
- frontend: `https://prospect-intel-agent.vercel.app` (proxies `/api/*` → Fly)

Total cold-start cost: ~5 minutes the first time, then `git push` deploys both.

---

## 1. Backend → Fly.io

```bash
# install once
brew install flyctl
flyctl auth login                  # browser SSO

cd ~/repos/prospect-intel-agent

# scaffolds an app from fly.toml without deploying yet
flyctl launch --no-deploy --copy-config --name prospect-intel-agent --region yyz

# (optional) wire Claude — the mock backend works without this
flyctl secrets set ANTHROPIC_API_KEY=sk-ant-...
flyctl secrets set LLM_BACKEND=auto

flyctl deploy
flyctl status                       # should show 1 machine, https://prospect-intel-agent.fly.dev
curl https://prospect-intel-agent.fly.dev/health
```

Fly will scale to zero when idle and cold-start in ~2s on first hit — fine for a portfolio demo, not fine for production traffic.

## 2. Frontend → Vercel

```bash
npm i -g vercel
vercel login                        # browser SSO

cd ~/repos/prospect-intel-agent/web
vercel link                         # pick the project name; default settings are fine
vercel deploy --prod
```

`web/vercel.json` already points the production rewrite at the Fly backend, so you don't need any environment variables in the Vercel dashboard. If you renamed the Fly app, edit `web/vercel.json` and redeploy.

## 3. Tell GitHub about the live URL

```bash
gh repo edit stephancselinger-arch/prospect-intel-agent \
  --homepage "https://prospect-intel-agent.vercel.app"
```

That puts the demo URL in the repo sidebar — the first thing a recruiter clicks.

---

## Updating after deploy

- Backend: any push to `main` → manual `flyctl deploy` (or wire `superfly/flyctl-actions@1` in a workflow).
- Frontend: Vercel watches GitHub by default after `vercel link` — every push deploys.

## Costs

Both providers ship a hobby tier that covers a portfolio demo at $0/mo as long as traffic stays low:
- Fly: free shared-cpu-1x with 3GB persistent storage; you scale to zero so machine-hours are negligible.
- Vercel: 100 GB-hours/month free on Hobby.

Claude API calls are the only meaningful cost. With the mock backend (default), it's $0.
