"""India's National Immunization Schedule, infant and child portion.

Source: National Immunization Schedule, Immunization Division, Ministry of
Health and Family Welfare (indexed in the guideline corpus as
national_immunization_schedule.pdf).

Each entry is (vaccine, dose label, weeks after birth). Rows are materialised
for a patient at registration so due dates exist from day one instead of
depending on the worker remembering the schedule.
"""

from __future__ import annotations

SCHEDULE: tuple[tuple[str, str | None, int], ...] = (
    ("BCG", None, 0),
    ("Hepatitis B", "Birth dose", 0),
    ("OPV", "0", 0),
    ("OPV", "1", 6),
    ("Pentavalent", "1", 6),
    ("Rotavirus", "1", 6),
    ("fIPV", "1", 6),
    ("PCV", "1", 6),
    ("OPV", "2", 10),
    ("Pentavalent", "2", 10),
    ("Rotavirus", "2", 10),
    ("OPV", "3", 14),
    ("Pentavalent", "3", 14),
    ("Rotavirus", "3", 14),
    ("fIPV", "2", 14),
    ("PCV", "2", 14),
    ("Measles-Rubella", "1", 39),      # 9 completed months
    ("PCV Booster", None, 39),
    ("JE", "1", 39),
    ("Vitamin A", "1st dose", 39),
    ("DPT", "Booster-1", 70),          # 16-24 months
    ("Measles-Rubella", "2", 70),
    ("OPV", "Booster", 70),
    ("JE", "2", 70),
)
