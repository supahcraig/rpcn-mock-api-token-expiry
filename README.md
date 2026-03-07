# Mock Token API + Redpanda Connect Example

## Run Flask API

A flask app creates 2 routes, one to return mock data with a token required for authentication.  The other route is used to generate a short ttl token.   The `http_fetch` pipeline will call these two endpoints.

```bash
cd flask-api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then in a separate terminal window run the http fetch pipeline.   It will log calls/responses to the flask api.  The API requires a token, which is retrieved through the /token route and cached in an in-memory cache in the pipeline.   Whenever the token expires or the cache TTL expires, it will make another call to the token endpoint to refresh the token and continue on.

```bash
rpk connect run http_fetch.yaml
```

---

# Jittery Sensor Data + Windowed Aggregation

These pipelines are marked up to be run in BYOC, but they can be made to run self-hosted as well (left as an exercise to you, dear reader).   The `generate_jittery_messages.yaml` pipeline generates some randomized data with a randomized delay to simulate jitter in how the sensors produce their data.  It publishes to a Redpanda topic called `iot_raw`

The `consume_and_aggregate.yaml` pipeline consumes the `iot_raw` topic and holds them for up to a second and aggregates them into a json array.  This slows down the message rate to 1 msg/sec, although the message itself could have as many as 20 messages.  It will flush the batch if it gets to 20 to avoid a consumer lag flushing too many at once.
