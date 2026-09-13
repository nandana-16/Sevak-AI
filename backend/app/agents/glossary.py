"""Danger-sign vocabulary, English to Hindi and back.

The risk prompt already asks for `danger_signs` in Hindi and names the field
explicitly. The model obeys most of the time and then, on some visits, returns
the prose in Hindi and the list in English anyway - so a worker reading a Hindi
result finds "pedal oedema" sitting in the middle of it. Prompting harder has
already been tried; this is the deterministic floor underneath it.

Two jobs, and they are the same table read in both directions:

* `to_hindi` renders a sign for display. Unknown phrases are returned
  untouched - a half-translated sign is worse than an honest English one, and
  silence about what we could not translate would be worse still.
* `canonical` produces a language-independent key so the model's "blurred
  vision" and the rule engine's "तेज़ सर दर्द के साथ धुंधला दिखना" can be
  recognised as the same finding instead of both being shown.

Abbreviations and numbers stay in Latin script throughout - BP, Hb, SpO2, MUAC
are what an ASHA's registers already use, and "BP 168/112" is read the same way
in either language.
"""

from __future__ import annotations

import re

from app.agents.rules import SIGN_HI

# Clinical vocabulary the extraction and risk agents actually emit, beyond the
# rule engine's own sign names. Keys are lowercase English.
TERM_HI: dict[str, str] = {
    # --- maternal ---------------------------------------------------------
    "headache": "सर दर्द",
    "blurred vision": "धुंधला दिखना",
    "blurring of vision": "धुंधला दिखना",
    "visual disturbance": "दिखने में दिक्कत",
    "pedal oedema": "पैरों में सूजन",
    "pedal edema": "पैरों में सूजन",
    "oedema": "सूजन",
    "edema": "सूजन",
    "swelling": "सूजन",
    "facial swelling": "चेहरे पर सूजन",
    "swelling of face": "चेहरे पर सूजन",
    "swelling of feet": "पैरों में सूजन",
    "vaginal bleeding": "योनि से खून आना",
    "bleeding": "खून आना",
    "heavy bleeding": "बहुत खून आना",
    "reduced fetal movement": "बच्चे का हिलना कम",
    "absent fetal movement": "बच्चे का हिलना बंद",
    "decreased fetal movement": "बच्चे का हिलना कम",
    "abdominal pain": "पेट में दर्द",
    "epigastric pain": "पेट के ऊपरी हिस्से में दर्द",
    "high blood pressure": "उच्च रक्तचाप",
    "hypertension": "उच्च रक्तचाप",
    "low blood pressure": "रक्तचाप कम",
    "hypotension": "रक्तचाप कम",
    "pre-eclampsia": "प्री-एक्लेम्पसिया",
    "preeclampsia": "प्री-एक्लेम्पसिया",
    "eclampsia": "एक्लेम्पसिया",
    "leaking of fluid": "पानी निकलना",
    "preterm labour": "समय से पहले प्रसव पीड़ा",
    "preterm labor": "समय से पहले प्रसव पीड़ा",
    "foul smelling discharge": "बदबूदार स्राव",
    "decreased urine output": "पेशाब कम होना",
    # --- general ----------------------------------------------------------
    "fever": "बुख़ार",
    "high fever": "तेज़ बुख़ार",
    "convulsions": "झटके",
    "fits": "दौरे",
    "seizures": "झटके",
    "unconscious": "बेहोश",
    "unresponsive": "कोई जवाब नहीं",
    "pallor": "पीलापन",
    "pale": "पीला पड़ना",
    "anaemia": "ख़ून की कमी",
    "anemia": "ख़ून की कमी",
    "severe anaemia": "ख़ून की बहुत कमी",
    "severe anemia": "ख़ून की बहुत कमी",
    "breathlessness": "साँस फूलना",
    "fast breathing": "तेज़ साँस",
    "rapid breathing": "तेज़ साँस",
    "difficulty breathing": "साँस लेने में तकलीफ़",
    "fast pulse": "नाड़ी तेज़",
    "rapid pulse": "नाड़ी तेज़",
    "tachycardia": "नाड़ी तेज़",
    "weak pulse": "नाड़ी कमज़ोर",
    "dizziness": "चक्कर आना",
    "fainting": "बेहोशी जैसा लगना",
    "vomiting": "उल्टी",
    "diarrhoea": "दस्त",
    "diarrhea": "दस्त",
    "dehydration": "पानी की कमी",
    "weight loss": "वज़न घटना",
    # --- newborn and infant ------------------------------------------------
    "not feeding": "दूध नहीं पी रहा",
    "unable to feed": "दूध नहीं पी पा रहा",
    "poor feeding": "ठीक से दूध नहीं पी रहा",
    "lethargy": "सुस्ती",
    "lethargic": "सुस्त",
    "drowsy": "नींद जैसा",
    "hypothermia": "शरीर ठंडा",
    "cold to touch": "छूने पर ठंडा",
    "jaundice": "पीलिया",
    "chest indrawing": "पसली का अंदर धँसना",
    "grunting": "कराहना",
    "nasal flaring": "नाक फूलना",
    "umbilical redness": "नाभि के पास लाली",
    "low birth weight": "जन्म के समय कम वज़न",
}

# Qualifiers that the model attaches to almost anything. Handled separately so
# "severe abdominal pain" resolves without needing its own row next to
# "abdominal pain".
QUALIFIER_HI: dict[str, str] = {
    "severe": "तेज़",
    "very severe": "बहुत तेज़",
    "very": "बहुत",
    "mild": "हल्का",
    "persistent": "लगातार",
    "continuous": "लगातार",
    "sudden": "अचानक",
    "possible": "शायद",
    "suspected": "शायद",
}

# The rule engine's sign names, folded in so both tables stay in step.
_ALL_HI: dict[str, str] = {**TERM_HI, **{k.lower(): v for k, v in SIGN_HI.items()}}

# Hindi back to English, for keying. Built from the same rows, so the two
# directions cannot drift apart.
_HI_EN: dict[str, str] = {}
for _en, _hi in _ALL_HI.items():
    _HI_EN.setdefault(_hi, _en)

_DEVANAGARI = re.compile(r"[ऀ-ॿ]")


def has_devanagari(text: str) -> bool:
    return bool(_DEVANAGARI.search(text))


def _normalise(text: str) -> str:
    """Lowercase, collapse whitespace, drop trailing punctuation and any
    parenthetical the model tacked on ("Severe anaemia (Hb 6.2 g/dL)")."""
    cleaned = re.sub(r"\([^)]*\)", " ", text.lower())
    cleaned = re.sub(r"[\s]+", " ", cleaned)
    return cleaned.strip(" .,;:-/")


def to_hindi(sign: str) -> str:
    """Render one danger sign in Hindi, or return it unchanged.

    Anything already in Devanagari is left alone, so this is safe to apply to a
    list the model got right - and safe to apply twice.
    """
    if not sign or has_devanagari(sign):
        return sign

    key = _normalise(sign)
    if not key:
        return sign

    direct = _ALL_HI.get(key)
    if direct:
        return direct

    # "severe abdominal pain" -> tez + pet me dard
    for qualifier, qualifier_hi in sorted(
        QUALIFIER_HI.items(), key=lambda kv: -len(kv[0])
    ):
        prefix = qualifier + " "
        if key.startswith(prefix):
            base = _ALL_HI.get(key[len(prefix):])
            if base:
                return f"{qualifier_hi} {base}"

    # A phrase built from terms we know: "headache with blurred vision".
    # Longest terms first so "severe abdominal pain" is not consumed by
    # "abdominal pain" leaving a stray English "severe" behind.
    replaced = key
    hit = False
    for term, term_hi in sorted(_ALL_HI.items(), key=lambda kv: -len(kv[0])):
        pattern = r"\b" + re.escape(term) + r"\b"
        if re.search(pattern, replaced):
            replaced = re.sub(pattern, term_hi, replaced)
            hit = True
    if hit:
        for qualifier, qualifier_hi in QUALIFIER_HI.items():
            replaced = re.sub(r"\b" + qualifier + r"\b", qualifier_hi, replaced)
        # Only accept it if nothing substantial is left in English - a sign
        # reading "तेज़ सर दर्द with photophobia" helps nobody.
        leftover = re.sub(r"[^a-z]+", "", re.sub(r"\b(with|and|or|of|the|a)\b", "", replaced))
        if not leftover:
            return re.sub(r"\s+", " ", replaced).strip()

    # Measurements and abbreviations - "BP 168/112", "Hb 6.2 g/dL" - are read
    # the same either way and stay as they are.
    return sign


def canonical(sign: str) -> str:
    """A language-independent key for spotting the same finding twice.

    Hindi signs are mapped back to their English name where we know it, so the
    model's English list and the rule engine's Hindi labels collide instead of
    both being shown to the worker.
    """
    if not sign:
        return ""
    if has_devanagari(sign):
        stripped = sign.strip()
        return _HI_EN.get(stripped, stripped)
    return _normalise(sign)
