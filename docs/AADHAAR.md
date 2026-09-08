# Aadhaar verification: what SevakAI does, and why

This is the part of the system most likely to be challenged, so it is worth
being precise about. The short version:

> SevakAI performs **offline Aadhaar validation with consent capture and
> irreversible masking**. It does not perform UIDAI e-KYC, and it never stores
> an Aadhaar number.

---

## Why not real UIDAI authentication?

Aadhaar authentication and e-KYC are governed by the Aadhaar (Targeted Delivery
of Financial and Other Subsidies, Benefits and Services) Act, 2016 and the
regulations under it. Access to the UIDAI authentication API is available only
to entities licensed as an **AUA** (Authentication User Agency) or **KUA**
(e-KYC User Agency), through an **ASA** (Authentication Service Agency) with a
dedicated leased line to UIDAI's data centres.

That licensing involves a formal application, security audits, and a contract
with UIDAI. There is:

- no public endpoint,
- no free tier,
- no sandbox that a student project can legitimately obtain,
- and no lawful way to route around it.

Any library, website, or "Aadhaar verification API" offering this without a
licence is either reselling a licensed entity's access (which shifts the
compliance question rather than answering it) or scraping, which is a
prohibited use.

So the honest engineering answer is not to fake a UIDAI call. It is to do the
parts that **can** be done correctly offline, and to build the interface so a
licensed integration drops in later without changing anything else.

---

## What the app actually does

### 1. Structural validation

An Aadhaar number is 12 digits and never begins with 0 or 1 — those ranges are
reserved and UIDAI does not issue them. Repeated-digit numbers (`999999999999`)
are rejected as obviously not real.

### 2. Verhoeff checksum

The last digit of every Aadhaar number is a **Verhoeff check digit** — the same
algorithm UIDAI uses. Verhoeff is a dihedral-group (D₅) checksum, chosen
because unlike a simple modulus it catches **all** single-digit errors and
**all** adjacent transpositions — the two mistakes a human actually makes when
copying a number off a card.

The implementation is in [`backend/app/core/aadhaar.py`](../backend/app/core/aadhaar.py).

This is a genuine mathematical check, not a formality. A mistyped digit fails
it. It cannot tell you the number belongs to the person in front of you — only
UIDAI can do that — but it eliminates the large majority of real-world data
entry errors, which is most of the day-to-day value.

```
2341 1610 8454   ->  valid   (checksum passes)
2341 1610 8455   ->  invalid (single digit changed)
1234 5678 9012   ->  invalid (starts with 1)
9999 9999 9999   ->  invalid (not a plausible number)
```

### 3. Explicit consent

Registration is **refused** if an Aadhaar number is supplied without the
consent checkbox being ticked (`400 Bad Request`). Consent is recorded on the
patient record with a timestamp. Section 7 of the Aadhaar Act requires informed
consent before collection; recording it is not optional, and the app treats it
as a hard gate rather than a formality.

### 4. Duplicate detection without storage

Before registering, the app checks whether this Aadhaar is already on file.
It does this by comparing **salted HMAC-SHA256 hashes**, not numbers:

```python
hmac.new(AADHAAR_HASH_SALT, digits, hashlib.sha256).hexdigest()
```

The hash is one-way. It permits exactly one operation — "have I seen this
number before?" — and nothing else. The salt lives in `.env` and is generated
per deployment, so hashes are not portable between installations and a stolen
database cannot be attacked with a precomputed rainbow table of all ~10¹²
possible Aadhaar numbers.

### 5. What is stored

| Stored | Not stored |
|---|---|
| Salted HMAC-SHA256 hash | The Aadhaar number |
| Last 4 digits | The first 8 digits |
| Consent flag + timestamp | Any biometric or demographic e-KYC data |
| Verification method (`offline_verhoeff`) | Any photograph of the card |

The profile screen shows `XXXX XXXX 4312` — the masked form UIDAI itself
recommends, enough for a worker to confirm with the patient that they are
looking at the right record, and useless to anyone who steals the database.

---

## Where this sits legally and ethically

This design is deliberately **more conservative** than many production Indian
health apps, which store full Aadhaar numbers in plaintext. Storing the number
is exactly the thing that turns a health database into an identity-theft
target, and the app gains nothing from having it.

It is also honest in the interface: the profile says *"Verified offline at
registration"*, not *"Aadhaar verified"*. A worker or auditor reading the
screen is told what actually happened.

---

## Upgrading to real e-KYC later

The interface was designed for this. `verify()` in
`backend/app/core/aadhaar.py` returns an `AadhaarCheck` with a `method` field:

```python
@dataclass
class AadhaarCheck:
    valid: bool
    reason: str
    last4: str | None = None
    method: str = "offline_verhoeff"
```

To move to licensed e-KYC, replace the body of `verify()` with the AUA/KUA call
and set `method="uidai_ekyc"`. Everything downstream — the storage model, the
consent gate, the masking, the duplicate check, the UI — is unchanged, because
none of it ever depended on holding the number.

Two other paths are worth knowing about if this project continues:

- **UIDAI Offline e-KYC (Aadhaar Paperless Offline e-KYC / XML)**: the resident
  downloads a digitally signed, share-code-protected XML or QR code from the
  UIDAI site and hands it over. It is signature-verifiable **without** an AUA
  licence, and yields a verified name, DOB, gender and address. This is the
  natural next step for SevakAI and does not require licensing — it requires
  the patient to have a smartphone or to have obtained the file, which is the
  practical obstacle in rural settings.
- **ABHA / Ayushman Bharat Health Account (ABDM)**: the government's own health
  identifier, purpose-built for exactly this use case, and the correct
  long-term answer for a health record system. Integration is via the ABDM
  sandbox and does not require an Aadhaar AUA licence.

If asked "why not ABHA from the start?" — the honest answer is that ABHA
onboarding requires a registered health facility and an ABDM sandbox
application, which is out of scope for a five-day build, while the offline
validation above is fully implementable and defensible today.
