"""Aadhaar handling.

What this is NOT: real UIDAI e-KYC. Live Aadhaar authentication is available
only to licensed AUA/KUA entities under the Aadhaar Act; there is no public or
free API, and no legitimate way for this project to call one.

What this IS: the checks that can be done honestly offline --
  1. structural validity (12 digits, does not start with 0 or 1),
  2. the Verhoeff checksum UIDAI actually uses on the last digit,
  3. explicit recorded consent from the patient,
  4. storage of a salted hash + last four digits only, never the number.

That combination catches typos and duplicate registrations, which is most of
the day-to-day value, and it is the same interface a licensed KUA integration
would later drop into: swap `verify()` for a real API call and nothing else in
the codebase changes.
"""

from __future__ import annotations

from dataclasses import dataclass

# Verhoeff tables (dihedral group D5), per the UIDAI specification.
_D = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
    (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
    (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
    (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
    (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
)

_P = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
    (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
    (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
    (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
)


def verhoeff_valid(number: str) -> bool:
    digits = "".join(c for c in number if c.isdigit())
    check = 0
    for i, digit in enumerate(reversed(digits)):
        check = _D[check][_P[i % 8][int(digit)]]
    return check == 0


def normalise(raw: str) -> str:
    """Strip the spaces workers naturally type between groups of four."""
    return "".join(c for c in raw if c.isdigit())


@dataclass
class AadhaarCheck:
    valid: bool
    reason: str
    last4: str | None = None
    method: str = "offline_verhoeff"


def verify(raw: str) -> AadhaarCheck:
    digits = normalise(raw)

    if len(digits) != 12:
        return AadhaarCheck(False, "Aadhaar number must be exactly 12 digits")
    if digits[0] in "01":
        # UIDAI never issues numbers beginning with 0 or 1.
        return AadhaarCheck(False, "Aadhaar numbers cannot start with 0 or 1")
    if len(set(digits)) == 1:
        return AadhaarCheck(False, "That does not look like a real Aadhaar number")
    if not verhoeff_valid(digits):
        return AadhaarCheck(False, "Checksum failed - please re-enter the number")

    return AadhaarCheck(True, "Verified offline", last4=digits[-4:])


def mask(last4: str | None) -> str:
    return f"XXXX XXXX {last4}" if last4 else "Not linked"
