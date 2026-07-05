# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import time
import uuid
import json
import datetime
import requests
from collections.abc import Iterator
import streamlit as st

# Setup page config first
st.set_page_config(
    page_title="HealBuddy Portal",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SYSTEM PROMPT CONSTANTS (For local simulation fallback) ---

SOAP_SYSTEM_PROMPT = """You are an expert medical scribe and clinical documentation assistant. Your task is to generate a highly professional, accurate, and structured SOAP (Subjective, Objective, Assessment, Plan) note based on the details provided.

INPUT METADATA:
- Doctor Name: {doctor_name}
- Department/Specialty: {doctor_department}
- Encounter Transcript:
\"\"\"
{transcript}
\"\"\"

INSTRUCTIONS:
1. Review the transcript carefully. Organize the clinical information into standard SOAP format:
   - **Subjective (S):** Chief complaint, symptoms, relevant past history, lifestyle factors.
   - **Objective (O):** Vital signs, physical exams, or labs mentioned. If none, note "None reported in transcript."
   - **Assessment (A):** Differential or confirmed diagnoses, clinical reasoning.
   - **Plan (P):** Prescribed medications, tests, lifestyle guidance, and follow-up.
2. Adapt the terminology and depth to align with the specified department: {doctor_department}.
3. Maintain an objective, professional medical tone. Do not include extraneous conversational filler."""

PATIENT_CHATBOT_SYSTEM_PROMPT = """You are a compassionate, helpful, and highly professional healthcare assistant chatbot. Your role is to support the patient and answer general inquiries based on their details.

PATIENT PROFILE:
- Name: {patient_name}
- Age: {patient_age}
- Interaction ID: {interaction_id}

RULES:
1. Be empathetic, warm, and clear. Address the patient by name. Use simple, non-jargon language appropriate for their age ({patient_age}).
2. **Clinical Boundaries:** Do not diagnose conditions or prescribe medications. Frame advice as general education.
3. If severe or urgent symptoms are mentioned, immediately instruct them to seek emergency services (911) or go to the nearest ER. Always advise consulting their primary healthcare provider or the doctor associated with Interaction ID {interaction_id} for clinical decisions."""

# --- MOCK GENERATION FALLBACKS ---

def generate_mock_soap(doctor_name: str, doctor_department: str, transcript: str) -> str:
    """Generates a high-quality clinical SOAP note mockup based on transcript keywords."""
    time.sleep(2.0)  # Simulate API latency
    text = transcript.lower()
    
    # Keyword detection for realistic clinical matches
    if "chest pain" in text or "heart" in text or "cardiac" in text:
        complaint = "Retrosternal chest discomfort described as tightness, radiating mildly to left shoulder"
        objective = "BP: 138/86 mmHg, HR: 84 bpm, RR: 16 bpm, Temp: 98.4°F, O2 Sat: 97% on room air. RRR, normal S1/S2. Lungs clear to auscultation."
        assessment = "Chest pain under evaluation. Differential includes stable angina, gastroesophageal reflux, costochondritis."
        plan = "1. Schedule outpatient stress test and 12-lead EKG.\n2. Advise low fat, low sodium diet.\n3. Prescribe sublingual Nitroglycerin 0.4mg SOS for severe chest discomfort.\n4. **Red Flags:** Proceed directly to nearest ER or call 911 if pain worsens, becomes crushing, or is accompanied by sweating/nausea."
    elif "stomach" in text or "abdominal" in text or "diarrhea" in text or "vomit" in text:
        complaint = "Diffuse abdominal cramping and watery diarrhea (3-4 episodes/day) for 48 hours"
        objective = "BP: 114/72 mmHg, HR: 92 bpm, Temp: 99.1°F. Abdomen soft, diffuse mild tenderness in lower quadrants, hyperactive bowel sounds."
        assessment = "Acute gastroenteritis, likely viral vs infectious foodborne etiology."
        plan = "1. Strict oral rehydration protocol (ORS, electrolyte fluids).\n2. Probiotic supplementation daily for 7 days.\n3. BRAT diet (Bananas, Rice, Applesauce, Toast); avoid dairy and fatty foods.\n4. Seek immediate re-evaluation if hematochezia, high fevers (>102°F), or signs of severe dehydration manifest."
    elif "fever" in text or "cough" in text or "throat" in text or "breath" in text:
        complaint = "Subjective fevers, sore throat, and persistent dry cough for 3 days"
        objective = "Temp: 101.2°F, HR: 96 bpm, O2 Sat: 96% on room air. Oropharynx erythematous with mild tonsillar hypertrophy, lungs clear bilaterally."
        assessment = "Acute viral upper respiratory infection (URI). Differential includes acute bronchitis, pharyngitis."
        plan = "1. Support recovery with rest and oral hydration (2.5L daily).\n2. Paracetamol 650mg TDS as needed for fevers/sore throat.\n3. Cough lozenges/warm honey saline gargles.\n4. Follow up if symptoms worsen or dyspnea develops."
    else:
        complaint = "Routine outpatient consultation and clinical review"
        objective = "Stable vitals. BP: 120/80 mmHg, HR: 72 bpm, Temp: 98.6°F. Systemic physical examinations within normal limits."
        assessment = "General outpatient evaluation. Department specialty focus: " + doctor_department
        plan = "1. Maintain standard dietary and exercise habits.\n2. Order baseline laboratory panel (CBC, lipid profiles, HbA1c).\n3. Re-evaluate at scheduled routine follow-up."

    return f"""### CLINICAL SOAP NOTE (SIMULATED RESPONSE)
**Encounter Date:** {datetime.date.today().strftime('%d-%b-%Y')}  
**Attending Scribe/Provider:** {doctor_name}  
**Specialty/Department:** {doctor_department}  

---

#### 1. SUBJECTIVE (S)
- **Chief Complaint:** {complaint}.
- **History of Present Illness (HPI):** The patient presents with symptoms as documented. Reports onset is acute and has caused mild to moderate discomfort.
- **Review of Systems (ROS):** Positive for chief complaint as detailed above. All other systems reviewed are otherwise negative and unremarkable.

#### 2. OBJECTIVE (O)
- **Vitals:** {objective}
- **Physical Examination:** General appearance is alert, oriented x3, and in no acute distress. Detailed examinations are pending review.

#### 3. ASSESSMENT (A)
- **Primary Diagnosis:** {assessment}
- **Clinical Impression:** Symptoms match diagnostic criteria. Specialty care pathways are initiated.

#### 4. PLAN (P)
- **Directives & Care Instructions:**  
{plan}
- **Provider Note:** Follow up or escalate care immediately if any warning indicators manifest.
"""

def generate_mock_chat_response(patient_name: str, patient_age: str, interaction_id: str, message: str) -> str:
    """Generates an empathetic, simulated assistant response matching safety boundaries."""
    time.sleep(1.0)  # Simulate response latency
    msg = message.lower()
    
    if "emergency" in msg or "severe" in msg or "chest pain" in msg or "breath" in msg or "die" in msg:
        return f"🚨 **{patient_name}, please listen carefully.** If you are experiencing severe symptoms, intense pain, or difficulty breathing, please call emergency services (911) or proceed to the nearest emergency department immediately. Your safety is paramount. For non-emergent updates, please consult your primary physician or doctor reference ID {interaction_id}."
        
    if "medication" in msg or "drug" in msg or "dose" in msg or "pill" in msg or "tablet" in msg:
        return f"Hello {patient_name}, regarding your medications: as an AI assistant, I am not authorized to prescribe, adjust, or make recommendations on drug dosages. I strongly advise checking with your pharmacist or the doctor associated with Interaction ID {interaction_id} before making any changes."
        
    if "soap" in msg or "diagnose" in msg or "what is" in msg or "note" in msg or "record" in msg:
        return f"Concerning your clinical record under ID {interaction_id}: your doctor recorded a detailed SOAP note outlining your complaints (Subjective), vitals/exams (Objective), clinical impression (Assessment), and therapy plan (Plan). Let me know if there are specific sections or terminologies you'd like me to explain!"

    if "thank" in msg or "bye" in msg or "thanks" in msg:
        return f"You're very welcome, {patient_name}! I'm glad I could help explain this. Always remember to check in with your primary doctor for any actual diagnoses or clinical decisions. Let me know if you need anything else!"

    return f"Thank you for sharing that, {patient_name}. Regarding your loaded health session (Interaction ID: {interaction_id}), I am here to help translate any medical terminology or outline generic health topics for you. Please let me know what questions you have about your plan!"

# --- ADK STREAMING RUNNER CLIENT ---

def stream_adk_agent(base_url: str, message: str, state_init: dict = None) -> Iterator[str]:
    """Interfaces with a deployed ADK service, yields the response chunks in real-time."""
    user_id = f"user_{uuid.uuid4()}"
    
    # 1. Create Session
    session_url = f"{base_url.rstrip('/')}/apps/app/users/{user_id}/sessions"
    session_data = {"state": state_init or {}}
    
    try:
        session_res = requests.post(session_url, json=session_data, headers={"Content-Type": "application/json"}, timeout=15)
        session_res.raise_for_status()
        session_id = session_res.json()["id"]
    except Exception as e:
        raise RuntimeError(f"Failed to create session on {base_url}: {e}")
        
    # 2. Run Server-Sent Events (SSE) stream
    run_url = f"{base_url.rstrip('/')}/run_sse"
    payload = {
        "app_name": "app",
        "user_id": user_id,
        "session_id": session_id,
        "new_message": {"role": "user", "parts": [{"text": message}]},
        "streaming": True
    }
    
    try:
        response = requests.post(run_url, json=payload, headers={"Content-Type": "application/json"}, stream=True, timeout=60)
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode("utf-8")
                if line_str.startswith("data: "):
                    event = json.loads(line_str[6:])
                    content = event.get("content")
                    if content and content.get("parts"):
                        for part in content["parts"]:
                            text = part.get("text")
                            if text:
                                yield text
    except Exception as e:
        raise RuntimeError(f"Execution error on {base_url}: {e}")

# --- CSS STYLING & PREMIUM CUSTOMIZATION ---

st.markdown("""
    <style>
    .main-header {
        font-family: 'Outfit', 'Inter', sans-serif;
        font-size: 2.6rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.1rem;
    }
    .sub-header {
        font-family: 'Inter', sans-serif;
        font-size: 1.1rem;
        color: #4B5563;
        margin-bottom: 2rem;
    }
    .custom-card {
        background-color: #F8FAFC;
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid #E2E8F0;
        margin-bottom: 1rem;
    }
    .pulse-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        background-color: #10B981;
        border-radius: 50%;
        margin-right: 8px;
    }
    .stButton>button {
        background-color: #2563EB;
        color: white;
        font-weight: 600;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1.5rem;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #1D4ED8;
        transform: translateY(-1px);
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR CONFIGURATION ---

with st.sidebar:
    st.markdown("## 🌐 Service URLs")
    st.info("Direct the frontend to communicate with your deployed Cloud Run services below. Fallback simulation runs if services are unreachable.")
    
    doctor_service_url = st.text_input(
        "Doctor Service URL",
        value="https://doctor-service-1011679267195.us-central1.run.app",
        help="Base URL of doctor-service deployment"
    )
    
    patient_service_url = st.text_input(
        "Patient Service URL",
        value="	https://patient-service-1011679267195.us-central1.run.app",
        help="Base URL of patient-service deployment"
    )
    
    st.markdown("---")
    st.markdown("### Quick Demo Presets")
    
    demo_transcript = """Patient Patrick Allen, a 42-year-old male, presents with abdominal pain and diarrhea. 
He reports the pain started yesterday, localized around the belly button, radiating downwards. 
Describes it as severe cramping. Reports 4 loose watery bowel movements since this morning. 
Tried taking Paracetamol without relief. Reports no fevers or vomiting, but complains of nausea. 
No history of bowel disorders. Attending doctor: Dr. Jenkins, Internal Medicine."""
    
    if st.button("Load Demo Patient Data"):
        st.session_state.demo_loaded = True
        st.session_state.doctor_name = "Dr. Jenkins"
        st.session_state.doctor_dept = "General Practice"
        st.session_state.transcript_input = demo_transcript
        st.session_state.patient_name_input = "Patrick Allen"
        st.session_state.patient_age_input = "42"
        st.session_state.interaction_id_input = "D2N028"

# --- MAIN HERO HEADER ---

st.markdown('<div class="main-header">🏥 HealBuddy Portal</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">AI-Assisted SOAP note orchestration and interactive patient health chatbot.</div>', unsafe_allow_html=True)

# Initialize Session State Variables safely
if "soap_note" not in st.session_state:
    st.session_state.soap_note = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "patient_registered" not in st.session_state:
    st.session_state.patient_registered = False
if "patient_name" not in st.session_state:
    st.session_state.patient_name = ""
if "patient_age" not in st.session_state:
    st.session_state.patient_age = ""
if "interaction_id" not in st.session_state:
    st.session_state.interaction_id = ""

# Handle Demo load variables
doctor_name_val = st.session_state.get("doctor_name", "Dr. Sarah Jenkins")
doctor_dept_val = st.session_state.get("doctor_dept", "General Practice")
transcript_val = st.session_state.get("transcript_input", "")
pat_name_val = st.session_state.get("patient_name_input", "")
pat_age_val = st.session_state.get("patient_age_input", "")
int_id_val = st.session_state.get("interaction_id_input", "")

# --- TABS CREATION ---

tab_doc, tab_pat = st.tabs(["🩺 Doctor Portal (SOAP Note Scribe)", "💬 Patient Portal (Empathy Chat)"])

# ==============================================================================
# TAB 1: DOCTOR PORTAL
# ==============================================================================
with tab_doc:
    st.subheader("Clinical Encounter Transcriber & SOAP Scribe")
    col_input, col_output = st.columns([1, 1], gap="large")
    
    with col_input:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown("### 📋 Encounter Inputs")
        
        doc_name = st.text_input(
            "Attending Doctor Name", 
            value=doctor_name_val,
            placeholder="Dr. Sarah Jenkins"
        )
        
        dept_options = ["General Practice", "Cardiology", "Pediatrics", "Neurology", "Psychiatry", "Orthopedics"]
        doc_department = st.selectbox(
            "Department/Specialty",
            options=dept_options,
            index=dept_options.index(doctor_dept_val) if doctor_dept_val in dept_options else 0
        )
        
        transcript = st.text_area(
            "Consultation Transcript",
            value=transcript_val,
            height=260,
            placeholder="Paste raw transcript, speech-to-text diarized output, or patient visit summary here..."
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        btn_disabled = not transcript.strip()
        generate_btn = st.button("Generate SOAP Document", disabled=btn_disabled, use_container_width=True)
        
        if btn_disabled:
            st.caption("⚠️ Please enter a transcript to enable SOAP generation.")
            
        if generate_btn:
            # Clear previous note
            st.session_state.soap_note = ""
            
            with st.spinner("Connecting to Doctor Cloud Run service..."):
                note_placeholder = st.empty()
                try:
                    # Format user request
                    user_message = f"Process this encounter transcript. Attending: {doc_name}, Department: {doc_department}.\nTranscript:\n{transcript}"
                    
                    full_response = ""
                    # Stream live from Cloud Run doctor-service
                    for chunk in stream_adk_agent(doctor_service_url, user_message):
                        full_response += chunk
                        note_placeholder.markdown(full_response)
                        
                    st.session_state.soap_note = full_response
                    st.success("SOAP note fanned out and generated from live Cloud Run successfully!")
                except Exception as e:
                    st.warning(f"Live service offline/error: {e}. Falling back to simulation mode.")
                    st.session_state.soap_note = generate_mock_soap(doc_name, doc_department, transcript)
                    note_placeholder.markdown(st.session_state.soap_note)
                    st.success("Generated simulated SOAP note successfully.")
            
    with col_output:
        st.markdown("### 📝 Generated SOAP Clinical Note")
        
        if st.session_state.soap_note:
            st.markdown('<div class="custom-card" style="background-color: white;">', unsafe_allow_html=True)
            st.markdown(st.session_state.soap_note)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Download action
            st.download_button(
                label="📥 Download SOAP Note (.md)",
                data=st.session_state.soap_note,
                file_name=f"SOAP_Note_{datetime.date.today().strftime('%Y%m%d')}.md",
                mime="text/markdown",
                use_container_width=True
            )
        else:
            st.info("Await inputs. Once generated, your formatted SOAP note will render here.")

# ==============================================================================
# TAB 2: PATIENT PORTAL
# ==============================================================================
with tab_pat:
    st.subheader("Empathetic Patient Care Chatbot")
    
    col_reg, col_chat = st.columns([1, 2], gap="large")
    
    with col_reg:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown("### 🔑 Patient Registration")
        
        pat_name = st.text_input("Patient Name", value=pat_name_val, placeholder="e.g. Patrick Allen")
        pat_age = st.text_input("Patient Age", value=pat_age_val, placeholder="e.g. 42")
        int_id = st.text_input("Interaction/Encounter ID", value=int_id_val, placeholder="e.g. D2N028")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        start_chat_btn = st.button("Start Conversation", use_container_width=True)
        
        if start_chat_btn:
            if not pat_name.strip() or not pat_age.strip() or not int_id.strip():
                st.error("Please fill in all registration fields to initiate conversation.")
            else:
                st.session_state.patient_name = pat_name
                st.session_state.patient_age = pat_age
                st.session_state.interaction_id = int_id
                
                # Setup session context variables for patient service
                st.session_state.patient_user_id = f"user_{uuid.uuid4()}"
                
                # Check live patient service connection
                with st.spinner("Initializing Cloud Run patient session..."):
                    try:
                        session_url = f"{patient_service_url.rstrip('/')}/apps/app/users/{st.session_state.patient_user_id}/sessions"
                        session_res = requests.post(
                            session_url,
                            json={"state": {"encounter_id": int_id, "patient_name": pat_name}},
                            headers={"Content-Type": "application/json"},
                            timeout=8
                        )
                        session_res.raise_for_status()
                        st.session_state.patient_session_id = session_res.json()["id"]
                        st.session_state.patient_service_connected = True
                    except Exception as e:
                        st.session_state.patient_service_connected = False
                        st.sidebar.warning(f"Patient service offline: {e}. Running in simulation mode.")
                        
                st.session_state.patient_registered = True
                
                # Pre-populate greeting message
                greeting = f"Hello {pat_name} ({pat_age} y/o). Warm welcome to your HealBuddy health portal. I have successfully loaded your visit record (Interaction ID: {int_id}). How can I help clarify your care plan, prescriptions, or check-up details today?"
                st.session_state.chat_history = [
                    {"role": "assistant", "content": greeting}
                ]
                st.rerun()

        # Diagnostic active metrics
        if st.session_state.patient_registered:
            st.markdown("#### Active Clinical Context")
            st.markdown(f"**Patient:** {st.session_state.patient_name}  \n**Age:** {st.session_state.patient_age}  \n**Encounter Ref:** {st.session_state.interaction_id}")
            if st.session_state.get("patient_service_connected", False):
                st.markdown("🟢 **Status:** Connected to Patient Cloud Run")
            else:
                st.markdown("🟡 **Status:** Running Local Simulation")
            
    with col_chat:
        st.markdown("### Chat Assistant")
        
        if not st.session_state.patient_registered:
            st.info("Complete patient registration on the left to activate the secure interactive chat assistant.")
        else:
            # Display chat messages
            chat_container = st.container(height=420)
            
            with chat_container:
                for msg in st.session_state.chat_history:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])
                        
            # Accept user inputs
            user_input = st.chat_input("Ask a question about your SOAP record or medical terms...")
            
            if user_input:
                # Echo user message in container immediately
                with chat_container:
                    with st.chat_message("user"):
                        st.markdown(user_input)
                
                # Save user message to history
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                
                # Fetch AI response
                with chat_container:
                    with st.chat_message("assistant"):
                        reply_placeholder = st.empty()
                        
                        if st.session_state.get("patient_service_connected", False):
                            # Stream live from patient-service Cloud Run
                            try:
                                full_reply = ""
                                stream_generator = stream_adk_agent(
                                    patient_service_url,
                                    user_input,
                                    state_init={
                                        "encounter_id": st.session_state.interaction_id,
                                        "patient_name": st.session_state.patient_name
                                    }
                                )
                                for chunk in stream_generator:
                                    full_reply += chunk
                                    reply_placeholder.markdown(full_reply)
                                    
                                st.session_state.chat_history.append({"role": "assistant", "content": full_reply})
                            except Exception as e:
                                st.warning(f"Chat stream connection failed: {e}. Falling back to simulation.")
                                ai_reply = generate_mock_chat_response(
                                    st.session_state.patient_name,
                                    st.session_state.patient_age,
                                    st.session_state.interaction_id,
                                    user_input
                                )
                                reply_placeholder.markdown(ai_reply)
                                st.session_state.chat_history.append({"role": "assistant", "content": ai_reply})
                        else:
                            # Mock mode
                            ai_reply = generate_mock_chat_response(
                                st.session_state.patient_name,
                                st.session_state.patient_age,
                                st.session_state.interaction_id,
                                user_input
                            )
                            reply_placeholder.markdown(ai_reply)
                            st.session_state.chat_history.append({"role": "assistant", "content": ai_reply})
                
                st.rerun()
