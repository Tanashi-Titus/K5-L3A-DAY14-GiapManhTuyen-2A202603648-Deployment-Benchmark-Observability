# Deployment Information — CP6

## Public URL

https://exquisite-embrace-production-d20b42aa.up.railway.app

## Platform

Railway — project `exquisite-embrace`, environment `production`.

## Current deployment status (2026-11-25)

The Railway deployment is **Online** and CP6 public checks passed after fixing the Redis variable. The agent's `REDIS_URL` is built from the Redis service's private `REDISUSER`, `REDISPASSWORD`, `REDISHOST`, and `REDISPORT` variables; the credentials remain stored as Railway variable references and are not committed here.

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

Screenshots of a successful running deployment and API checks will be added after the service passes the four checks.
