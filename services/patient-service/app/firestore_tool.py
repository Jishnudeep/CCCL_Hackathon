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

import logging
from google.cloud import firestore
from google.cloud import storage
from google.adk.tools import ToolContext

logger = logging.getLogger(__name__)

def extract_content_from_gcs_uri(gcs_uri: str) -> str:
    """Downloads text content from a GCS URI (gs://bucket/path)."""
    if not gcs_uri.startswith("gs://"):
        raise ValueError("Invalid GCS URI. Must start with 'gs://'")

    uri_path = gcs_uri[5:]
    parts = uri_path.split("/", 1)
    if len(parts) < 2 or not parts[1]:
        raise ValueError(f"Invalid GCS URI structure. Could not parse bucket/file path from: {gcs_uri}")
        
    bucket_name = parts[0]
    blob_name = parts[1]

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    return blob.download_as_bytes().decode('utf-8')

def fetch_patient_record(encounter_id: str, patient_name: str) -> dict | None:
    """Retrieves all Firestore documents and details associated with the patient from 'partients' and 'doctors-encounters'."""
    try:
        db = firestore.Client(database="cccl-firestore")
        
        # 1. Fetch from 'partients' collection
        pat_ref = db.collection("partients").document(encounter_id)
        pat_doc = pat_ref.get()
        
        if not pat_doc.exists:
            logger.warning(f"No document found with ID '{encounter_id}' in 'partients' collection.")
            return None
            
        pat_data = pat_doc.to_dict()
        
        # Security validation: Verify name matches (case-insensitive, stripped)
        stored_name = pat_data.get("patient_name", "").strip().lower()
        provided_name = patient_name.strip().lower()
        if stored_name != provided_name:
            logger.warning(f"Access denied: name mismatch for encounter ID {encounter_id}. Expected: {stored_name}, Got: {provided_name}")
            return None
            
        # 2. Fetch from 'doctors-encounters' to merge additional details (doctor details, transcript URL)
        doc_ref = db.collection("doctors-encounters").document(encounter_id)
        doc_doc = doc_ref.get()
        
        if doc_doc.exists:
            doc_data = doc_doc.to_dict()
            # Merge doctor details into patient data
            for key, val in doc_data.items():
                if key not in pat_data:
                    pat_data[key] = val
                    
        # 3. Retrieve GCS transcript text if transcript_gcs_url is present
        gcs_url = pat_data.get("transcript_gcs_url")
        if gcs_url:
            try:
                pat_data["transcript"] = extract_content_from_gcs_uri(gcs_url)
            except Exception as ge:
                logger.warning(f"Could not retrieve GCS transcript content from {gcs_url}: {ge}")

        return pat_data

    except Exception as e:
        logger.error(f"Error fetching patient record: {e}")
        raise e

async def retrieve_patient_record_tool(
    encounter_id: str,
    patient_name: str,
    tool_context: ToolContext
) -> dict:
    """Retrieves the patient's record (SOAP note and details) from Firestore and loads it into session state.

    Args:
        encounter_id: The unique encounter ID (e.g., D2N123).
        patient_name: The name of the patient.

    Returns:
        A dictionary containing the status and the retrieved patient record.
    """
    record = fetch_patient_record(encounter_id, patient_name)
    if record:
        tool_context.state["patient_record"] = record
        tool_context.state["encounter_id"] = encounter_id
        tool_context.state["patient_name"] = patient_name
        return {
            "status": "success",
            "message": f"Successfully retrieved patient record for {patient_name}.",
            "record": record
        }
    else:
        return {
            "status": "error",
            "message": f"Could not find or access record for encounter {encounter_id} and name {patient_name}."
        }