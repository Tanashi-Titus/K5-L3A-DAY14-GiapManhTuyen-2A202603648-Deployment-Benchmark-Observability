# Deployment Information — CP6

## Public URL

https://exquisite-embrace-production-d20b42aa.up.railway.app

## Platform

Railway — project `exquisite-embrace`, environment `production`.

## Current deployment status (verified 2026-11-26)

The Railway deployment is **Online** and CP6 public checks passed after fixing the Redis variable. The agent's `REDIS_URL` is built from the Redis service's private `REDISUSER`, `REDISPASSWORD`, `REDISHOST`, and `REDISPORT` variables; the credentials remain stored as Railway variable references and are not committed here.

The public smoke check was repeated on 2026-11-26: `GET /health` returned **200**, `GET /ready` returned **200**, and `POST /ask` without a key returned **401**. The authenticated `POST /ask` returned **200** on 2026-11-25 after the Redis fix. `/health` currently reports `environment: development`, which is the app's default because the Railway service does not set `ENVIRONMENT`; it does not affect readiness or the API-key check.

## Required verification after correcting the Railway variable

The checks were run on 2026-11-25. Results were **200, 200, 401, 200** in this order. A separate invalid-key check returned **401**. The API key was kept local and was not printed. To repeat, set `BASE` to the URL above and keep `AGENT_API_KEY` in a local shell variable or secret manager:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/health"
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ready"
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -d '{"question":"Hello"}'
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -H "X-API-Key: $AGENT_API_KEY" -d '{"question":"Hello"}'
```

## Platform variables

- `AGENT_API_KEY`: set in Railway service variables; keep secret.
- `REDIS_URL`: configured on the Railway agent service from private Redis service variables; do not copy the credential value into this repository.
- `PORT`: supplied by Railway and consumed by the container command.

## Screenshots

- `screenshots/dashboard.png`: Railway networking page showing the public domain and port.
- `screenshots/running.png`: Railway project view showing the agent and Redis online.
- `screenshots/test.png`: visual summary of the HTTP codes verified above. The authenticated request result is from 2026-11-25; the other three were repeated on 2026-11-26.
