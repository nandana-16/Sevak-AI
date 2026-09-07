"""Registry of the guideline documents in the corpus.

Every retrieved chunk carries the title and URL from here, so a risk
classification the app shows a worker can always be traced back to a real
Government of India document rather than to something the model invented.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GuidelineSource:
    filename: str
    title: str
    publisher: str
    year: str
    url: str
    # Which kinds of patient this document is relevant to. Used to bias
    # retrieval so an infant case does not get answered with ANC protocol.
    topics: tuple[str, ...]


SOURCES: tuple[GuidelineSource, ...] = (
    GuidelineSource(
        "hbnc_operational_guidelines_2014.pdf",
        "Home Based Newborn Care - Operational Guidelines (Revised 2014)",
        "Ministry of Health and Family Welfare, Government of India",
        "2014",
        "https://nhm.gov.in/images/pdf/programmes/child-health/guidelines/Revised_Home_Based_New_Born_Care_Operational_Guidelines_2014.pdf",
        ("newborn", "infant", "postnatal", "home_visit"),
    ),
    GuidelineSource(
        "hbyc_asha_facilitator_handbook.pdf",
        "Handbook for ASHA Facilitator and ANM/MPW on Home Based Newborn Care and Home Based Care for Young Child",
        "Ministry of Health and Family Welfare, Government of India",
        "2022",
        "https://www.nhm.gov.in/New-Update-2022-24/CH-Programmes/HBNC-&-HBYC-Resource-%20Material/HBYC-Handbook-for-Asha-Facilator-Book.pdf",
        ("newborn", "infant", "child", "home_visit", "nutrition"),
    ),
    GuidelineSource(
        "pmsma_high_risk_conditions.pdf",
        "High Risk Conditions in Pregnancy (PMSMA)",
        "Maternal Health Division, Ministry of Health and Family Welfare",
        "2016",
        "https://pmsma.mohfw.gov.in/wp-content/uploads/2016/10/High-Risk-Conditions-in-preg-modified-Final.pdf",
        ("pregnancy", "anc", "high_risk"),
    ),
    GuidelineSource(
        "pmsma_guidelines.pdf",
        "Pradhan Mantri Surakshit Matritva Abhiyan - Guidelines",
        "Maternal Health Division, Ministry of Health and Family Welfare",
        "2016",
        "https://nhm.hp.gov.in/storage/app/media/uploaded-files/PMSMA-Guidelines.pdf",
        ("pregnancy", "anc"),
    ),
    GuidelineSource(
        "extended_pmsma_hrp_tracking.pdf",
        "Guidance Note for Extended PMSMA - Tracking High Risk Pregnancies",
        "Maternal Health Division, Ministry of Health and Family Welfare",
        "2022",
        "https://www.nhm.gov.in/New_Update-2022-23/MH/GUIDELINES-%20MH/Guidance_Note-Extended_PMSMA_for_tracking_HRPs.pdf",
        ("pregnancy", "anc", "high_risk", "follow_up"),
    ),
    GuidelineSource(
        "anemia_mukt_bharat_operational_guidelines.pdf",
        "Anemia Mukt Bharat - Operational Guidelines",
        "Ministry of Health and Family Welfare, Government of India",
        "2018",
        "https://nhm.gov.in/images/pdf/Nutrition/AMB-guidelines/Anemia-Mukt-Bharat-Operational-Guidelines-FINAL.pdf",
        ("anaemia", "pregnancy", "child", "nutrition"),
    ),
    GuidelineSource(
        "national_immunization_schedule.pdf",
        "National Immunization Schedule",
        "Immunization Division, Ministry of Health and Family Welfare",
        "2018",
        "https://nhm.gov.in/New_Updates_2018/NHM_Components/Immunization/report/National_%20Immunization_Schedule.pdf",
        ("immunisation", "infant", "child", "pregnancy"),
    ),
    GuidelineSource(
        "imnci_chart_booklet.pdf",
        "IMNCI Chart Booklet",
        "Ministry of Health and Family Welfare, Government of India",
        "2009",
        "https://nhm.gov.in/images/pdf/programmes/child-health/guidelines/imnci_chart_booklet.pdf",
        ("child", "infant", "danger_signs", "fever", "diarrhoea", "pneumonia"),
    ),
)

BY_FILENAME = {source.filename: source for source in SOURCES}
