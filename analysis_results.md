# ACI-Bench Corpus: Comprehensive Data Analysis Report

This report presents a thorough analysis of the **ACI-Bench** (Ambient Clinical Intelligence Benchmark) corpus, which contains **207 full-encounter dialogue-note pairs** from clinical settings. These pairs map natural doctor-patient spoken dialogues to structured electronic health record (EHR) clinical notes.

---

## 1. Directory Structure & File Inventory

The ACI-Bench corpus is structured into two main directories:
*   [challenge_data](file:///e:/Gen%20AI%20Projects/CCCL_Hackathon/aci-bench-corpus/challenge_data): Contains standard splits (train, validation, and three independent test sets) from the MEDIQA-Chat 2023 and ImageCLEF 2023 challenges.
*   [src_experiment_data](file:///e:/Gen%20AI%20Projects/CCCL_Hackathon/aci-bench-corpus/src_experiment_data): Contains matched configurations comparing raw ASR (Automatic Speech Recognition) transcripts, human-transcribed dialogues, and human-corrected ASR transcripts across splits.

### Challenge Data File Summary
| Split Name | CSV File | Metadata File | Encounter Count |
| :--- | :--- | :--- | :---: |
| **Train** | [train.csv](file:///e:/Gen%20AI%20Projects/CCCL_Hackathon/aci-bench-corpus/challenge_data/train.csv) | [train_metadata.csv](file:///e:/Gen%20AI%20Projects/CCCL_Hackathon/aci-bench-corpus/challenge_data/train_metadata.csv) | 67 |
| **Validation** | [valid.csv](file:///e:/Gen%20AI%20Projects/CCCL_Hackathon/aci-bench-corpus/challenge_data/valid.csv) | [valid_metadata.csv](file:///e:/Gen%20AI%20Projects/CCCL_Hackathon/aci-bench-corpus/challenge_data/valid_metadata.csv) | 20 |
| **Test (CLEF Task C)** | [clef_taskC_test3.csv](file:///e:/Gen%20AI%20Projects/CCCL_Hackathon/aci-bench-corpus/challenge_data/clef_taskC_test3.csv) | [clef_taskC_test3_metadata.csv](file:///e:/Gen%20AI%20Projects/CCCL_Hackathon/aci-bench-corpus/challenge_data/clef_taskC_test3_metadata.csv) | 40 |
| **Test (ClinicalNLP Task B)** | [clinicalnlp_taskB_test1.csv](file:///e:/Gen%20AI%20Projects/CCCL_Hackathon/aci-bench-corpus/challenge_data/clinicalnlp_taskB_test1.csv) | [clinicalnlp_taskB_test1_metadata.csv](file:///e:/Gen%20AI%20Projects/CCCL_Hackathon/aci-bench-corpus/challenge_data/clinicalnlp_taskB_test1_metadata.csv) | 40 |
| **Test (ClinicalNLP Task C)** | [clinicalnlp_taskC_test2.csv](file:///e:/Gen%20AI%20Projects/CCCL_Hackathon/aci-bench-corpus/challenge_data/clinicalnlp_taskC_test2.csv) | [clinicalnlp_taskC_test2_metadata.csv](file:///e:/Gen%20AI%20Projects/CCCL_Hackathon/aci-bench-corpus/challenge_data/clinicalnlp_taskC_test2_metadata.csv) | 40 |
| **Total** | | | **207** |

---

## 2. Demographic & Metadata Profile

Analyzing patient metadata across all 207 encounters reveals a balanced demographic representation:

*   **Total Patients**: 207 (172 with explicit age recorded).
*   **Gender Distribution**:
    *   **Female**: 102 (49.3%)
    *   **Male**: 101 (48.8%)
    *   **Unknown**: 4 (1.9%)
*   **Age Distribution**:
    *   **Mean Age**: 48.3 years ($\pm$ 16.5)
    *   **Median Age**: 48.0 years
    *   **Age Range**: 3 to 100 years (representing a full spectrum from pediatric to geriatric care).

![Demographic Profile (Age and Gender Distribution)](C:/Users/bjish/.gemini/antigravity-ide/brain/72540511-a052-43b9-a601-706caf0aebe3/age_gender_dist.png)

### Dataset Source Representation
The corpus aggregates data from three different clinical audio-source subsets:
*   `aci`: 112 encounters (54.1%)
*   `virtassist`: 55 encounters (26.6%)
*   `virtscribe`: 40 encounters (19.3%)

### Clinical Indications
We extracted the top chief complaints (CC) and secondary/history complaints across the corpus:

| Top 10 Chief Complaints | Count | Top 10 Secondary Complaints | Count |
| :--- | :---: | :--- | :---: |
| 1. Back pain | 12 | 1. Hypertension | 35 |
| 2. Annual exam | 9 | 2. Depression | 17 |
| 3. Right knee pain | 8 | 3. None | 16 |
| 4. Chronic problems | 6 | 4. Diabetes | 14 |
| 5. Right knee injury | 5 | 5. Type 2 diabetes | 12 |
| 6. Joint pain | 4 | 6. Congestive heart failure | 6 |
| 7. Right elbow pain | 4 | 7. Diabetes type 2 (variant) | 6 |
| 8. Left shoulder pain | 4 | 8. Reflux | 6 |
| 9. Cough | 3 | 9. Coronary artery disease | 5 |
| 10. ER follow-up | 3 | 10. Anxiety | 5 |

---

## 3. Dialogue & Clinical Note Text Lengths

A key characteristic of this corpus is the **length discrepancy** between the source dialogues and target clinical notes. Source dialogues are highly conversational and wordy, whereas clinical notes are concise and highly summarized.

### Word & Sentence Length Summary (Across Splits)

| Split | Dialog Word Count (Mean) | Dialog Word Count (Median) | Dialog Word Count (Range) | Note Word Count (Mean) | Note Word Count (Median) | Note Word Count (Range) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Train** | 1301.2 | 1240.0 | 628 - 3050 | 420.8 | 404.0 | 135 - 884 |
| **Valid** | 1221.5 | 1241.5 | 695 - 1789 | 430.9 | 435.0 | 171 - 829 |
| **CLEF Test 3** | 1334.0 | 1297.0 | 770 - 2707 | 439.8 | 419.5 | 249 - 771 |
| **NLP Test 1** | 1231.4 | 1098.0 | 693 - 2392 | 415.3 | 397.0 | 152 - 785 |
| **NLP Test 2** | 1382.4 | 1261.0 | 742 - 2681 | 437.7 | 430.0 | 163 - 884 |
| **Overall** | **1301.9** | **1235.0** | **628 - 3050** | **427.2** | **414.0** | **135 - 884** |

![Dialogue vs. Note Length Scatter](C:/Users/bjish/.gemini/antigravity-ide/brain/72540511-a052-43b9-a601-706caf0aebe3/dialogue_note_length_scatter.png)

> [!NOTE]
> On average, a clinical note is **approximately 32.8%** of the length of the raw spoken dialogue. This indicates a high compression ratio (~3x reduction in text volume).

---

## 4. Conversational and Note Structures

### Dialogue Speaker Dynamics
We analyzed all speaker tags used in dialogues across the splits:
*   `[doctor]`: **5,897 turns** (Average ~28.5 turns per encounter)
*   `[patient]`: **5,406 turns** (Average ~26.1 turns per encounter)
*   `[patient_guest]`: **132 turns** (Present in select family/caregiver discussions)
*   `[inaudible XX:XX:XX]`: Occasional transcription artifacts (1 turn)

On average, clinical dialogues involve exactly 2 main speakers (doctor & patient) with very balanced alternating turn-taking, averaging about 54.4 total turns per encounter.

### Clinical Note Section Frequencies
Notes follow strict SOAP (Subjective, Objective, Assessment, Plan) structuring guidelines. We extracted all section headers from all 207 notes to rank the most frequent templates:

| Note Section Header | Frequency Count | Occurs in Notes (%) | Note Component |
| :--- | :---: | :---: | :--- |
| **CHIEF COMPLAINT** (or `CC`) | 192 | 92.7% | Subjective |
| **RESULTS** | 158 | 76.3% | Objective (Labs/Imaging) |
| **REVIEW OF SYSTEMS** | 155 | 74.9% | Subjective (Symptom Checklist) |
| **PHYSICAL EXAM** (or `PHYSICAL EXAMINATION`) | 190 | 91.7% | Objective (Physical Findings) |
| **HISTORY OF PRESENT ILLNESS** | 143 | 69.1% | Subjective (Encounter Narrative) |
| **PLAN** / **ASSESSMENT** / **ASSESSMENT AND PLAN** | 206 | 99.5% | Assessment & Plan (A/P) |
| **INSTRUCTIONS** | 107 | 51.7% | Plan (Patient Education) |
| **SOCIAL HISTORY** | 82 | 39.6% | Subjective (Lifestyle) |
| **VITALS** | 77 | 37.2% | Objective (Measurements) |
| **MEDICATIONS** / **CURRENT MEDICATIONS** | 83 | 40.1% | Subjective / Plan |

---

## 5. Vocabulary Overlap & "Reasoning Gap"

One of the most important metrics for clinical text generation is **lexical overlap** between the source text and target summary. This measures what percentage of the note's vocabulary is explicitly spoken in the dialogue.

*   **Jaccard Similarity (Overall)**: **30.7%**
    *   The Jaccard word-level overlap between the dialogue and the note's unique words is relatively low, demonstrating that they are distinct styles of text.
*   **Total Word Recall (Mean)**: **61.4%**
    *   About 61.4% of the words in the target note can be found in the dialogue.
*   **Content-Only Word Recall (Mean)**: **54.9%**
    *   When we remove common English stopwords (focusing purely on medical nouns, verbs, drug names, diagnoses), only **54.9% of content words** present in the note are explicitly mentioned in the raw dialogue.

> [!IMPORTANT]
> **The ~45% "Reasoning Gap":**
> Because nearly **45.1% of the medical concepts and descriptors in the clinical note do not appear in the dialogue**, generative models cannot rely on extraction alone.
> The model must perform **synthesis, translation of lay terms to clinical terminology** (e.g., patient says *"heart valve leakage"*, doctor writes *"mitral regurgitation"*), and **reasoning** (synthesizing vital signs or medical history into formal assessments).

---

## 6. Source Experiment Data Analysis (ASR vs. Human / Corrected)

The `src_experiment_data` folder allows us to analyze the difference between raw ASR transcripts, human transcriptions, and human-corrected transcripts.

### Matched Comparisons Summary

We matched encounters across transcripts to compute the **Word Error Rate (WER)** and length differences:

| Dataset Configuration | Compared Transcript Types | Merged Encounters | Average WER | Avg Word Count Diff | Target Notes Match (%) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Test 1 ACI** | ASR vs. ASR-Corrected | 22 | 0.0000 | 0.00 | 100% |
| **Test 2 ACI** | ASR vs. ASR-Corrected | 22 | 0.0002 | -0.09 | 100% |
| **Test 3 ACI** | ASR vs. ASR-Corrected | 22 | 0.0006 | -0.27 | 100% |
| **Valid ACI** | ASR vs. ASR-Corrected | 11 | 0.0007 | +0.18 | 100% |
| **Test 1 VirtScribe** | ASR vs. Human Transcription | 8 | **0.1092 (10.9%)** | **+97.12 (Human longer)** | 100% |
| **Test 2 VirtScribe** | ASR vs. Human Transcription | 8 | **0.1119 (11.2%)** | **+132.38 (Human longer)**| 100% |
| **Test 3 VirtScribe** | ASR vs. Human Transcription | 8 | **0.1508 (15.1%)** | **+160.38 (Human longer)**| 100% |
| **Valid VirtScribe** | ASR vs. Human Transcription | 4 | **0.1610 (16.1%)** | **+138.25 (Human longer)**| 100% |

![ASR Word Error Rate (WER) Comparison](C:/Users/bjish/.gemini/antigravity-ide/brain/72540511-a052-43b9-a601-706caf0aebe3/asr_wer_comparison.png)

### Key Insights from ASR Comparisons:
1.  **ACI Transcripts**: The `ASR` and `ASR-Corrected` versions are **virtually identical** (WER $\approx$ 0%). The word counts differ by less than 1 word on average. This suggest that the raw ASR system used in the ACI pipeline was either highly accurate, or these specific files represent a post-processed state.
2.  **VirtScribe Transcripts**: In contrast, the `VirtScribe` dataset shows a clear gap between `ASR` and `Human Transcription` (WER ranges between **10.9% and 16.1%**).
3.  **Missing Dialogue in ASR**: The human transcriptions are consistently longer than their ASR counterparts by **97 to 160 words**. This demonstrates that the VirtScribe ASR system struggled to capture portions of the conversation, either due to overlapping speech, low audio quality, or speaker accentuation.
4.  **Reference Note Stability**: For both ACI and VirtScribe, the target `note` column is **100% identical** between compared files. The dataset is designed to test how note generation models perform under different audio transcription quality conditions against the *same* ground truth clinical note.

---

## 7. Implications for Machine Learning Models

*   **Handling Multiline Formats**: The raw CSV files represent multiline text structures (dialogue turns and clinical notes span multiple lines within double quotes). Standard line-based parsers will fail; models must be trained using robust CSV parsing libraries (like `pandas`).
*   **Terminology Mapping**: Because only 54.9% of content words carry over, models need strong medical synonyms mapping capability. A sequence-to-sequence model needs to understand clinical synonym associations.
*   **Robustness to ASR Noise**: Using VirtScribe data, researchers can benchmark how note generation quality degrades when feeding a model a transcript with ~11-16% word errors compared to a perfect human transcript.

---
*Report compiled on July 5, 2026.*
