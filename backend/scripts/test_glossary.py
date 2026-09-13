"""Danger-sign translation, without touching the model or the network.

This exists because the thing it covers is a *fallback*. The risk prompt asks
for danger_signs in Hindi and the model usually complies, so a test that runs a
live visit mostly exercises the model getting it right and proves nothing about
the path that matters - the one taken when the model returns the prose in Hindi
and the list in English anyway.

Running offline also means this still works when Groq's daily token ceiling is
reached, which is exactly when the integration tests go quiet.

Run:  python -m scripts.test_glossary
"""

from __future__ import annotations

import re
import sys

from app.agents import glossary

failures = 0

# Latin that is meant to survive: an ASHA's registers use these, and
# "BP 172/114" reads the same in either language.
ALLOWED_LATIN = {
    "bp", "hb", "spo", "spo2", "muac", "anc", "ifa", "tt", "edd",
    "g", "dl", "mg", "ml", "kg", "cm", "c", "f",
}


def check(label: str, ok: bool, detail: str = "") -> None:
    global failures
    if not ok:
        failures += 1
    print(f"[{'  ok  ' if ok else ' FAIL '}] {label}{(' - ' + detail) if detail else ''}")


# Signs seen coming back from the model in English on a Hindi visit.
MUST_TRANSLATE = [
    "headache", "blurred vision", "pedal oedema", "pedal edema",
    "severe headache", "severe abdominal pain", "abdominal pain",
    "vaginal bleeding", "heavy bleeding", "reduced fetal movement",
    "high blood pressure", "low blood pressure", "fast pulse",
    "severe anaemia", "fever", "convulsions", "unconscious",
    "not feeding", "unable to feed", "lethargy", "fast breathing",
    "cold to touch", "hypothermia", "jaundice", "chest indrawing",
    "swelling of feet", "facial swelling", "severe headache with blurred vision",
    "Severe anaemia (Hb 6.2 g/dL)",
]

# Must survive untouched: measurements and abbreviations.
MUST_KEEP = ["BP 168/112", "BP 172/114", "Hb 6.2 g/dL", "SpO2 88%", "MUAC 10.5 cm"]

# Already Hindi - the model got it right, so nothing should happen to these.
ALREADY_HINDI = [
    "सिर दर्द", "धुंधली दृष्टि", "पैरों में सूजन",
    "तेज़ सर दर्द के साथ धुंधला दिखना", "गर्भावस्था में खून आना",
]


def main() -> int:
    # --- The rescue path ----------------------------------------------------
    for sign in MUST_TRANSLATE:
        out = glossary.to_hindi(sign)
        stray = [
            word for word in re.findall(r"[A-Za-z]+", out)
            if word.lower() not in ALLOWED_LATIN
        ]
        check(f"translates {sign!r}", glossary.has_devanagari(out) and not stray,
              f"{out!r}" + (f" stray={stray}" if stray else ""))

    # --- What must not be translated ----------------------------------------
    for sign in MUST_KEEP:
        check(f"leaves {sign!r} alone", glossary.to_hindi(sign) == sign,
              repr(glossary.to_hindi(sign)))

    # --- Idempotence ---------------------------------------------------------
    # This runs over output the model may already have translated, and over
    # rule labels that are Hindi from the start, so applying it twice must
    # change nothing.
    for sign in [*MUST_TRANSLATE, *MUST_KEEP, *ALREADY_HINDI]:
        once = glossary.to_hindi(sign)
        check(f"stable on repeat: {sign[:32]!r}", glossary.to_hindi(once) == once,
              f"{once!r} -> {glossary.to_hindi(once)!r}")

    for sign in ALREADY_HINDI:
        check(f"passes through {sign!r}", glossary.to_hindi(sign) == sign)

    # --- Honest about what it does not know ---------------------------------
    # A half-translated sign is worse than an English one. Anything outside the
    # vocabulary must come back whole, not mangled.
    for sign in ["photophobia", "photophobia and headache", "oliguria",
                 "hyperreflexia with clonus"]:
        check(f"leaves the unknown {sign!r} intact",
              glossary.to_hindi(sign) == sign, repr(glossary.to_hindi(sign)))

    # --- Keying across languages --------------------------------------------
    # The model's English and the rule engine's Hindi for one finding have to
    # collide, or the worker is shown the same danger sign twice.
    pairs = [
        ("headache", "सर दर्द"),
        ("blurred vision", "धुंधला दिखना"),
        ("not feeding", "दूध नहीं पी रहा"),
        ("severe abdominal pain", "पेट में तेज़ दर्द"),
        ("vaginal bleeding in pregnancy", "गर्भावस्था में खून आना"),
    ]
    for english, hindi in pairs:
        check(f"{english!r} and {hindi!r} key alike",
              glossary.canonical(english) == glossary.canonical(hindi),
              f"{glossary.canonical(english)!r} vs {glossary.canonical(hindi)!r}")

    print()
    print(f"{failures} check(s) failed" if failures
          else "Danger signs translate correctly")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
