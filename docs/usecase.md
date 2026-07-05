Let me research India-specific clinical documentation patterns before designing the architecture.Now I have the full picture. Let me design the GCP architecture grounded in the realities of an Indian OPD.

The Indian clinical context is fundamentally different from the US/EU ambient scribe products, and that's actually your competitive edge. Let me lay out the design.

---

## The Indian doctor's documentation problem

The numbers tell the story. Time-motion studies at Indian OPDs show an extreme mismatch: total OPD time per patient averages 2 hours but actual consultation time is just 3 minutes. A busy OPD doctor sees 50-100+ patients daily. Most documentation happens on paper — handwritten prescriptions with Indian drug brand names (Dolo 650, Crocin, Zifi 200, Augmentin), Indian disease patterns (dengue, typhoid, TB, malaria), and a mix of English medical terms with Hindi/regional language patient descriptions. The result: documentation is either skipped entirely (just a prescription scribble) or done hours later from memory.

Your system needs to handle three India-specific realities that Western ambient scribes don't:

**Hindi-English code-switching (Hinglish):** A doctor says "Patient ko 3 din se fever hai, Dolo 650 liya but fever persist kar raha hai, urine culture send karo." Your STT needs to handle this seamlessly.

**Indian drug brands:** The doctor prescribes "Tab Augmentin 625 BD × 5 days" not "Amoxicillin-Clavulanate." Your NER layer needs an Indian pharmacopeia mapping.

**3-minute consultation window:** There's no time for a 15-minute ambient recording. The system must work with ultra-short, dense, rapid-fire consultations — often with the doctor dictating while examining.Now let me break down each layer of the architecture in detail.

---

### Layer 1 — Audio capture

The entry point is the doctor's phone. In an Indian OPD, the doctor won't wear a lapel mic or use a dedicated hardware device — they'll use their phone. The Streamlit/React frontend provides a "Start Recording" button. The doctor taps it at the start of a consultation and taps "Stop" when done (typically ~3 minutes for a routine OPD visit). The audio is captured as WebM/Opus and uploaded to a GCS staging bucket.

For the hackathon demo, skip live recording entirely. Pre-record 3-4 sample consultations (you can role-play these yourself in Hinglish) covering common Indian OPD cases: viral fever with Dolo prescription, UTI with Cefixime, hypertension follow-up with Telmisartan, and a diabetic review with Metformin dose adjustment. This gives you realistic demo material without needing to solve the audio capture UX.

---

### Layer 2 — Speech-to-Text (Chirp 3)

This is where GCP gives you a real advantage. Chirp 3 on Cloud Speech-to-Text V2 supports automatic language detection (handles Hinglish without pre-specifying the language), speaker diarization (separates doctor from patient), and has strong performance on Indian accents — Google has the largest repository of Indian linguistic data, and Chirp uses self-supervised learning on millions of hours of unlabelled audio including Indian dialects.

The config you'd use:

```python
config = cloud_speech.RecognitionConfig(
    auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
    language_codes=["hi-IN", "en-IN"],  # Hinglish
    model="chirp_3",
    features=cloud_speech.RecognitionFeatures(
        enable_automatic_punctuation=True,
        diarization_config=cloud_speech.SpeakerDiarizationConfig(
            min_speaker_count=2,
            max_speaker_count=3,  # doctor + patient + attendant
        ),
    ),
)
```

The output is a diarized transcript with speaker labels and timestamps. For the hackathon, if Chirp 3 diarization isn't available in your region, fall back to Chirp 2 or Whisper — you can run `openai/whisper-large-v3` locally or on a Cloud Run container. Whisper has excellent Hinglish code-switching support.

---

### Layer 3 — The agent pipeline (Cloud Run)

This is the core. Four agents running on Cloud Run, orchestrated with either Google ADK (if you want the GCP-native story for the hackathon pitch) or LangGraph (if you want faster development). Each agent is a Gemini 2.5 Flash call with a specialized system prompt.

**Agent 1 — Transcript Structurer.** Takes the raw diarized transcript and produces a clean, structured version. It labels each turn as `[DOCTOR]` or `[PATIENT]`, normalizes Hinglish (transliterates Hindi portions while preserving medical terms in English), and segments the conversation into phases: chief complaint, history-taking, examination, diagnosis, and prescription. The system prompt includes examples of Indian OPD conversations.

**Agent 2 — Medical Entity Extractor.** This is where the India-specific intelligence lives. The agent extracts structured entities from the transcript using Gemini's structured output (JSON schema):

```json
{
  "chief_complaint": "Fever × 3 days, not responding to Dolo 650",
  "symptoms": ["fever", "body_ache", "loss_of_appetite"],
  "vitals": {"temp": "101.2°F", "bp": "120/80"},
  "medications_current": [
    {"brand": "Dolo 650", "generic": "Paracetamol 650mg", "frequency": "TDS"}
  ],
  "medications_prescribed": [
    {"brand": "Augmentin 625", "generic": "Amoxicillin+Clavulanate", "dose": "625mg", "frequency": "BD", "duration": "5 days"},
    {"brand": "Pan-D", "generic": "Pantoprazole+Domperidone", "frequency": "OD", "duration": "5 days"}
  ],
  "investigations_ordered": ["CBC", "Dengue NS1", "Widal"],
  "provisional_diagnosis": "Acute febrile illness, R/O Dengue",
  "icd10_codes": ["R50.9", "A90"]
}
```

The system prompt includes an Indian drug brand → generic mapping for the top 200 prescribed drugs in India (Dolo, Crocin, Zifi, Augmentin, Pan-D, Shelcal, Ecosprin, Glycomet, Telma, Amlodip, etc.). This is a simple lookup table baked into the prompt — not a separate database.

**Agent 3 — SOAP Note Generator.** Takes the extracted entities and produces a structured SOAP note formatted for Indian clinical practice:

```
─── SOAP NOTE ───────────────────────────
Patient: [Name], [Age]/[Sex]
Date: 05-Jul-2026 | OPD Visit

SUBJECTIVE
Chief Complaint: Fever × 3 days, not responding to Dolo 650
HPI: Patient reports continuous fever with body ache and
loss of appetite. Self-medicated with Paracetamol 650mg TDS
for 2 days without improvement. No rash, bleeding, or
joint pain. No travel history.

OBJECTIVE
Vitals: Temp 101.2°F, BP 120/80, PR 92/min
General: Febrile, no pallor/icterus/cyanosis/edema
Abdomen: Soft, no hepatosplenomegaly

ASSESSMENT
Acute febrile illness — R/O Dengue, R/O Enteric fever
ICD-10: R50.9, A90

PLAN
Rx:
1. Tab Augmentin 625mg — 1 tab BD × 5 days
2. Tab Pan-D — 1 tab OD (before breakfast) × 5 days
3. Tab Dolo 650mg — SOS for fever > 101°F
Ix: CBC, Dengue NS1 Ag, Widal test
Advice: Plenty of fluids, soft diet, avoid NSAIDs
Follow-up: After 3 days with reports
──────────────────────────────────────────
```

This template is designed for Indian OPD practice — it includes the Rx format Indian doctors and pharmacists expect (brand name + dose + frequency + duration), investigation abbreviations used in Indian labs (CBC, LFT, KFT, Widal), and follow-up instructions.

**Agent 4 — Hallucination Reviewer.** This is the self-evolving loop. The reviewer receives both the original transcript and the generated SOAP note, then checks every clinical claim against the source. It flags three categories: (a) hallucinated findings not in the transcript, (b) omitted findings that were discussed, (c) incorrect drug names or dosages. If critical issues are found, it sends the note back to Agent 3 with specific corrections. This cross-examination pattern has shown significant improvement in note accuracy in recent research.

---

### Layer 4 — Output formats

Two output paths:

**Printable prescription + SOAP note.** A PDF formatted for Indian standard: doctor's letterhead section (name, qualification, MCI/NMC registration number, clinic address), patient demographics, the SOAP note, and the prescription in the familiar Indian format. For the hackathon, render this as a styled HTML page that can be printed.

**FHIR bundle (future-ready).** A FHIR R4 `Bundle` containing `Encounter`, `Condition`, `MedicationRequest`, and `DocumentReference` resources. This makes the system ABDM-compatible (Ayushman Bharat Digital Mission) — India's national health ID initiative. For the hackathon, generate the FHIR JSON and show it in a collapsible panel to demonstrate interoperability readiness. Don't build the actual ABDM integration.

---

### Layer 5 — Storage

Cloud Storage for audio files, Firestore for session state (which step each consultation is at in the pipeline, doctor preferences, frequently prescribed drug combinations), and optionally the Healthcare API for FHIR store if you want to demo FHIR queries. For the hackathon, Firestore alone is sufficient.

---

Now let me give you the concrete build plan.