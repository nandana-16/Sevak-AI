"""Turning a Patient row into the compact text the agents reason over.

Kept separate from the agents so all three see exactly the same picture of the
patient, and so the shape of that picture can be tuned in one place.
"""

from __future__ import annotations

from datetime import date

from app.models.db import Patient, PatientCategory


def age_years(patient: Patient) -> float | None:
    if patient.dob:
        delta = date.today() - patient.dob
        return round(delta.days / 365.25, 2)
    if patient.age_years_approx is not None:
        return float(patient.age_years_approx)
    return None


def age_label(patient: Patient) -> str:
    years = age_years(patient)
    if years is None:
        return "age unknown"
    if years < 0.16:
        return f"{int(years * 365.25)} days old"
    if years < 2:
        return f"{int(years * 12)} months old"
    return f"{int(years)} years old"


def gestation_weeks(patient: Patient) -> int | None:
    record = patient.pregnancy
    if not record or not record.lmp:
        return None
    return max(0, (date.today() - record.lmp).days // 7)


def build(patient: Patient, *, max_history: int = 3) -> str:
    """A short brief. Deliberately compact: this goes into three prompts per
    visit, and padding it with everything on file makes the model worse, not
    better."""
    lines = [
        f"Name: {patient.name}",
        f"Age: {age_label(patient)} | Sex: {patient.gender} | Category: {patient.category.value}",
    ]
    if patient.blood_group:
        lines.append(f"Blood group: {patient.blood_group}")
    if patient.village:
        lines.append(f"Village: {patient.village}")

    if patient.category == PatientCategory.pregnant and patient.pregnancy:
        record = patient.pregnancy
        weeks = gestation_weeks(patient)
        bits = []
        if weeks is not None:
            bits.append(f"{weeks} weeks pregnant")
        if record.edd:
            bits.append(f"EDD {record.edd.isoformat()}")
        if record.gravida is not None:
            bits.append(f"G{record.gravida}P{record.para or 0}")
        bits.append(f"{record.anc_visits_completed} ANC visits done")
        if record.last_hb is not None:
            bits.append(f"last Hb {record.last_hb} g/dL")
        if record.last_bp_systolic:
            bits.append(f"last BP {record.last_bp_systolic}/{record.last_bp_diastolic}")
        if record.high_risk_factors:
            bits.append("high-risk factors: " + ", ".join(record.high_risk_factors))
        lines.append("Pregnancy: " + "; ".join(bits))

    if patient.infant_record:
        record = patient.infant_record
        bits = []
        if record.birth_weight_kg:
            bits.append(f"birth weight {record.birth_weight_kg} kg")
        if record.gestation_weeks:
            bits.append(f"born at {record.gestation_weeks} weeks")
        if record.exclusive_breastfeeding is not None:
            bits.append(
                "exclusively breastfed" if record.exclusive_breastfeeding
                else "not exclusively breastfed"
            )
        if record.last_weight_kg:
            bits.append(f"last weight {record.last_weight_kg} kg")
        if bits:
            lines.append("Infant: " + "; ".join(bits))

    ongoing = [c.name for c in patient.conditions if c.ongoing]
    past = [c.name for c in patient.conditions if not c.ongoing]
    if ongoing:
        lines.append("Ongoing conditions: " + ", ".join(ongoing))
    if past:
        lines.append("Past history: " + ", ".join(past[:6]))

    due = [
        v for v in patient.vaccinations
        if not v.given and v.due_date and v.due_date <= date.today()
    ]
    if due:
        lines.append(
            "Immunisation overdue: "
            + ", ".join(f"{v.vaccine} {v.dose_label or ''}".strip() for v in due[:5])
        )

    history = [v for v in patient.visits if v.summary][:max_history]
    if history:
        lines.append("Recent visits:")
        for visit in history:
            lines.append(
                f"  - {visit.visited_at.date().isoformat()} "
                f"[{visit.risk_level.value}] {visit.summary}"
            )

    return "\n".join(lines)


def topics_for(patient: Patient) -> list[str]:
    """Which guideline documents to bias retrieval toward."""
    mapping = {
        PatientCategory.pregnant: ["pregnancy", "anc", "high_risk", "anaemia"],
        PatientCategory.postnatal: ["postnatal", "newborn", "anaemia"],
        PatientCategory.infant: ["newborn", "infant", "danger_signs", "immunisation"],
        PatientCategory.child: ["child", "danger_signs", "nutrition", "immunisation"],
    }
    return mapping.get(patient.category, ["danger_signs", "anaemia"])
