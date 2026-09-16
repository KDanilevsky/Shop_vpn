from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Shop VPN webhook")


async def invoice_webhook(request: Request):
    """Minimal webhook endpoint compatible with the bot startup code.

    The project currently emits invoice-related PostgreSQL events and may later
    receive external payment webhooks. This endpoint accepts JSON payloads, does a
    tiny validation pass, and returns 200 so the app can import cleanly even when
    no external webhook service is configured yet.
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    invoice_id = None
    if isinstance(payload, dict):
        invoice_id = payload.get("invoice_id") or payload.get("id")

    return JSONResponse({
        "ok": True,
        "invoice_id": invoice_id,
        "received": True,
    })


app.add_api_route("/invoice", invoice_webhook, methods=["POST"])
app.add_api_route("/webhook/invoice", invoice_webhook, methods=["POST"])
app.add_api_route("/api/webhook", invoice_webhook, methods=["POST"])
