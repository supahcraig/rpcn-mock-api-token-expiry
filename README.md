# Redpanda Connect Demo: Short-Lived Tokens & Message Aggregation

Two standalone demos that highlight common Redpanda Connect patterns.

---

## Demo 1 — Automatic Short-Lived Token Refresh (`http_fetch.yaml`)

**Problem:** A downstream API issues bearer tokens that expire. You don't want to fetch a new token on every request, but you also can't hold one indefinitely.

**Solution:** Use Redpanda Connect's in-memory cache as a token store. On each pipeline tick:
1. Try to read the token from cache.
2. On a cache miss (or after the TTL expires), POST to `/token` to get a fresh one, then cache it.
3. Use the token to call the protected `/data` endpoint.
4. If the API returns 401, evict the cached token immediately so the next tick re-fetches.

### Components

| File | Role |
|------|------|
| `app.py` | Mock Flask API — issues short-lived bearer tokens, exposes a protected `/data` endpoint |
| `http_fetch.yaml` | Redpanda Connect pipeline that manages the token lifecycle |

### Run it

**1. Start the mock API**

A Flask app creates 2 routes: one to return mock data (token required), and one to generate a short-TTL token. The `http_fetch` pipeline will call these two endpoints.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

The API listens on `http://localhost:5000`.
Tokens are valid for **120 seconds** by default (configurable via `DEFAULT_TTL_SECONDS` in `app.py`).

Endpoints:
- `POST /token` — requires headers `X-Client-Id: demo` and `X-Client-Secret: demo`
- `GET /data` — requires `Authorization: Bearer <token>`
- `GET /health`

**2. Run the pipeline**

```bash
rpk connect run http_fetch.yaml
```

The pipeline polls every 5 seconds and logs calls/responses to the Flask API. The API requires a token, which is retrieved through the `/token` route and cached in an in-memory cache in the pipeline. Whenever the token expires or the cache TTL expires, it will make another call to the token endpoint to refresh and continue on.

**Key config values in `http_fetch.yaml`**

| Setting | Value | What it controls |
|---------|-------|-----------------|
| `default_ttl` | `1m` | How long an idle cache entry lives |
| `ttl` (on cache set) | `30s` | How long a freshly fetched token is cached |
| `interval` (generate) | `5s` | How often the pipeline polls `/data` |

The cache TTL (30s) is intentionally shorter than the token lifetime (120s) so you can see re-fetches without waiting 2 minutes.

---

## Demo 2 — Message Aggregation to Avoid Rate Limits (`consume_and_aggregate.yaml`)

**Problem:** IoT devices produce bursty, high-frequency messages. Forwarding them one-by-one to a downstream API will hit rate limits.

**Solution:** Use Redpanda Connect's `system_window` buffer to collect messages over a 1-second tumbling window, then emit a single aggregated payload (count + array of messages). This slows the message rate to 1 msg/sec, although each message can contain up to 20 raw events. It flushes at 20 to avoid consumer lag flushing too many at once.

### Components

| File | Role |
|------|------|
| `generate_jittery_messages.yaml` | Generates fake IoT sensor events with random jitter and publishes to `iot_raw` |
| `consume_and_aggregate.yaml` | Reads `iot_raw`, windows messages into 1s buckets, writes aggregated batches to `iot_aggregated` |

### Prerequisites

You need a running Redpanda cluster with two topics: `iot_raw` and `iot_aggregated`.

**Option A — Redpanda Cloud (BYOC or Serverless)**

Set environment variables before running:
```bash
export REDPANDA_BROKERS="<your-seed-broker>:9092"
export REDPANDA_SASL_USER="<username>"
export REDPANDA_SASL_PASSWORD="<password>"
```

The pipelines use TLS + SCRAM-SHA-256, which matches Redpanda Cloud defaults.

> **Note:** The pipelines reference secrets as `${secrets.CNELSON_SASL_USER}` / `${secrets.CNELSON_SASL_PASSWORD}`.
> Replace these with your own secret names, or substitute plain env vars (`${REDPANDA_SASL_USER}`) for local testing.

**Option B — Local / self-hosted (no auth)**

Remove the `tls` and `sasl` blocks from both YAML files, then:
```bash
export REDPANDA_BROKERS="localhost:9092"
```

Create the topics:
```bash
rpk topic create iot_raw iot_aggregated
```

### Run it

In two separate terminals:

```bash
# Terminal 1 — generate bursty IoT events
rpk connect run generate_jittery_messages.yaml

# Terminal 2 — consume and aggregate into 1-second windows
rpk connect run consume_and_aggregate.yaml
```

Each message published to `iot_aggregated` looks like:
```json
{
  "ts": "2026-03-31 12:00:01",
  "count": 14,
  "messages": [ ... ]
}
```

The `count` field shows how many raw events were collapsed into that window — handy for demonstrating the aggregation effect.
