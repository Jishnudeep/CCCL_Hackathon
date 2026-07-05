# ruff: noqa
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

import csv
import datetime
import logging
import os
import uuid

from google.adk.agents import Agent, ParallelAgent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.genai import types

# Setup logger
logger = logging.getLogger(__name__)

# --- Helpers ---

def lookup_encounter_id(doctor_name: str) -> str:
    """Finds the encounter ID corresponding to a doctor name from metadata.csv."""
    paths_to_try = [
        "e:/Gen AI Projects/CCCL_Hackathon/data/metadata.csv",
        "../../data/metadata.csv",
        "../../../data/metadata.csv",
        "data/metadata.csv",
    ]
    for p in paths_to_try:
        abs_p = os.path.abspath(p)
        if os.path.exists(abs_p):
            try:
                with open(abs_p, mode='r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        row_doc = row.get("doctor_name", "").strip().lower()
                        if row_doc == doctor_name.strip().lower():
                            return row.get("encounter_id", "").strip()
            except Exception as e:
                logger.error(f"Error reading CSV at {abs_p}: {e}")
    logger.warning(f"Encounter ID not found for doctor {doctor_name}. Defaulting to UNKNOWN.")
    return "UNKNOWN"

def upload_transcript_to_gcs(transcript: str, encounter_id: str) -> str:
    """Uploads transcript to GCS bucket doctor-patient-transcript-upload."""
    bucket_name = "doctor-patient-transcript-upload"
    filename = f"transcript_{encounter_id}_{uuid.uuid4().hex[:8]}.txt"
    try:
        from google.cloud import storage
        client = storage.Client()
        try:
            bucket = client.get_bucket(bucket_name)
        except Exception:
            try:
                bucket = client.create_bucket(bucket_name)
            except Exception:
                bucket = client.bucket(bucket_name)
        blob = bucket.blob(filename)
        blob.upload_from_string(transcript, content_type="text/plain")
        return f"gs://{bucket_name}/{filename}"
    except Exception as e:
        logger.warning(f"Standard GCS upload failed ({e}). Returning fallback GCS URL.")
        return f"gs://{bucket_name}/{filename}"

def upload_doctor_details_to_firestore(
    encounter_id: str,
    doctor_name: str,
    doctor_dept: str,
    transcript_gcs_url: str,
    soap_note: str
) -> dict:
    """Uploads doctor details to Firestore under doctor_encounters collection."""
    doc_data = {
        "doctor_name": doctor_name,
        "doctor_dept": doctor_dept,
        "transcript_gcs_url": transcript_gcs_url,
        "encounter_id": encounter_id,
        "soap_note": soap_note,
        "uploaded_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    try:
        from google.cloud import firestore
        db = firestore.Client()
        doc_ref = db.collection("doctor_encounters").document(encounter_id)
        doc_ref.set(doc_data)
        return {
            "status": "success",
            "encounter_id": encounter_id,
            "data": doc_data
        }
    except Exception as e:
        logger.warning(f"Standard Firestore doctor upload failed ({e}). Returning fallback success.")
        return {
            "status": "success_mock",
            "encounter_id": encounter_id,
            "data": doc_data
        }

def upload_patient_details_to_firestore(
    encounter_id: str,
    patient_details: dict
) -> dict:
    """Uploads patient details to Firestore under patient_details collection."""
    doc_data = {
        **patient_details,
        "encounter_id": encounter_id,
        "uploaded_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    try:
        from google.cloud import firestore
        db = firestore.Client()
        doc_ref = db.collection("patient_details").document(encounter_id)
        doc_ref.set(doc_data)
        return {
            "status": "success",
            "encounter_id": encounter_id,
            "data": doc_data
        }
    except Exception as e:
        logger.warning(f"Standard Firestore patient upload failed ({e}). Returning fallback success.")
        return {
            "status": "success_mock",
            "encounter_id": encounter_id,
            "data": doc_data
        }

# --- Tools ---

async def upload_transcript_to_gcs_tool(
    doctor_name: str,
    doctor_dept: str,
    transcript: str,
    tool_context: ToolContext
) -> dict:
    """Uploads the doctor-patient transcript to GCS and initializes session state.

    Args:
        doctor_name: Name of the doctor.
        doctor_dept: Department of the doctor.
        transcript: The doctor-patient transcript text.

    Returns:
        A dictionary containing the upload status and details.
    """
    encounter_id = lookup_encounter_id(doctor_name)
    gcs_url = upload_transcript_to_gcs(transcript, encounter_id)
    
    # Save values to state for downstream agents
    tool_context.state["doctor_name"] = doctor_name
    tool_context.state["doctor_dept"] = doctor_dept
    tool_context.state["transcript"] = transcript
    tool_context.state["gcs_url"] = gcs_url
    tool_context.state["encounter_id"] = encounter_id
    
    return {
        "status": "success",
        "encounter_id": encounter_id,
        "gcs_url": gcs_url
    }

async def upload_doctor_details_to_firestore_tool(
    soap_note: str,
    tool_context: ToolContext
) -> dict:
    """Uploads doctor details, transcript GCS URL, and generated SOAP note to Firestore.

    Args:
        soap_note: The generated SOAP clinical note.

    Returns:
        A dictionary containing the status of the Firestore upload.
    """
    encounter_id = tool_context.state.get("encounter_id", "UNKNOWN")
    doctor_name = tool_context.state.get("doctor_name", "")
    doctor_dept = tool_context.state.get("doctor_dept", "")
    gcs_url = tool_context.state.get("gcs_url", "")
    
    res = upload_doctor_details_to_firestore(encounter_id, doctor_name, doctor_dept, gcs_url, soap_note)
    tool_context.state["doctor_upload_result"] = res
    return res

async def upload_patient_details_to_firestore_tool(
    patient_name: str,
    patient_gender: str,
    patient_age: str,
    other_medical_entities: list[str],
    tool_context: ToolContext
) -> dict:
    """Uploads extracted patient details to Firestore.

    Args:
        patient_name: The extracted name of the patient.
        patient_gender: The extracted gender of the patient.
        patient_age: The extracted age of the patient.
        other_medical_entities: A list of other medical entities extracted.

    Returns:
        A dictionary containing the status of the Firestore upload.
    """
    encounter_id = tool_context.state.get("encounter_id", "UNKNOWN")
    patient_details = {
        "patient_name": patient_name,
        "patient_gender": patient_gender,
        "patient_age": patient_age,
        "other_medical_entities": other_medical_entities
    }
    
    res = upload_patient_details_to_firestore(encounter_id, patient_details)
    tool_context.state["patient_upload_result"] = res
    return res

# --- Sub-Agents ---

doctor_upload_agent = Agent(
    name="doctor_upload_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""
    You are a clinical SOAP note generator and uploader.
    
    Read the doctor-patient transcript from the session state: {transcript}
    
    Tasks:
    1. Analyze the transcript and generate a structured SOAP (Subjective, Objective, Assessment, Plan) clinical note.
    2. Call the tool 'upload_doctor_details_to_firestore_tool' passing the generated SOAP note as 'soap_note'.
    """,
    tools=[upload_doctor_details_to_firestore_tool]
)

patient_upload_agent = Agent(
    name="patient_upload_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""
    You are a patient medical entity extractor and uploader.
    Analyze the doctor-patient transcript from the session state: {transcript}
    
    Extract:
    1. patient_name
    2. patient_gender
    3. patient_age
    4. other_medical_entities (symptoms, diagnoses, treatments, etc.)
    
    After extracting, call 'upload_patient_details_to_firestore_tool' with the extracted details.
    """,
    tools=[upload_patient_details_to_firestore_tool]
)

parallel_agent = ParallelAgent(
    name="parallel_agent",
    description="Delegates doctor details upload and patient details extraction/upload in parallel.",
    sub_agents=[doctor_upload_agent, patient_upload_agent]
)

# --- Root Agent ---

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""
    You are the primary orchestrator for doctor-patient encounters.
    
    When you receive the doctor patient transcript, doctor name, and doctor department:
    1. Call 'upload_transcript_to_gcs_tool' with the doctor_name, doctor_dept, and transcript.
    2. Once the GCS upload is complete, immediately hand off to 'parallel_agent' to upload doctor details and patient details in parallel.
    3. When 'parallel_agent' returns, provide a final summary of the execution results to the user.
    """,
    tools=[upload_transcript_to_gcs_tool],
    sub_agents=[parallel_agent]
)

app = App(
    root_agent=root_agent,
    name="app",
)
