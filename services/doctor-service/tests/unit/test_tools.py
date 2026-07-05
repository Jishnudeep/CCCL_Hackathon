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

import pytest
from unittest.mock import MagicMock, patch
from google.adk.tools import ToolContext
from app.agent import (
    upload_transcript_to_gcs_tool,
    upload_doctor_details_to_firestore_tool,
    upload_patient_details_to_firestore_tool,
    PatientDetails,
)

def create_mock_tool_context() -> ToolContext:
    """Helper to create a ToolContext with a real state dictionary."""
    mock_session = MagicMock()
    mock_session.state = {}
    mock_invocation_ctx = MagicMock()
    mock_invocation_ctx.session = mock_session
    return ToolContext(invocation_context=mock_invocation_ctx)

@pytest.mark.asyncio
@patch("app.agent.generate_encounter_id", return_value="D2N028")
@patch("app.agent.upload_transcript_to_gcs")
async def test_upload_transcript_to_gcs_tool(mock_upload, mock_gen_id):
    mock_upload.return_value = "gs://doctor-patient-transcript-upload/transcript_D2N028_xyz.txt"
    
    ctx = create_mock_tool_context()
    
    res = await upload_transcript_to_gcs_tool(
        doctor_name="edwards",
        doctor_dept="Internal Medicine",
        transcript="Hello from patient",
        tool_context=ctx
    )
    
    assert res["status"] == "success"
    assert res["encounter_id"] == "D2N028"
    assert res["gcs_url"] == "gs://doctor-patient-transcript-upload/transcript_D2N028_xyz.txt"
    assert ctx.state["encounter_id"] == "D2N028"
    assert ctx.state["doctor_name"] == "edwards"
    assert ctx.state["doctor_dept"] == "Internal Medicine"
    assert ctx.state["transcript"] == "Hello from patient"
    
    mock_upload.assert_called_once_with("Hello from patient", "D2N028")

@pytest.mark.asyncio
@patch("app.agent.upload_doctor_details_to_firestore")
async def test_upload_doctor_details_to_firestore_tool(mock_upload):
    mock_upload.return_value = {"status": "success"}
    
    ctx = create_mock_tool_context()
    ctx.state.update({
        "encounter_id": "D2N028",
        "doctor_name": "edwards",
        "doctor_dept": "Internal Medicine",
        "gcs_url": "gs://bucket/file.txt"
    })
    
    res = await upload_doctor_details_to_firestore_tool(
        soap_note="SOAP NOTE CONTENT",
        tool_context=ctx
    )
    
    assert res["status"] == "success"
    mock_upload.assert_called_once_with(
        "D2N028",
        "edwards",
        "Internal Medicine",
        "gs://bucket/file.txt",
        "SOAP NOTE CONTENT"
    )

@pytest.mark.asyncio
@patch("app.agent.upload_patient_details_to_firestore")
async def test_upload_patient_details_to_firestore_tool(mock_upload):
    mock_upload.return_value = {"status": "success"}
    
    ctx = create_mock_tool_context()
    ctx.state.update({
        "encounter_id": "D2N028"
    })
    
    res = await upload_patient_details_to_firestore_tool(
        patient_details=PatientDetails(
            patient_name="patrick",
            patient_gender="male",
            patient_age="42",
            other_medical_entities=["abdominal pain", "diarrhea"]
        ),
        tool_context=ctx
    )
    
    assert res["status"] == "success"
    mock_upload.assert_called_once_with(
        "D2N028",
        {
            "patient_name": "patrick",
            "patient_gender": "male",
            "patient_age": "42",
            "other_medical_entities": ["abdominal pain", "diarrhea"]
        }
    )

@pytest.mark.asyncio
@patch("app.agent.upload_transcript_to_gcs")
async def test_upload_error_propagation(mock_upload):
    # Verify that exceptions raised in helpers propagate through tools
    mock_upload.side_effect = Exception("GCS upload failed")
    
    ctx = create_mock_tool_context()
    
    with pytest.raises(Exception, match="GCS upload failed"):
        await upload_transcript_to_gcs_tool(
            doctor_name="edwards",
            doctor_dept="Internal Medicine",
            transcript="Hello",
            tool_context=ctx
        )
