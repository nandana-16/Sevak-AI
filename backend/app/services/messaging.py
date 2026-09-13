"""Outbound WhatsApp messages.

**The default provider is a simulation, and says so everywhere it can.**

Real delivery needs the WhatsApp Cloud API, which is free for the first 1,000
service conversations a month but requires a verified Meta Business account, a
registered sender number, and template approval for anything sent outside a
24-hour customer-initiated window. None of that is obtainable for a project at
this stage, so `MESSAGING_PROVIDER=mock` writes the message exactly as it would
be sent and marks it simulated. Nothing in this module pretends a message
reached a phone when it did not.

Swapping to real delivery is one environment variable plus credentials; the
message bodies, the queue, the scheduling and the record all stay as they are.

Three kinds of message, all triggered by things the system already decides:

* **referral** - to the family, when a visit classifies red. The body is the
  risk agent's own `what_to_tell_the_family`, which until now was generated on
  every visit and never used.
* **escalation** - to the supervising ANM, when a red flag is raised, so it
  does not sit in a dashboard nobody has opened.
* **reminder** - to the family, the day before a scheduled follow-up.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.db import (
    Message,
    MessageStatus,
    MessageType,
    Patient,
    RiskLevel,
    Visit,
    Worker,
)

log = logging.getLogger("sevakai.messaging")

MOCK_PROVIDER = "mock"
CLOUD_PROVIDER = "whatsapp_cloud"


def provider_name() -> str:
    return settings.messaging_provider


def is_simulated() -> bool:
    """True when nothing is actually being delivered. The API and the dashboard
    both surface this, so a demo can never imply real messages went out."""
    return provider_name() != CLOUD_PROVIDER or not settings.whatsapp_api_token


# ---------------------------------------------------------------------------
# Message bodies
# ---------------------------------------------------------------------------
# Written to be read aloud as much as read. Many recipients will have someone
# else in the household read the message to them, so no jargon, no links, and
# the action in the first line.

def _hindi(language: str | None) -> bool:
    return (language or "hi").startswith("hi")


def referral_body(patient: Patient, advice: str, worker: Worker, language: str) -> str:
    if _hindi(language):
        return (
            f"नमस्ते, मैं {worker.name} हूँ, आपकी आशा कार्यकर्ता।\n\n"
            f"{patient.name} की आज की जाँच में कुछ ऐसी बातें मिली हैं जिनके लिए "
            f"आज ही अस्पताल जाना ज़रूरी है।\n\n"
            f"{advice}\n\n"
            f"कोई भी सवाल हो तो मुझे इसी नंबर पर बताएँ।"
        )
    return (
        f"Hello, this is {worker.name}, your ASHA worker.\n\n"
        f"Today's check on {patient.name} found something that needs care at a "
        f"health facility today.\n\n"
        f"{advice}\n\n"
        f"Please reply on this number if you have any questions."
    )


def escalation_body(
    patient: Patient, worker: Worker, reason: str, danger_signs: list[str], language: str
) -> str:
    signs = ", ".join(danger_signs[:4])
    if _hindi(language):
        return (
            f"तत्काल ध्यान दें\n\n"
            f"मरीज़: {patient.name} ({patient.village or '-'})\n"
            f"आशा: {worker.name}\n"
            f"{('लक्षण: ' + signs) if signs else ''}\n\n"
            f"{reason}\n\n"
            f"कृपया डैशबोर्ड पर देखकर पुष्टि करें।"
        ).replace("\n\n\n", "\n\n")
    return (
        f"URGENT - high risk patient\n\n"
        f"Patient: {patient.name} ({patient.village or '-'})\n"
        f"ASHA: {worker.name}\n"
        f"{('Danger signs: ' + signs) if signs else ''}\n\n"
        f"{reason}\n\n"
        f"Please review and acknowledge on the dashboard."
    ).replace("\n\n\n", "\n\n")


def reminder_body(patient: Patient, worker: Worker, due: date, language: str) -> str:
    if _hindi(language):
        return (
            f"नमस्ते, मैं {worker.name} हूँ, आपकी आशा कार्यकर्ता।\n\n"
            f"{patient.name} की अगली जाँच {due.strftime('%d-%m-%Y')} को है। "
            f"कृपया घर पर रहें।\n\n"
            f"अगर समय बदलना हो तो बता दें।"
        )
    return (
        f"Hello, this is {worker.name}, your ASHA worker.\n\n"
        f"{patient.name}'s next check is due on {due.strftime('%d-%m-%Y')}. "
        f"Please be at home if you can.\n\n"
        f"Let me know if another day suits you better."
    )


# ---------------------------------------------------------------------------
# Queueing
# ---------------------------------------------------------------------------

def queue(
    db: Session,
    *,
    message_type: MessageType,
    to_phone: str | None,
    to_name: str,
    body: str,
    language: str,
    patient_id: str | None = None,
    visit_id: str | None = None,
    worker_id: str | None = None,
    send_after: date | None = None,
) -> Message:
    message = Message(
        message_type=message_type,
        to_phone=to_phone,
        to_name=to_name,
        body=body,
        language=language,
        patient_id=patient_id,
        visit_id=visit_id,
        worker_id=worker_id,
        send_after=send_after,
    )
    if not to_phone:
        # No number on file. Recorded, not discarded: the worker still has to
        # pass this on in person, and the dashboard shows it so somebody does.
        message.status = MessageStatus.no_contact
        message.error = "No phone number on file - deliver this in person"
    db.add(message)
    db.flush()
    return message


def queue_for_visit(
    db: Session,
    patient: Patient,
    visit: Visit,
    state: dict,
    *,
    follow_up_due: date | None = None,
    escalation_is_new: bool = False,
) -> list[Message]:
    """Everything a completed visit should send.

    `follow_up_due` is the date the scheduler actually settled on, passed in
    rather than recomputed here so the reminder can never disagree with the
    visit that was booked.

    `escalation_is_new` mirrors the one-open-escalation rule: a patient who is
    red for the third day running should not send the supervising ANM a third
    identical alert about a case she already has open.
    """
    worker = db.get(Worker, visit.worker_id)
    if worker is None:
        return []

    language = visit.language or "hi"
    created: list[Message] = []

    if visit.risk_level == RiskLevel.red:
        advice = (state.get("family_message") or visit.risk_rationale or "").strip()
        if advice:
            created.append(
                queue(
                    db,
                    message_type=MessageType.referral,
                    to_phone=patient.phone,
                    to_name=patient.name,
                    body=referral_body(patient, advice, worker, language),
                    language=language,
                    patient_id=patient.id,
                    visit_id=visit.id,
                    worker_id=worker.id,
                    send_after=date.today(),
                )
            )

        supervisor = db.get(Worker, worker.supervisor_id) if worker.supervisor_id else None
        if supervisor is not None and escalation_is_new:
            supervisor_language = supervisor.preferred_language or "hi"
            created.append(
                queue(
                    db,
                    message_type=MessageType.escalation,
                    to_phone=supervisor.phone,
                    to_name=supervisor.name,
                    body=escalation_body(
                        patient,
                        worker,
                        (visit.risk_rationale or "").strip(),
                        visit.danger_signs or [],
                        supervisor_language,
                    ),
                    language=supervisor_language,
                    patient_id=patient.id,
                    visit_id=visit.id,
                    worker_id=supervisor.id,
                    send_after=date.today(),
                )
            )

    # Reminder for the follow-up this visit booked, held until the day before.
    # A follow-up due today or tomorrow gets none: the worker has just been
    # standing in the family's house and can say it out loud.
    if follow_up_due is not None and follow_up_due > date.today() + timedelta(days=1):
        created.append(
            queue(
                db,
                message_type=MessageType.reminder,
                to_phone=patient.phone,
                to_name=patient.name,
                body=reminder_body(patient, worker, follow_up_due, language),
                language=language,
                patient_id=patient.id,
                visit_id=visit.id,
                worker_id=worker.id,
                send_after=follow_up_due - timedelta(days=1),
            )
        )

    return created


# ---------------------------------------------------------------------------
# Delivery
# ---------------------------------------------------------------------------

def dispatch_due(db: Session, worker_ids: list[str] | None = None) -> dict:
    """Send every scheduled message whose date has arrived."""
    stmt = select(Message).where(
        Message.status == MessageStatus.scheduled,
        Message.send_after <= date.today(),
    )
    if worker_ids is not None:
        stmt = stmt.where(Message.worker_id.in_(worker_ids))

    due = list(db.scalars(stmt).all())
    sent = failed = 0
    for message in due:
        if deliver(message):
            sent += 1
        else:
            failed += 1
    db.flush()
    return {"considered": len(due), "sent": sent, "failed": failed,
            "simulated": is_simulated()}


def deliver(message: Message) -> bool:
    if not message.to_phone:
        message.status = MessageStatus.no_contact
        return False

    if is_simulated():
        message.status = MessageStatus.sent
        message.sent_at = datetime.now(timezone.utc)
        message.provider = MOCK_PROVIDER
        log.info(
            "[SIMULATED WhatsApp] to %s (%s): %s",
            message.to_phone, message.to_name,
            message.body.replace("\n", " / ")[:120],
        )
        return True

    try:
        _send_via_cloud_api(message)
        message.status = MessageStatus.sent
        message.sent_at = datetime.now(timezone.utc)
        message.provider = CLOUD_PROVIDER
        return True
    except Exception as exc:
        message.status = MessageStatus.failed
        message.provider = CLOUD_PROVIDER
        message.error = str(exc)[:400]
        log.warning("WhatsApp delivery failed for %s: %s", message.id, exc)
        return False


def _send_via_cloud_api(message: Message) -> None:
    """Real delivery. Never exercised with the default configuration.

    Left in so the swap is visibly a configuration change rather than a
    rewrite - and so it is obvious exactly what the mock is standing in for.
    Note that outside a 24-hour reply window Meta only permits pre-approved
    templates, so a production version would send `type: template` here rather
    than free text.
    """
    import httpx

    url = (
        f"https://graph.facebook.com/v20.0/"
        f"{settings.whatsapp_phone_number_id}/messages"
    )
    response = httpx.post(
        url,
        headers={"Authorization": f"Bearer {settings.whatsapp_api_token}"},
        json={
            "messaging_product": "whatsapp",
            "to": message.to_phone,
            "type": "text",
            "text": {"body": message.body},
        },
        timeout=20,
    )
    response.raise_for_status()
