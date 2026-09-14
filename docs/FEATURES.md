# What SevakAI does

This is the full list of what the project can do, feature by feature. It is
written for someone who has not seen the code. If you want to run it, start
with the [README](../README.md). If you want to demo it, use
[DEMO.md](DEMO.md).

**Contents**

1. [The idea in one page](#1-the-idea-in-one-page)
2. [Signing in](#2-signing-in)
3. [The patient roster](#3-the-patient-roster)
4. [The patient profile](#4-the-patient-profile)
5. [Registering a new patient](#5-registering-a-new-patient)
6. [Aadhaar verification](#6-aadhaar-verification)
7. [Recording a visit by voice](#7-recording-a-visit-by-voice)
8. [Typing instead of speaking](#8-typing-instead-of-speaking)
9. [The three agents](#9-the-three-agents)
10. [The guideline corpus and citations](#10-the-guideline-corpus-and-citations)
11. [The safety rules underneath the model](#11-the-safety-rules-underneath-the-model)
12. [The visit result screen](#12-the-visit-result-screen)
13. [Risk levels and how they move](#13-risk-levels-and-how-they-move)
14. [The visit plan](#14-the-visit-plan)
15. [Immunisation tracking](#15-immunisation-tracking)
16. [Escalations](#16-escalations)
17. [Messages to families](#17-messages-to-families)
18. [Working offline](#18-working-offline)
19. [Speech to text when offline](#19-speech-to-text-when-offline)
20. [Hindi and English](#20-hindi-and-english)
21. [The supervisor dashboard](#21-the-supervisor-dashboard)
22. [Who can see what](#22-who-can-see-what)
23. [When the model is unavailable](#23-when-the-model-is-unavailable)
24. [Server address settings](#24-server-address-settings)
25. [Design and look](#25-design-and-look)
26. [Tests](#26-tests)
27. [Demo data and reset](#27-demo-data-and-reset)
28. [What it does not do](#28-what-it-does-not-do)

---

## 1. The idea in one page

An ASHA worker is India's front line community health worker. She walks to
homes in her village, checks on pregnant women, new mothers and babies, and
writes what she finds in a paper register. The register goes to her supervisor
later. If a woman has danger signs today, whether she gets to a hospital
depends on whether the worker recognised the signs and pushed hard enough.

SevakAI sits in that gap. The worker opens the patient, presses the mic, and
says what she sees in her own language. The app turns that into a structured
visit record, checks it against real Government of India health guidelines,
tells her whether this person needs a hospital today, books the next visit, and
writes the message the family should get.

It is built to work with no network, because that is the normal condition in
the villages it is for.

Three parts:

| Part | What it is | Who uses it |
|---|---|---|
| Android app | Kotlin and Jetpack Compose | the ASHA worker, on her phone |
| Backend | Python, FastAPI, SQLite | nobody directly |
| Web dashboard | one HTML page served by the backend | the ANM and the BMO |

---

## 2. Signing in

The worker signs in with her phone number and a 4 digit PIN. That is all she
has to remember.

Before she signs in she picks her language, Hindi or English. The choice is
saved on the device, so she picks it once.

The sign in screen also shows which server the app is talking to, and lets her
change it. That matters on a real phone, where the backend is not on the same
machine.

**Why a PIN and not a password.** These are shared, low cost handsets, often
used with wet or work worn hands. A long password typed on a small keyboard in
a doorway is a password written on the back of the phone. The PIN is short on
purpose.

**Why the login lasts 14 days.** A worker can go days without seeing a network.
Being logged out in the middle of a round, with a queue of unsent visits, is
worse than the small extra risk of a long session. The token is set to expire
after 14 days by default and that number is a setting.

---

## 3. The patient roster

The first screen after sign in is her own list of patients. Nobody else's.

The list is sorted riskiest first, then by who is most overdue. That is the
order she plans her day in, so no sorting controls are needed.

Every row shows:

- name, age and category
- the risk colour as a word, not only a colour
- **the last visit note**, one line, so she knows what happened last time
  before she knocks on the door
- the next visit due date

She can:

- **search** by name or village
- **filter** by village
- **filter** by category (pregnant, infant, child, postnatal, adult, elderly)
- **filter** by risk level
- **filter** to only those with a visit due now

The last visit note on the row is a small thing that matters a lot. Without it
she has to open each profile to remember who this is.

---

## 4. The patient profile

Opening a patient shows the whole record:

- name, age, date of birth, gender, village, address
- blood group
- guardian name and household id
- phone number, if there is one
- Aadhaar status, shown masked as `XXXX XXXX 3356`, never in full
- current risk level
- **pregnancy block** for pregnant women: weeks of gestation, expected delivery
  date, gravida and para, how many ANC visits out of four, last haemoglobin,
  last BP, last weight, TT doses, IFA tablets, where the delivery is planned
- **infant block** for babies: birth weight, gestation at birth, delivery type,
  last weight, last MUAC, feeding status
- **immunisation list** with what has been given and what is due or overdue
- **disease history**, split into conditions the patient still has and ones
  that are in the past
- **previous visits**, each one tappable to see the full result again

A profile opens with no network if the patient has been seen before, because
the whole record is cached on the phone.

---

## 5. Registering a new patient

The worker can add someone who is not on her roster yet. The form collects:

- name, gender, date of birth or age
- category
- village, address, household id
- guardian name and phone
- blood group
- Aadhaar number, with consent

Two things happen automatically at registration:

- **A pregnancy or infant record is created** if the category calls for one, so
  the right fields exist from day one.
- **The full immunisation schedule is written out** for an infant, with real due
  dates counted from the date of birth. The worker never has to remember the
  schedule, and a baby registered today already has its 6 week, 10 week and 14
  week doses waiting.

The new patient is assigned to the worker who registered them.

---

## 6. Aadhaar verification

Aadhaar is India's national ID. This is the honest version of Aadhaar checking,
and the limits are worth stating plainly.

**What it is not.** It is not real UIDAI e-KYC. Live Aadhaar authentication is
only available to licensed AUA and KUA entities under the Aadhaar Act. There is
no public or free API. A student project cannot legitimately call one, and
pretending otherwise would be the dishonest choice.

**What it is.** The four checks that can be done offline and honestly:

1. The number is 12 digits and does not start with 0 or 1.
2. The **Verhoeff checksum** on the last digit passes. This is the real
   algorithm UIDAI uses, not a made up one.
3. The patient's consent is recorded explicitly.
4. Only a **salted one way hash** and the **last four digits** are stored. The
   number itself is never written to the database.

That combination catches typos and catches the same person being registered
twice, which is most of the day to day value. The duplicate check works on the
hash, so it works without ever holding the number.

The interface is the same shape a licensed integration would use. Swapping in
a real API later means changing one function and nothing else.

Full detail is in [AADHAAR.md](AADHAAR.md).

---

## 7. Recording a visit by voice

This is the centre of the app.

The worker opens a patient and presses one large mic button. She speaks
normally, in Hindi, in Hinglish, or in English. For example:

> रोशनी को तीन दिन से बहुत तेज़ सर दर्द है और आँखों के आगे धुंधला दिख रहा है।
> पैर में बहुत सूजन है। बच्चा कल से कम हिल रहा है।

While she talks she sees her words appearing on screen, and the mic button
pulses with how loud she is. Both exist so she can tell the mic is really
listening, which is not obvious on a cheap phone in a noisy room.

When she stops, the text goes to the backend and the three agents run. It takes
about four seconds.

She can also add measurements by hand at the same time: temperature, BP, pulse,
weight, haemoglobin, SpO2. Anything she types by hand is kept exactly as typed
and is never overwritten by the model. Speaking a number and typing a number
are both allowed, and typed wins.

---

## 8. Typing instead of speaking

Voice is the fast path, not the only path. Every visit can be typed instead.

This matters more than it sounds. Voice fails in a room with a television on,
with a crying baby, or when the woman being examined would rather the details
were not said out loud in front of her family. The typed path goes through
exactly the same three agents and produces exactly the same result.

---

## 9. The three agents

The backend runs three agents in a row, wired together with LangGraph. Each one
needs what the one before it produced.

```
speech or typed text
        |
        v
  1. Extraction        pulls out symptoms and numbers
        |
        v
  2. Risk              retrieves guidelines, classifies, cites them
        |
        v
  3. Scheduling        decides actions and the next visit date
        |
        v
  visit record, follow up, escalation, messages
```

### Agent 1: extraction

Turns free speech into structured fields. It reads Hindi in Devanagari script,
Hinglish in Latin script, and English, because a worker speaks all three in one
sentence.

Examples of what it handles:

| She says | It records |
|---|---|
| *pair me sujan* | pedal oedema |
| *BP 150 by 100* | `bp_systolic 150`, `bp_diastolic 100` |
| *एक सौ अड़सठ बटा एक सौ बारह* | `168/112` |
| *बच्चा कल से कम हिल रहा है* | reduced fetal movement |

Spoken Hindi numbers were a real problem here. "एक सौ अड़सठ" is 168, and the
model was reading it as 158 until the prompt was given a numeral glossary.

It also has an `unclear` field. Anything it could not confidently understand
goes there instead of being guessed at.

### Agent 2: risk classification

This is the one that matters clinically. It:

1. builds a short context about the patient (category, weeks pregnant, age,
   standing conditions)
2. retrieves the relevant passages from the guideline corpus, biased by the
   kind of patient so an infant case is not answered with pregnancy protocol
3. classifies the visit **red**, **yellow** or **green**
4. writes a plain language reason
5. lists the danger signs it found
6. cites the exact documents and page numbers it used
7. writes the message the family should be given

It is told to classify **today**, not the patient's past. A stable, already
managed condition is context, not a reason to keep someone red forever. That
instruction exists because the classifier used to anchor on history and never
let anyone improve.

### Agent 3: scheduling

Decides what to do now and when to come back. Each action carries an urgency:
`now`, `today`, `this_week` or `routine`.

The follow up interval the model proposes is then clamped to what the risk
level allows:

| Risk | Soonest | Default | Latest |
|---|---|---|---|
| Red | 1 day | 1 day | 2 days |
| Yellow | 2 days | 4 days | 7 days |
| Green | 7 days | routine for that patient type | 45 days |

The green default is not one number. It depends on who the patient is:

- pregnant, under 28 weeks: 30 days
- pregnant, 28 weeks or more: 14 days, because ANC goes fortnightly in the
  third trimester
- newborn under about six weeks: 3 days, because HBNC visits are dense early
- infant: 14 days
- postnatal: 7 days
- child or adult: 30 days

The clamp means a red case can never be scheduled three weeks out because the
model was feeling relaxed.

---

## 10. The guideline corpus and citations

The risk agent does not classify from memory. It retrieves from eight real
Government of India documents, indexed into 594 page anchored chunks in
ChromaDB.

| Document | Publisher | Year |
|---|---|---|
| Home Based Newborn Care, Operational Guidelines | MoHFW | 2014 |
| Handbook for ASHA Facilitator and ANM/MPW on HBNC and HBYC | MoHFW | 2022 |
| High Risk Conditions in Pregnancy (PMSMA) | Maternal Health Division, MoHFW | 2016 |
| Pradhan Mantri Surakshit Matritva Abhiyan Guidelines | Maternal Health Division, MoHFW | 2016 |
| Guidance Note for Extended PMSMA, Tracking High Risk Pregnancies | Maternal Health Division, MoHFW | 2022 |
| Anemia Mukt Bharat, Operational Guidelines | MoHFW | 2018 |
| National Immunization Schedule | Immunization Division, MoHFW | 2018 |
| IMNCI Chart Booklet | MoHFW | 2009 |

Every chunk keeps the document title, the publisher and the page number. So
every classification the app shows a worker can be traced back to a real
document and a real page.

This is the answer to "says who?". When a family asks why the baby has to go to
the health centre tonight, the worker can open the passage. The citations are
collapsed by default so they never get in the way of the action, and they are
one tap away when needed.

`GET /api/guidelines` lists the sources with their government URLs, so anyone
can check the documents are real.

---

## 11. The safety rules underneath the model

There is a deterministic rule engine under the model. It reads the transcript
and the extracted symptoms directly, looking for danger signs by keyword, in
English, Hindi and Hinglish.

It knows the standard danger sign lists:

- **general**: convulsions, unconscious, unable to drink or feed, vomiting
  everything, lethargic or very drowsy
- **maternal**: bleeding in pregnancy, severe headache with blurred vision,
  convulsions, reduced or absent fetal movement, severe abdominal pain,
  leaking of fluid
- **newborn**: severe chest indrawing, grunting or nasal flaring, cold to touch,
  umbilical redness or pus, yellow palms and soles, no movement

It also checks numbers against thresholds, for example a BP high enough to
mean pre-eclampsia, or a haemoglobin low enough to mean severe anaemia.

**The rules can raise the risk level. They can never lower it.**

That is the whole design in one line. If the model says green and the rules
find a danger sign, the visit comes back red and the reason says the protocol
check raised it. If the model says red and the rules find nothing, it stays
red. The model is allowed to be more cautious than the rules, never less.

The rule engine also produces its sign names in the worker's language, so a
Hindi result does not have English danger signs inside it.

---

## 12. The visit result screen

After a visit is processed the worker sees, in this order:

1. **The verdict**, as a large coloured block: High risk, Medium or Healthy,
   with the reason in plain language.
2. **A warning if anything was degraded**, meaning part of the answer came from
   rules alone because the model was unreachable. Canned output is never
   allowed to pass as live reasoning.
3. **The danger signs found**, listed.
4. **What to do now**, numbered, each with its urgency.
5. **The next visit date**, and a note that it has already been added to her
   plan.
6. **The messages that went out**, with their full text. More on this below.
7. **What was recorded in this visit**: symptoms and every measurement.
8. **The guidelines it was based on**, collapsed, expandable to the exact
   passages and page numbers.

The order is deliberate. A worker standing in someone's doorway needs the
action first. The evidence is there to justify it when asked, not to be read
first.

---

## 13. Risk levels and how they move

Three levels, named for what the worker should do:

| Level | Name shown | What it means |
|---|---|---|
| Red | **High risk** | take this person to a facility today |
| Yellow | **Medium** | a doctor should see this person soon |
| Green | **Healthy** | routine, come back at the normal interval |

There is also `unknown`, for a patient who has not been assessed yet.

**Risk moves in both directions.** Every visit re-classifies the patient. A
woman who was red last week and is well this week goes back to green. This was
a specific decision. A label that only ever gets worse stops meaning anything,
and a worker learns to ignore it.

The current risk level on the patient record is always the result of the most
recent visit.

---

## 14. The visit plan

A calendar view of what is due. Two tabs: today, and the next two weeks.

Rows are ordered by what needs attention, with overdue and high risk first.
Each row shows the patient, the village, the reason for the visit and the
priority.

From the plan she can:

- **open the patient** and record the visit
- **mark it done**
- **snooze it** by a number of days, when nobody was home

**Snoozing a high risk follow up is refused by the server.** The app does not
merely hide the button, the API rejects it with a message telling her to record
the visit or escalate it to her ANM. A red follow up being quietly pushed a week
is exactly the failure this project exists to prevent, so the rule lives on the
server where it cannot be bypassed.

Follow ups are created automatically by the scheduling agent. The worker never
has to add one by hand, and every visit closes whatever was pending for that
patient and books the next one.

---

## 15. Immunisation tracking

Infants get the full National Immunization Schedule written out at
registration, with due dates counted from their date of birth. 24 rows, from
the BCG and Hepatitis B birth doses through to the DPT booster and second
Measles-Rubella at 16 to 24 months.

On the profile the worker sees what has been given, what is coming up, and what
is overdue. Overdue doses are flagged.

She can mark a dose given with one tap, which records the date.

---

## 16. Escalations

When a visit classifies red, an escalation is raised automatically for the
supervising ANM. It carries the patient, the worker, the reason and the danger
signs.

Three rules shape how these behave:

**One open escalation per patient.** A worker recording three red visits during
a week where someone is getting worse should sharpen the supervisor's single
alert, not bury it under three copies of itself. The existing escalation is
updated instead.

**A later improvement is noted, not auto-resolved.** If the next visit comes
back green, a note is added saying the patient has since improved. The
escalation stays open, because a red event still needs a human to acknowledge
that they saw it. But the supervisor can see the case has moved on instead of
chasing it.

**Stale escalations are counted separately.** The dashboard shows how many have
gone unacknowledged for more than two days, because that number means a red
flagged patient may have been left.

A supervisor acknowledges an escalation from the dashboard, optionally with a
note.

---

## 17. Messages to families

A red flag is only worth raising if it reaches someone. Three kinds of message
come out of the pipeline automatically.

| Message | Goes to | When |
|---|---|---|
| **Referral** | the family | a visit classifies red |
| **Alert** | the supervising ANM | a new red flag is raised |
| **Reminder** | the family | the day before the follow up that visit booked |

The referral text is the risk agent's own advice to the family, written in the
language the visit was recorded in. It is addressed from the worker by name,
because that is who the family knows.

**Delivery is simulated, and the system says so everywhere.** The API returns
`simulated: true`, the dashboard carries a banner, and the phone shows a line
saying the message was written and queued but not actually delivered. A
screenshot of the outbox cannot be mistaken for proof that a family was
contacted.

The reason is not cost. WhatsApp Cloud API is free for the first 1,000 service
conversations a month. It needs a verified Meta Business account, a registered
sender number, and template approval for anything sent outside a 24 hour reply
window. None of that can be arranged for a project at this stage. So everything
up to the final hop is real, and the final hop is a stub that a single setting
switches over.

Two behaviours worth knowing:

**A patient with no phone still gets a message written.** Most infants on a
roster have no number of their own. The message is marked "No phone number,
tell them in person" and stays visible, because somebody still has to carry it
to the house. Silently dropping it would be the worst option.

**A repeat red does not re-alert the supervisor.** If a patient is still red on
the third visit, the ANM does not get a third identical alert about a case she
already has open. The family is still told again each time, because they have
to act each time.

Messages can be sent one at a time, or all the due ones at once, from the
dashboard.

---

## 18. Working offline

This is the feature the whole app is shaped around. In the villages this is
built for, no network is the normal state, not the exception.

**What works with no signal:**

- the roster opens, from the cache
- a patient profile opens in full, from the cache
- the visit plan opens, from the cache
- the mic works and records
- a visit can be recorded and saved

**What happens to the visit.** It is written to a local queue on the phone
before anything is sent anywhere. The worker sees it land in the queue with a
count. She can keep working and record ten more.

**When signal returns**, WorkManager wakes the app and uploads the queue. It
does not poll. The system tells it the moment a network appears, which means it
works even if she has closed the app, locked the phone and walked to the next
village.

**Nothing is lost and nothing is duplicated.** Every visit carries a
`client_uuid` generated on the phone. If an upload half succeeds and is retried,
the server recognises the id and returns the visit it already has instead of
creating a second one.

Local storage keeps two kinds of thing apart on purpose:

- **Cached patients and schedule** are a mirror of server data. They can be
  thrown away and rebuilt at any time.
- **Pending visits are the only copy.** Work the worker has done that the
  server has never seen. A row here is a home visit. It is never cleared until
  the server confirms it has it.

There is a queue screen showing what is waiting, and she can trigger a sync by
hand if she wants to.

---

## 19. Speech to text when offline

Online, the app uses Android's own speech recogniser. It is free, needs no API
key, handles Hindi and Indian English natively, and on most phones keeps
working with the network off once the Hindi language pack is installed.

When there is no network and no on device recogniser, the app records the audio
instead and queues the file. That audio is transcribed on the server when it
uploads.

Server side transcription has four options, set by one setting:

| Provider | What it is |
|---|---|
| `bhashini` | The Government of India language platform, `ai4bharat/conformer-hi-gpu--t4` for Hindi. Free after registering. The default. |
| `groq_whisper` | Groq's `whisper-large-v3`. |
| `whisper` | faster-whisper, running fully locally. |
| `mock` | A canned transcript, for development with no setup. |

Bhashini is the default because it has the best provenance for a system meant
for NHM use. The audio stays inside government infrastructure. If Bhashini is
unreachable the app falls back to Whisper automatically and logs a warning.

One practical detail: the phone records AAC, which is about 13 KB for a short
visit instead of 190 KB for WAV. That matters on a slow rural connection.
Bhashini will not accept AAC, so the server converts it to 16 kHz mono WAV
before sending. The small file stays on the wire, the conversion happens where
bandwidth is free.

---

## 20. Hindi and English

The worker picks her language at sign in, and the whole app follows.

**Every screen, every label, every button, every error message.** Not a partial
translation.

This includes the parts that are generated, not just the fixed text. When the
language is Hindi, the agents write the rationale, the actions, the follow up
reason, the summary and the danger signs in Hindi too. So does the message to
the family.

**Abbreviations stay in Latin script on purpose**: BP, Hb, SpO2, MUAC, ANC,
IFA, TT, EDD. These are what an ASHA is trained on and what her paper registers
already use. "BP 168/112" reads the same in either language, and translating it
would make it harder, not easier.

**Danger signs get a deterministic backstop.** The risk prompt asks for danger
signs in Hindi and names the field explicitly. The model complies most of the
time and then, on some visits, returns the reasoning in Hindi and the sign list
in English. That put "pedal oedema" in the middle of an otherwise Hindi alert.
Prompting harder had already been tried, so there is a glossary underneath:

- a known sign is rendered in Hindi
- an unknown sign is left in English rather than half translated, because
  "तेज़ सर दर्द with photophobia" helps nobody
- anything the model already got right passes through untouched
- numbers and abbreviations are left alone

The same table read backwards gives the duplicate check a language independent
key, so the model's "blurred vision" and the rule engine's Hindi label for the
same finding are recognised as one sign instead of both being shown.

The translation is implemented as a Compose `CompositionLocal` rather than
Android's `values-hi/strings.xml`. That was deliberate: the language is a
choice the user makes inside the app, not the phone's system locale, and it has
to reach agent output as well as UI text.

---

## 21. The supervisor dashboard

A web page served by the backend itself at `/dashboard`. No build step, no
separate host, no CORS exemption. It reaches the API at whatever address the
browser used to load it.

Two audiences, one set of screens:

| | ANM | BMO |
|---|---|---|
| Scope | the ASHAs she supervises | every worker in the block |
| Question it answers | "who needs me today?" | "which areas are drifting?" |
| Scoped by | reporting line | geography |

A BMO is scoped by **block, not reporting line**. PHCs and ANMs get
reorganised, and a dashboard that silently lost half a block after a transfer
would be worse than useless.

The page shows:

- **Counts**: patients, high risk, open escalations, overdue visits, visits in
  the last 7 days, and how many results came from rules alone
- **Risk spread** across the whole scope, as a bar
- **Open escalations**, with the reason and an acknowledge button
- **Messages to families**, the outbox, with the full text of each message, its
  status, and buttons to send one or send all that are due
- **Field workers**, ordered by what needs attention: open escalations first,
  then overdue visits, then high risk patients. Each row shows patient counts,
  activity, and days since that worker last recorded anything
- **Areas**, a village roll up with a status of Needs attention, Visits overdue
  or On track

Two numbers on this page are less obvious than they look:

**Days since last activity** is the single most useful signal that somebody has
stopped working, or that their phone has stopped syncing. It is asked of the
database separately from the activity window, so a worker whose last visit was
three weeks ago reads as "21 days ago" and not as "no visits recorded". A
supervisor acts very differently on those two.

**Rule-only results** tells a supervisor how much of what they are reading was
produced without the model. Without it, a degraded day looks like a healthy
one.

Field workers are refused the dashboard with a 403. They use the phone app.

---

## 22. Who can see what

Four roles:

| Role | Sees |
|---|---|
| **ASHA** | only the patients assigned to her |
| **ANM** | herself plus the workers who report to her |
| **BMO** | every active worker in his block |
| **admin** | everything |

Every read and write of patient data goes through one function,
`visible_worker_ids`. Routers never build their own patient filters. That means
there is exactly one place in the codebase where the rule "a worker only sees
her own people" can be got wrong, and it is tested directly.

Asking for another worker's patient by id returns 404, not 403. A worker should
not be able to learn that a patient exists by being told she is not allowed to
see them.

The same scoping covers visits, schedules, escalations and messages.

Actions that matter are written to an audit log: who did it, what, to which
record, and when.

---

## 23. When the model is unavailable

The API can be down, rate limited, or out of daily quota. The app does not
simply fail.

Each agent has a deterministic fallback. If the model is unreachable:

- extraction falls back to keyword matching and number parsing
- risk falls back to the rule engine's own verdict
- scheduling falls back to the routine interval for that patient type

The visit still produces a real answer, which for a danger sign case is the
same answer, because the rules would have raised it anyway.

**The degradation is always visible.** The visit records which steps fell back.
The app shows a warning on the result. The dashboard counts them. At no point
is rule generated output allowed to look like live reasoning.

This is also why one of the test suites runs entirely offline. When Groq's
daily token limit is reached, the integration tests go quiet, and that is
exactly when you want a suite that does not need an API to still tell you the
truth.

---

## 24. Server address settings

On the emulator the backend is at `10.0.2.2:8010`. On a real phone that address
means nothing, and the app has to be told the laptop's address on the Wi-Fi.

So the server address is a setting, not a build constant:

- it defaults correctly by device type, emulator or phone, so a fresh install
  works without being configured
- it can be changed from the sign in screen
- it has a test button that reports what actually went wrong, whether that is
  the wrong address, a firewall, or the server not running
- the address is normalised, so typing `192.168.1.5:8010` works as well as the
  full URL

This exists because the first attempt at running on a physical phone failed on
exactly this, and the failure was invisible.

---

## 25. Design and look

Green, white and black. Green carries identity, black and white carry
structure, and saturated colour is kept for the risk levels so that red means
one thing only.

Decisions that shaped it:

- **One font throughout**, at sizes larger than a typical app. Users may be
  reading in sunlight, in a hurry, without glasses.
- **Risk is never colour alone.** Every risk indicator has a word next to it.
  Colour blindness and glare both make colour unreliable.
- **The mic button is the biggest thing on the visit screen.** It is the main
  action and it should be hittable without looking.
- **The evidence is collapsed.** Guideline citations matter, but not before the
  action.
- **No chat interface.** The worker is not conversing with an assistant. She is
  recording a visit, and the app answers in one shot.

The web dashboard uses the same palette, so the two halves look like one
system.

---

## 26. Tests

Six suites. The first five need the server running. The last one does not need
anything.

| Suite | Covers |
|---|---|
| `scripts.smoke_test` | 40 checks across the whole worker journey: sign in, roster isolation, filters, profiles, Aadhaar, a typed visit, a red visit, escalation, the plan, guidelines |
| `scripts.test_risk_downgrade` | risk moves in both directions, not only up |
| `scripts.test_escalations` | one open alert per patient, not duplicates |
| `scripts.test_dashboard` | 15 checks on supervisor scoping, including that the two ANM scopes do not overlap and the BMO's is exactly their union |
| `scripts.test_messages` | the outbox: who is told, who cannot be, de-duplication, and that one worker can neither read nor send another's messages |
| `scripts.test_glossary` | 87 checks on Hindi danger sign translation, with no network and no API key |

Some checks exist because of a real bug that was found and fixed:

- a worker gets 404, not 403, on someone else's patient
- an offline retry returns the same visit and does not create a second one
- a worker whose last visit was weeks ago still shows a real date
- a message with no phone number is never marked as sent
- the guideline sources really are on government domains

`test_messages` reports its Hindi check as **skipped, naming the quota**, when
the model is unavailable, rather than failing. A test that goes red because the
API ran out of tokens is a misleading signal.

---

## 27. Demo data and reset

The seed builds a realistic block: one BMO, two ANMs running two PHCs, four
ASHA workers, and 158 patients spread across four villages with pregnancies,
infants, immunisation records, conditions and visit history.

The two ANM scopes are deliberately separate and the BMO's is exactly their
union, so the hierarchy can be demonstrated rather than just claimed.

`scripts.demo_reset` puts the demo worker's roster back to a known state: it
clears her visits, follow ups, escalations and outbox, then sets up three named
patients for the walkthrough. It is safe to run repeatedly and it only touches
the demo worker, leaving the other workers' data alone.

Sign in details for a demo:

| Phone | PIN | Role | Sees |
|---|---|---|---|
| `9000000002` | `1234` | ASHA, Sunita Devi | her own 43 patients, in the phone app |
| `9000000001` | `1234` | ANM, Dr. Anita Meena | Sanganer PHC: 2 workers, 83 patients |
| `9000000006` | `1234` | ANM, Dr. Priya Yadav | Phagi PHC: 2 workers, 75 patients |
| `9000000000` | `1234` | BMO, Dr. Rajesh Sharma | the whole block: 4 workers, 158 patients |

---

## 28. What it does not do

Stating the limits is part of the documentation, not a footnote to it.

- **Messages are simulated.** The queue, the scheduling, the language handling
  and the undeliverable cases are all real. The final hop to WhatsApp is a
  stub, for the account verification reason above.
- **Aadhaar is not real e-KYC.** Structure, checksum, consent and hashing are
  real. Live UIDAI authentication is not available to a project like this.
- **Local patient data is not encrypted at rest.** A real deployment should use
  SQLCipher. Cloud backup and device transfer are already switched off so the
  data cannot leave the phone that way.
- **The auth token lasts 14 days**, which trades security for not stranding a
  worker mid round.
- **Two IMNCI PDFs are scanned images** with no text layer, so they are not
  indexed. The IMNCI Chart Booklet covers the same ground.
- **No HMIS report export.** The dashboard answers the day to day questions,
  but district reporting formats are not generated.
- **Free tier limits are real.** Groq's free tier has a daily token ceiling.
  Past it, every visit comes back rules only. See
  [SCALING.md](SCALING.md) for what to buy first.
