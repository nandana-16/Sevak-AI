# Demo runbook

A rehearsable ~8 minute walkthrough on the Android emulator.

Everything below has been executed end to end on this machine. The timings are
measured, not estimated.

---

## Before you start (5 minutes, do this once)

### 1. Backend

```bash
cd backend
./venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8010
```

Leave it running in its own window — **you will point at this log during the
demo** to show the Groq calls happening live.

### 2. Reset to the demo state

In a second terminal:

```bash
cd backend
./venv/Scripts/python.exe -m scripts.demo_reset
```

This guarantees the three patients the script below refers to and wipes any
visits from a previous rehearsal, so you can run the demo again immediately.
It prints a valid Aadhaar number for the registration scene.

### 3. Emulator

```bash
"$LOCALAPPDATA/Android/Sdk/emulator/emulator.exe" -avd sevakai
```

Then install and launch:

```bash
cd android && ./gradlew :app:assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n in.sevakai.app/.MainActivity
```

### 4. Pre-flight check

- [ ] Backend log shows `Guideline chunks indexed: 594`
- [ ] App opens on the sign-in screen
- [ ] Tap **Server** → **Test connection** → *"Connected … 594 guideline chunks"*
- [ ] Backend window and emulator both visible on screen at once

---

## ⚠ The one thing that can break this

**Groq's free tier allows 8,000 tokens per minute, and a visit costs ~3,900.**

That is **two visits per minute**. If you submit a third within the same
minute, it will sit for 20–30 seconds before returning. It will still work —
nothing fails — but the pause is awkward on stage.

This runbook submits **three visits** and deliberately spaces them with talking
in between. Do not rush ahead of the script. If you do stall, say so plainly:
*"that's the free-tier rate limit — the scaling doc has the numbers"* — it is a
credible answer, not an excuse.

---

## The walkthrough

### Scene 1 — The roster (45 sec)

Sign in: **9000000002** / PIN **1234**.

> "This is Sunita Devi, an ASHA worker in Bagru. These are the 43 patients
> assigned to her — and only hers. This isn't a UI filter; the server refuses
> to return anyone else's patients."

Point at:
- **Sorted riskiest first** — the eight amber cards are at the top; that's
  the order she'd actually walk her round in. Nobody is red yet.
- **The grey box on each card** — the last visit's summary. "She knows what
  happened last time before she knocks on the door."
- **Every risk chip has a word, not just a colour** — "red/green is exactly the
  pair a colour-blind reader can't separate, and it's the most important thing
  on the screen."

Tap the **filter pills** — *Pregnant*, *High risk* — and the **search box**.

---

### Scene 2 — A patient profile (45 sec)

**Type `Roshni` in the search box** and open **Roshni Solanki** (pregnant, currently green).

> "Forty-three patients — she searches, the same as you would."

> "Everything the worker needs before the visit, in the order she needs it."

Point at, top to bottom:
- **Last visit note** at the very top.
- **Aadhaar shown as `XXXX XXXX 8454`** — "we never store the number. Only a
  salted one-way hash and the last four digits."
- **Pregnancy block** — 32 weeks, EDD, G2P1, ANC visits, last Hb and BP.
- Scroll to **immunisation** and **medical history** — "these sections appear
  based on the patient's category. An infant profile looks different."

---

### Scene 3 — The hero moment: voice → red flag (2.5 min)

Tap **Record visit**.

> "She presses one button and just talks, in Hindi, the way she actually
> speaks."

**Then use the typed path** (see *Voice on the emulator* below for why):
switch to the **Type** tab, or scroll to *Extra notes*, and enter:

```
Roshni ko teen din se bahut tez sar dard hai aur aankhon ke aage dhundla dikh raha hai. Pair me bahut sujan hai. Bachcha kal se kam hil raha hai.
```

Then in **Measurements**, type **BP systolic 168** and **BP diastolic 112**.

> "Note the measurements are a separate typed field. Anything a human types
> into a labelled box overrides anything the model heard — a number typed by a
> person is better evidence than a number recovered from noisy speech."

Tap **Save visit**. It takes about 4 seconds.

**While it runs, point at the backend log** — three `POST … groq.com` lines
appear. "That's the three agents: extraction, risk classification, scheduling."

When the result appears, walk it top to bottom:

| On screen | What to say |
|---|---|
| **Go to hospital today** (red) | "Not 'red'. The action." |
| The plain-language reason | "Written for a worker with limited formal education. No jargon." |
| **Danger signs found** | "It read *sar dard* as headache, *dhundla* as blurred vision, *pair me sujan* as pedal oedema — out of Hinglish, not English." |
| **What to do now** | "Ordered by urgency, and only things an ASHA can personally do — she can't prescribe." |
| **Next visit** | "Tomorrow. Automatically on her plan." |
| **Based on NHM guidelines** → *tap to expand* | **This is the moment.** "That's the actual text of the PMSMA High Risk Conditions document, page 3, with the page number. Not the model's memory — retrieved from the real PDF." |

> "And the safety net: those thresholds also run as plain code. If the model had
> said yellow, the rules would still have forced red, because 168/112 crosses
> the PMSMA severe-hypertension line. The model can add nuance, but it can never
> talk the system *down* below a documented danger sign."

---

### Scene 4 — The plan and the escalation (45 sec)

Back to the roster (clear the search). **Roshni is now at the top, in red.**

> "Her risk updated from that visit. And it moves both ways — if she's well next
> week, she goes back to green. A permanent red label would make the colour
> meaningless."

Tap the **calendar icon** → the visit plan.

> "Her follow-up is already scheduled for tomorrow, marked high priority.
> Nobody typed that in."

Try **snooze** on a red row — it is refused.

> "A high-risk follow-up can't be postponed. The server rejects it."

Search **`Aarav`** and open **Aarav Rathore** (infant) to show the different profile shape.

> "Different category, different record: birth weight, gestation, MUAC, and the
> National Immunization Schedule with the 14-week doses flagged overdue."

---

### Scene 5 — Offline (2 min) — *the part people remember*

> "Now the real problem. She's in a village with no signal."

**Turn off the network** — in the emulator's side toolbar open **Extended
controls (⋯) → Cellular → Data status: Denied**, and toggle Wi-Fi off in the
emulator's notification shade. Or, faster, from a terminal:

```bash
adb shell svc wifi disable && adb shell svc data disable
```

Search **`Bhavna`** and open **Bhavna Chauhan**.

> "The profile still opens. This is the copy saved on the phone —" *(point at
> the grey offline banner)*.

**Record visit** → Measurements → **BP systolic 142** → **Save visit**.

> "No error. No lost work."

Point at *"Saved on this phone. It will be sent automatically when you have a
network."*

Tap **Done**, then the **cloud icon** on the roster.

> "Here's the queue. She can see her work is safe — one waiting, with the reason
> it hasn't gone yet. A silent background queue would be technically fine and
> completely untrustworthy to someone who just walked five kilometres."

**Turn the network back on:**

```bash
adb shell svc wifi enable && adb shell svc data enable
```

Wait ~15 seconds and stay on the queue screen.

> "Nothing pressed. WorkManager wakes up the moment a network appears."

The row flips to **Sent**, with the risk chip and summary that came back.

> "And it came back *Watch*, not *high risk* — 142 is raised, but below the
> 160/110 severe threshold. The guideline distinction, applied automatically."

---

### Scene 6 — Registration and Aadhaar (1 min)

Roster → **Register**.

Type a wrong Aadhaar first: **1234 5678 9012**

> "Rejected — Aadhaar numbers never start with 0 or 1."

Now type the valid number `demo_reset` printed (e.g. **4567 8901 2341**).

> "Accepted. That's the Verhoeff checksum — the same algorithm UIDAI uses. It
> catches every single-digit typo and every transposition."

Point at the consent checkbox.

> "Registration is refused without recorded consent. And we store only the hash
> and last four digits."

Be ready for the obvious question:

> **"Is this real Aadhaar verification?"**
> "No, and we're explicit about that. Real e-KYC needs an AUA/KUA licence from
> UIDAI — there's no public API and no legitimate way for us to call one. So we
> do the parts that can be done honestly offline. Swapping in a licensed
> integration means replacing one function; nothing else changes. The two routes
> that *don't* need a licence are UIDAI Offline e-KYC XML and ABHA under ABDM —
> that's in `docs/AADHAAR.md`."

---

### Closing (30 sec)

> "Three agents on a real corpus of eight Government of India guideline
> documents — 594 passages, every recommendation traceable to a page. Built to
> work with no network. About four seconds and two-tenths of a rupee per visit."

---

## What to say into the mic

Android's `hi-IN` recogniser returns **Devanagari**, not romanised Hinglish, and
the extraction prompt reads both. Speak naturally at a normal pace — do not
over-enunciate, it makes recognition worse.

### The hero case — Roshni Solanki (turns red)

> रोशनी को तीन दिन से बहुत तेज़ सर दर्द है और आँखों के आगे धुंधला दिख रहा है।
> पैर में बहुत सूजन है। बच्चा कल से कम हिल रहा है।

*Roshni ko teen din se bahut tez sar dard hai aur aankhon ke aage dhundla dikh
raha hai. Pair mein bahut sujan hai. Bachcha kal se kam hil raha hai.*

("Three days of severe headache and blurred vision. A lot of swelling in the
feet. The baby has been moving less since yesterday.")

Then **type** BP **168** / **112** in Measurements. Expect: red, four danger
signs, PMSMA citations, follow-up tomorrow.

### A routine case — Bhavna Chauhan (stays green)

> आज रूटीन जाँच थी। कोई शिकायत नहीं है। खाना ठीक खा रही है और आयरन की गोली
> रोज़ ले रही है। कोई दर्द, बुखार या सूजन नहीं है।

*Aaj routine jaanch thi. Koi shikayat nahi hai. Khana theek kha rahi hai aur
iron ki goli roz le rahi hai. Koi dard, bukhar ya sujan nahi hai.*

Type BP **112** / **74**. Expect green, and a routine follow-up weeks out —
useful to show immediately after the red case, because it proves the classifier
is reading the findings rather than flagging everything.

### An infant case — Aarav Rathore (turns red)

> बच्चा दो दिन से दूध नहीं पी रहा है। बहुत सुस्ती है और छूने पर ठंडा लग रहा है।
> साँस तेज़ चल रही है।

*Bachcha do din se doodh nahi pi raha hai. Bahut susti hai aur chhoone par
thanda lag raha hai. Saans tez chal rahi hai.*

("Not feeding for two days. Very lethargic, cold to the touch. Breathing fast.")

Expect red against IMNCI/HBNC newborn danger signs — a different guideline
document from the pregnancy case, which is worth pointing out.

### In English instead

Tap the **English** pill next to the mic if the Hindi pack is missing:

> "She has had a severe headache for three days with blurred vision. There is a
> lot of swelling in her feet, and the baby has been moving less since
> yesterday."

### Speak the symptoms, type the numbers

Both work — the prompt handles Hindi numerals, including that
"एक सौ अड़सठ बटा एक सौ बारह" is 168/112 and not 158/112, which it originally
got wrong. But a misheard vital sign is the one error that would genuinely
matter, so type them.

That is not a workaround, it is the design: values typed into the Measurements
fields override anything the model heard. Say so out loud —

> "The story is spoken, the numbers are typed. A number a human put in a
> labelled box beats a number recovered from noisy audio, so the typed value
> always wins."

---

## Voice on the emulator

**The emulator has no Hindi offline language pack** — the log shows
`SodaSpeechRecognizer: Failed to get language pack of required locale: error 12`.
It falls back to Google's *online* recogniser, which needs both a network and
the emulator's virtual mic wired to your laptop's microphone.

To try it: **Extended controls (⋯) → Microphone → "Virtual microphone uses host
audio input"**, then tap the mic and speak Hindi into your laptop.

**Recommendation: don't stake the demo on it.** Type the Hinglish text instead
— typing is a first-class input path in this app, not a workaround, and the
extraction pipeline is byte-for-byte identical either way. If someone asks
whether the voice works, say:

> "Yes — on-device recognition, which also works offline once the language pack
> is installed. The emulator doesn't ship the Hindi pack, so on a real phone
> this is the mic; here I'm typing the same sentence into the same field."

If you have a physical phone, `bash scripts/run-on-phone.sh` and demo the mic
there — that's where it genuinely shines.

---

## If something goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| Sign-in says "Cannot reach 10.0.2.2:8010" | Backend not running | Start uvicorn; then **Server → Test connection** |
| A visit takes 30 s | Groq rate limit | Expected. Say so; wait. It completes. |
| Result shows a yellow "worked out by fixed rules" banner | Groq unreachable or key exhausted | Honest fallback working as designed. Point at it: "it tells you when it isn't the model." |
| Queue row stuck on "Will retry" | No network on device | `adb shell svc wifi enable` |
| Roster is empty | Wrong worker, or DB not seeded | `python -m app.seed --reset` then `python -m scripts.demo_reset` |
| App shows stale data after `demo_reset` | Cached on device | `adb shell pm clear in.sevakai.app`, sign in again |

**Reset between rehearsals:**

```bash
cd backend && ./venv/Scripts/python.exe -m scripts.demo_reset
adb shell pm clear in.sevakai.app
```

---

## Backup: no emulator, no phone

If everything visual fails, the pipeline still demos from a terminal:

```bash
cd backend && ./venv/Scripts/python.exe -m scripts.try_pipeline
```

Four pre-written Hinglish cases through the real agents, with the risk level,
danger signs, actions and guideline citations printed. Not as impressive, but
it proves the system works and it takes 15 seconds to start.
