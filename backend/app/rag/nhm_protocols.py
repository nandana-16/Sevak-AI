"""Synthetic NHM-style clinical protocol knowledge base for demo/RAG purposes.

These are original summaries written for this prototype, informed by publicly known
community-health-worker risk-screening concepts (maternal danger signs, anemia,
hypertensive disorders of pregnancy, child malnutrition/ARI/diarrhea danger signs,
immunization timing). They are NOT verbatim reproductions of any government document
and MUST be replaced with the actual current NHM/RCH guideline text before any real
clinical use — this dataset exists to make Agent 2's RAG pipeline demonstrable.
"""

NHM_PROTOCOLS = [
    {
        "id": "NHM-MH-01",
        "title": "Routine Antenatal Screening",
        "category": "maternal",
        "content": (
            "Routine antenatal visits should confirm blood pressure below 140/90 mmHg, "
            "hemoglobin above 11 g/dL, normal fetal movement, and absence of edema, "
            "bleeding, or severe headache. No abnormal findings indicates LOW risk; "
            "continue standard visit schedule."
        ),
    },
    {
        "id": "NHM-MH-02",
        "title": "Anemia Prevention and Management in Pregnancy",
        "category": "maternal",
        "content": (
            "All pregnant women should receive daily iron-folic acid (IFA) supplementation. "
            "Missed IFA doses over consecutive weeks, pallor, fatigue, or dizziness suggest "
            "developing anemia, which is a leading contributor to maternal mortality and low "
            "birth weight. Non-compliance with IFA for more than one week should be classified "
            "MEDIUM risk with counselling and re-supply; hemoglobin below 7 g/dL is HIGH risk "
            "requiring referral."
        ),
    },
    {
        "id": "NHM-MH-03",
        "title": "Antepartum Hemorrhage Danger Sign",
        "category": "maternal",
        "content": (
            "Any vaginal bleeding after the first trimester is a HIGH risk obstetric emergency "
            "requiring immediate referral to a facility capable of emergency obstetric care, "
            "regardless of reported bleeding volume."
        ),
    },
    {
        "id": "NHM-MH-04",
        "title": "Pregnancy-Induced Hypertension (PIH) / Pre-eclampsia Screening",
        "category": "maternal",
        "content": (
            "Blood pressure at or above 140/90 mmHg in pregnancy is classified as gestational "
            "hypertension and is HIGH risk. When accompanied by swelling of hands/face, severe "
            "headache, or visual disturbance, pre-eclampsia is suspected and referral is urgent "
            "and non-negotiable. Blood pressure between 130-139/85-89 mmHg without symptoms is "
            "MEDIUM risk requiring recheck within 3-5 days."
        ),
    },
    {
        "id": "NHM-MH-05",
        "title": "Reduced or Absent Fetal Movement",
        "category": "maternal",
        "content": (
            "Mother-reported reduction or absence of fetal movement after 28 weeks gestation is "
            "HIGH risk and requires same-day clinical evaluation to rule out fetal distress."
        ),
    },
    {
        "id": "NHM-MH-06",
        "title": "Severe Headache or Visual Disturbance in Pregnancy",
        "category": "maternal",
        "content": (
            "Severe or persistent headache, blurred vision, or seeing spots during pregnancy "
            "are classic pre-eclampsia warning signs and are HIGH risk irrespective of blood "
            "pressure reading at the time of visit, since BP can fluctuate."
        ),
    },
    {
        "id": "NHM-MH-07",
        "title": "Prolonged or Obstructed Labour Signs",
        "category": "maternal",
        "content": (
            "Labour lasting more than 12 hours for a first pregnancy or 8 hours for subsequent "
            "pregnancies without progress is HIGH risk; ASHA workers should facilitate immediate "
            "transport to a facility with emergency obstetric capability."
        ),
    },
    {
        "id": "NHM-MH-08",
        "title": "Postpartum Hemorrhage Warning Signs",
        "category": "maternal",
        "content": (
            "Heavy bleeding (soaking more than one pad per hour), passage of large clots, or "
            "dizziness/fainting within 24 hours to 6 weeks postpartum is HIGH risk and a leading "
            "cause of preventable maternal death; immediate referral is required."
        ),
    },
    {
        "id": "NHM-MH-09",
        "title": "Postpartum Fever / Sepsis Screening",
        "category": "maternal",
        "content": (
            "Fever above 100.4F (38C) with foul-smelling discharge or abdominal pain within 6 "
            "weeks postpartum suggests puerperal sepsis and is HIGH risk requiring antibiotics "
            "and referral."
        ),
    },
    {
        "id": "NHM-MH-10",
        "title": "Gestational Diabetes Risk Factors",
        "category": "maternal",
        "content": (
            "Excessive weight gain, family history of diabetes, or previous macrosomic baby are "
            "MEDIUM risk factors warranting glucose screening at the next facility visit."
        ),
    },
    {
        "id": "NHM-SOC-01",
        "title": "Social Determinants Screening",
        "category": "social",
        "content": (
            "Household isolation, absence of a supportive spouse/family member, or reported "
            "economic stress correlate with delayed care-seeking behavior and missed follow-up "
            "visits. Presence of one or more social risk factors should raise an otherwise LOW "
            "risk case to at least MEDIUM for closer monitoring, even without abnormal vitals."
        ),
    },
    {
        "id": "NHM-SOC-02",
        "title": "Adolescent or First-Time Pregnancy Risk",
        "category": "social",
        "content": (
            "Pregnancy under age 19 or first pregnancy without prior antenatal contact is MEDIUM "
            "risk due to higher complication rates and lower health literacy; extra counselling "
            "visits are recommended."
        ),
    },
    {
        "id": "NHM-CH-01",
        "title": "Child Danger Signs — General",
        "category": "child",
        "content": (
            "A child unable to drink or breastfeed, vomiting everything, having convulsions, or "
            "lethargic/unconscious presents with an IMCI general danger sign and is HIGH risk "
            "requiring urgent referral regardless of other findings."
        ),
    },
    {
        "id": "NHM-CH-02",
        "title": "Acute Respiratory Infection (ARI) Classification",
        "category": "child",
        "content": (
            "Fast breathing for age plus chest indrawing indicates severe pneumonia (HIGH risk, "
            "urgent referral). Fast breathing alone without chest indrawing is pneumonia (MEDIUM "
            "risk, oral antibiotics per protocol and follow-up in 2 days). Cough without fast "
            "breathing is LOW risk (home care advice)."
        ),
    },
    {
        "id": "NHM-CH-03",
        "title": "Diarrhea and Dehydration Assessment",
        "category": "child",
        "content": (
            "Diarrhea with sunken eyes, skin pinch returning very slowly, and lethargy indicates "
            "severe dehydration (HIGH risk, urgent IV/referral). Restless/irritable with sunken "
            "eyes and slow skin pinch is some dehydration (MEDIUM risk, ORS and zinc, follow-up). "
            "No signs of dehydration is LOW risk (home ORS management)."
        ),
    },
    {
        "id": "NHM-CH-04",
        "title": "Severe Acute Malnutrition (SAM) Screening",
        "category": "child",
        "content": (
            "MUAC (mid-upper arm circumference) below 11.5 cm or visible severe wasting or "
            "bilateral pitting edema in a child under 5 is HIGH risk (SAM) requiring immediate "
            "referral to a Nutrition Rehabilitation Centre. MUAC 11.5-12.5 cm is MEDIUM risk "
            "(moderate acute malnutrition), requiring supplementary feeding and monitoring."
        ),
    },
    {
        "id": "NHM-CH-05",
        "title": "Low Birth Weight Follow-up Protocol",
        "category": "child",
        "content": (
            "Birth weight below 2.5 kg is MEDIUM risk requiring weekly weight-gain monitoring "
            "and kangaroo mother care counselling for the first month; below 1.8 kg is HIGH risk "
            "requiring facility-based care."
        ),
    },
    {
        "id": "NHM-CH-06",
        "title": "Immunization Schedule Delay",
        "category": "child",
        "content": (
            "A child more than 4 weeks behind the National Immunization Schedule for age is "
            "MEDIUM risk; the ASHA worker should actively schedule and confirm the next session "
            "and note the reason for delay (access, hesitancy, illness)."
        ),
    },
    {
        "id": "NHM-CH-07",
        "title": "High-Grade Fever in Infants",
        "category": "child",
        "content": (
            "Fever above 101F (38.3C) in an infant under 2 months is HIGH risk requiring "
            "immediate referral, as young infants can deteriorate rapidly and localize infection "
            "poorly. In children over 2 months, high fever without other danger signs is MEDIUM "
            "risk and should be monitored with antipyretics and a 24-hour recheck."
        ),
    },
    {
        "id": "NHM-CH-08",
        "title": "Jaundice in Newborn",
        "category": "child",
        "content": (
            "Yellowing of a newborn's palms and soles, or jaundice appearing within the first 24 "
            "hours of life, is HIGH risk requiring urgent referral to rule out severe "
            "hyperbilirubinemia."
        ),
    },
    {
        "id": "NHM-CH-09",
        "title": "Umbilical Cord Infection Signs",
        "category": "child",
        "content": (
            "Redness spreading to the skin around the umbilical stump, pus discharge, or foul "
            "odor in a newborn is HIGH risk (possible omphalitis/sepsis) and requires urgent "
            "referral."
        ),
    },
    {
        "id": "NHM-GEN-01",
        "title": "Tuberculosis Symptom Screening",
        "category": "general",
        "content": (
            "Cough persisting more than 2 weeks, unexplained weight loss, evening fever, or "
            "night sweats in any household member is MEDIUM risk requiring sputum testing "
            "referral under the national TB programme; a positive contact history raises this to "
            "HIGH risk for household screening."
        ),
    },
    {
        "id": "NHM-GEN-02",
        "title": "Non-Communicable Disease Follow-up",
        "category": "general",
        "content": (
            "Known hypertensive or diabetic patients who have missed medication for more than 2 "
            "weeks, or report chest pain/breathlessness, are MEDIUM to HIGH risk depending on "
            "symptom severity and require prompt facility follow-up."
        ),
    },
    {
        "id": "NHM-GEN-03",
        "title": "Mental Health and Postpartum Depression Screening",
        "category": "general",
        "content": (
            "Persistent low mood, loss of interest, or expressed thoughts of self-harm in a "
            "postpartum or general patient is HIGH risk and requires prompt referral to the "
            "nearest facility with mental health support, handled with sensitivity and privacy."
        ),
    },
]
