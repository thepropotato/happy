import os

import httpx

BRIDGE_PORT = int(os.environ.get("WHATSAPP_BRIDGE_PORT") or 3001)
BRIDGE_BASE = f"http://127.0.0.1:{BRIDGE_PORT}"
BRIDGE_HEADERS = {"X-Bridge-Key": os.environ.get("INTERNAL_API_SECRET", "")}


def qr(name):
    # ONLY WHATSAPP IS SUPPORTED HERE.
    if name != "whatsapp":
        return {"status": "unsupported", "qr": None}

    # START MAY ALREADY BE UP OR MAY FAIL; QR CHECK DECIDES.
    try:
        httpx.post(f"{BRIDGE_BASE}/default/start", headers=BRIDGE_HEADERS, timeout=5, trust_env=False)
    except Exception:
        pass

    try:
        response = httpx.get(f"{BRIDGE_BASE}/default/qr", headers=BRIDGE_HEADERS, timeout=8, trust_env=False)
        return response.json()
    except Exception as error:
        return {"status": "offline", "qr": None, "error": str(error)[:200]}


def disconnect(name):
    if name != "whatsapp":
        return {"success": False}

    try:
        response = httpx.post(
            f"{BRIDGE_BASE}/default/disconnect",
            headers=BRIDGE_HEADERS,
            timeout=10,
            trust_env=False,
        )
        return response.json()
    except Exception as error:
        return {"success": False, "error": str(error)[:200]}
