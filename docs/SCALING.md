# Cost and scaling

SevakAI runs entirely on free tiers today. This document records what those
tiers actually cost in throughput, where they break, and what to buy first when
they do.

---

## What a visit costs

Measured, not estimated — see `total_tokens` on any visit response.

| Stage | Model | Tokens | Time |
|---|---|---|---|
| Extraction | `openai/gpt-oss-120b` (reasoning: low) | ~1,300 | ~1.5 s |
| Risk classification | `openai/gpt-oss-120b` (reasoning: medium) | ~1,500 | ~2 s |
| Scheduling | `openai/gpt-oss-120b` (reasoning: low) | ~1,100 | ~1.5 s |
| **Total** | | **~3,900** | **~4 s** |

Retrieval (ChromaDB) is local and free. Speech recognition is on-device and
free. The only metered resource is the LLM.

### Note on reasoning models

`gpt-oss-120b` spends hidden reasoning tokens that count against `max_tokens`.
At `reasoning_effort: medium` the risk agent burns ~850 reasoning tokens; at
`low` it is ~250. Extraction showed no measurable accuracy loss at `low`
(1.5 s vs 5–10 s), so only the clinically load-bearing risk step pays for
medium. This is set per-agent in `app/agents/`.

---

## Where the free tier ends

Groq's free tier, as observed from the API's own rate-limit headers:

| Limit | Value | What it means here |
|---|---|---|
| Tokens / minute | **8,000** | ~2 visits per minute sustained |
| Requests / day | 1,000 | ~330 visits per day |

**The per-minute token cap is the binding constraint, not the daily one.**

In practice this is not a problem. A real ASHA home visit takes 5–10 minutes,
so a single worker generates at most ~12 visits an hour — an order of magnitude
below the ceiling. A worker never waits: an individual visit completes in ~4
seconds regardless.

It matters in exactly two situations:

1. **Demos that submit several visits back to back.** Two visits fill the
   minute; the third queues 20–30 s. Pace scripted demos ~30 s apart.
2. **Many workers sharing one API key.** The cap is per project, not per user.
   Roughly 5–10 concurrent workers exhaust it.

The app degrades honestly rather than failing: when the cap is hit, the
`ResilientLLM` retries once respecting the provider's own suggested cooldown,
then falls back to deterministic rules, and the affected step is shown to the
worker as a warning on the result screen.

---

## What to buy first

In the order the constraints actually bite.

### 1. Groq paid tier — the cheapest fix, and the only one needed for a pilot

Same code, same models, one environment variable unchanged. Paid tier lifts the
token-per-minute cap by roughly two orders of magnitude.

At ~3,900 tokens/visit and `gpt-oss-120b` pricing (~$0.15/M input,
~$0.60/M output at the time of writing), a visit costs on the order of
**₹0.10–0.20**. A district with 200 ASHA workers doing 10 visits a day each is
~2,000 visits/day — roughly **₹300/day**, or under ₹10,000/month, for a
population of a few hundred thousand.

For context, that is materially less than the incentive paid to a single ASHA
worker for a single month. Cost is not the obstacle to scaling this; procurement
is.

### 2. Postgres instead of SQLite

SQLAlchemy models are already portable — change `DATABASE_URL` and run the
migration. SQLite is fine to roughly a single block's caseload; it becomes the
bottleneck when several ANMs and a district dashboard read concurrently.

### 3. Managed vector store, or pgvector

ChromaDB's local persistence is fine for one server and a 594-chunk corpus. If
the corpus grows to the full NHM library (thousands of pages) or the backend is
replicated, move to pgvector — which also removes a separate service, since
Postgres is already there.

### 4. Bhashini for speech

Android's on-device recogniser is free and works offline, but it is trained on
mainstream Hindi and struggles with strong regional accents and code-mixing.
[Bhashini](https://bhashini.gov.in) is the Government of India's own language
platform, covers 22 scheduled languages, and is the politically and technically
correct answer for a government-facing deployment. It requires registration
rather than payment.

Groq's `whisper-large-v3` (already wired for offline-queued audio) is the
commercial fallback and is noticeably better than the on-device recogniser on
accented, code-mixed speech.

---

## Alternatives considered, and why not

| Option | Verdict |
|---|---|
| **Google Gemini free tier** | Used in the earlier prototype and abandoned. 20 requests/day — about 6 visits — which is not enough to develop against, let alone demo. Paid Gemini Flash is a reasonable alternative to paid Groq; the free tier is not. |
| **OpenAI / Anthropic APIs** | Strong models, no free tier. Sensible if the project is already paying and wants the best available clinical reasoning; roughly 5–20× the per-visit cost of `gpt-oss-120b`. |
| **OpenRouter free models** | One key, several free models. Rate limits vary per model and free models get rotated or deprecated without notice — poor foundation for something a health worker depends on. |
| **Self-hosted Llama / Ollama** | Zero marginal cost and full data residency, which is a genuine advantage for health data under Indian law. Needs a GPU server; makes sense at district scale, not for a prototype. Worth revisiting if data-residency requirements are imposed. |
| **Fine-tuning a small model** | Premature. The prompts plus RAG grounding are doing the work, and there is no labelled corpus of ASHA visit transcripts to fine-tune on. Collecting that corpus is the prerequisite, and this app would be the thing that collects it. |

---

## The honest summary

Nothing in this system is architecturally blocked by the free tier. Every
provider sits behind an interface with a deterministic fallback, and moving to
paid infrastructure is a configuration change rather than a rewrite. The free
tier constrains **concurrency**, not capability — and at the throughput a real
ASHA worker generates, it is already sufficient for a single-worker pilot.
