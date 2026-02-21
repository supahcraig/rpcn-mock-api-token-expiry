from flask import Flask, request, jsonify
import time
import secrets

app = Flask(__name__)

# In-memory token store: token -> expires_at_epoch_seconds
TOKENS = {}

DEFAULT_TTL_SECONDS = 120  # set to 300 for 5 min

def mint_token(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> dict:
    token = secrets.token_urlsafe(24)
    expires_at = time.time() + ttl_seconds
    TOKENS[token] = expires_at
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": ttl_seconds,
    }

def validate_bearer_token(auth_header: str) -> tuple[bool, str]:
    if not auth_header:
        return False, "Missing Authorization header"
    if not auth_header.lower().startswith("bearer "):
        return False, "Authorization must be Bearer <token>"
    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        return False, "Empty bearer token"

    expires_at = TOKENS.get(token)
    if not expires_at:
        return False, "Unknown token"
    if time.time() >= expires_at:
        # expired: delete it so next validation fails fast
        TOKENS.pop(token, None)
        return False, "Expired token"
    return True, token

@app.post("/token")
def token():
    # Optional: require a “client credential” so it feels realistic
    # (Redpanda Connect can send headers/body to fetch token)
    client_id = request.headers.get("X-Client-Id", "")
    client_secret = request.headers.get("X-Client-Secret", "")
    if client_id != "demo" or client_secret != "demo":
        return jsonify({"error": "invalid_client"}), 401

    ttl = request.args.get("ttl", default=DEFAULT_TTL_SECONDS, type=int)
    ttl = max(5, min(ttl, 3600))  # clamp
    return jsonify(mint_token(ttl))

@app.get("/data")
def data():
    ok, msg = validate_bearer_token(request.headers.get("Authorization", ""))
    if not ok:
        return jsonify({"error": "unauthorized", "message": msg}), 401

    # Return something "market-ish" like Coinbase, but fake.
    return jsonify({
        "symbol": "BTC-USD",
        "price": 42000.00,
        "ts": int(time.time()),
        "note": "mock endpoint protected by short-lived bearer token",
    })

@app.get("/health")
def health():
    return jsonify({"ok": True})

if __name__ == "__main__":
    # Use 0.0.0.0 so it’s reachable from containers/VMs if needed
    app.run(host="0.0.0.0", port=5000, debug=True)
