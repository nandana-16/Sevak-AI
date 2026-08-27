"""Pluggable WhatsApp delivery. Mocked by default (matches the SRS's own documented
fallback for pending Meta Business API approval) — stores/returns the drafted message
so the UI can show it, and swaps to real sending the moment WHATSAPP_PROVIDER=meta and
credentials are set."""
import httpx

from app.core.config import settings


def send_whatsapp_message(to_phone: str, content: str) -> dict:
    if settings.whatsapp_provider == "meta" and settings.whatsapp_api_token:
        url = f"https://graph.facebook.com/v20.0/{settings.whatsapp_phone_number_id}/messages"
        headers = {"Authorization": f"Bearer {settings.whatsapp_api_token}"}
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "text",
            "text": {"body": content},
        }
        with httpx.Client(timeout=10) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return {"status": "sent", "provider": "meta", "response": resp.json()}

    return {"status": "drafted", "provider": "mock", "to": to_phone, "content": content}
