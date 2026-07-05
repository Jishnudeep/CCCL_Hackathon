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
from google.adk.agents.callback_context import CallbackContext
from app.firestore_tool import retrieve_patient_record_tool, fetch_patient_record
from app.agent import init_state

def create_mock_tool_context() -> ToolContext:
    mock_session = MagicMock()
    mock_session.state = {}
    mock_invocation_ctx = MagicMock()
    mock_invocation_ctx.session = mock_session
    return ToolContext(invocation_context=mock_invocation_ctx)

@pytest.mark.asyncio
@patch("app.firestore_tool.firestore.Client")
@patch("app.firestore_tool.extract_content_from_gcs_uri")
async def test_retrieve_patient_record_tool_success(mock_extract_gcs, mock_firestore_client):
    mock_extract_gcs.return_value = "Transcript text content"
    
    mock_db = MagicMock()
    mock_firestore_client.return_value = mock_db
    
    # Mock partients doc
    mock_pat_ref = MagicMock()
    mock_pat_doc = MagicMock()
    mock_pat_doc.exists = True
    mock_pat_doc.to_dict.return_value = {
        "patient_name": "patrick allen",
        "patient_age": "42",
        "patient_gender": "male",
        "soap_note": "SOAP NOTE CONTENT",
        "transcript_gcs_url": "gs://bucket/transcript.txt"
    }
    mock_pat_ref.get.return_value = mock_pat_doc
    mock_db.collection.return_value.document.return_value = mock_pat_ref
    
    # Mock doctors-encounters doc
    mock_doc_ref = MagicMock()
    mock_doc_doc = MagicMock()
    mock_doc_doc.exists = True
    mock_doc_doc.to_dict.return_value = {
        "doctor_name": "edwards",
        "doctor_dept": "Internal Medicine"
    }
    # Modify return value based on collection name
    def collection_side_effect(name):
        if name == "partients":
            ret = MagicMock()
            ret.document.return_value = mock_pat_ref
            return ret
        elif name == "doctors-encounters":
            ret = MagicMock()
            ret.document.return_value = mock_doc_ref
            return ret
        return MagicMock()
        
    mock_db.collection.side_effect = collection_side_effect
    mock_doc_ref.get.return_value = mock_doc_doc
    
    ctx = create_mock_tool_context()
    
    res = await retrieve_patient_record_tool(
        encounter_id="D2N028",
        patient_name="patrick allen",
        tool_context=ctx
    )
    
    assert res["status"] == "success"
    assert "patrick allen" in res["message"]
    
    record = ctx.state["patient_record"]
    assert record["patient_name"] == "patrick allen"
    assert record["doctor_name"] == "edwards"
    assert record["transcript"] == "Transcript text content"
    assert record["soap_note"] == "SOAP NOTE CONTENT"
    
    mock_firestore_client.assert_called_once_with(database="cccl-firestore")

@pytest.mark.asyncio
@patch("app.firestore_tool.firestore.Client")
async def test_retrieve_patient_record_tool_name_mismatch(mock_firestore_client):
    mock_db = MagicMock()
    mock_firestore_client.return_value = mock_db
    
    mock_pat_ref = MagicMock()
    mock_pat_doc = MagicMock()
    mock_pat_doc.exists = True
    mock_pat_doc.to_dict.return_value = {
        "patient_name": "patrick allen",
    }
    mock_pat_ref.get.return_value = mock_pat_doc
    mock_db.collection.return_value.document.return_value = mock_pat_ref
    
    ctx = create_mock_tool_context()
    
    res = await retrieve_patient_record_tool(
        encounter_id="D2N028",
        patient_name="different name",
        tool_context=ctx
    )
    
    assert res["status"] == "error"
    assert "patient_record" not in ctx.state

@pytest.mark.asyncio
@patch("app.firestore_tool.firestore.Client")
async def test_retrieve_patient_record_tool_not_found(mock_firestore_client):
    mock_db = MagicMock()
    mock_firestore_client.return_value = mock_db
    
    mock_pat_ref = MagicMock()
    mock_pat_doc = MagicMock()
    mock_pat_doc.exists = False
    mock_pat_ref.get.return_value = mock_pat_doc
    mock_db.collection.return_value.document.return_value = mock_pat_ref
    
    ctx = create_mock_tool_context()
    
    res = await retrieve_patient_record_tool(
        encounter_id="D2N028",
        patient_name="patrick allen",
        tool_context=ctx
    )
    
    assert res["status"] == "error"
    assert "patient_record" not in ctx.state

@pytest.mark.asyncio
@patch("app.agent.fetch_patient_record")
async def test_init_state_callback(mock_fetch):
    # Case 1: Empty state, should fallback to instructions
    mock_ctx = MagicMock()
    mock_ctx.state = {}
    await init_state(mock_ctx)
    assert "patient_record" in mock_ctx.state
    assert "No record retrieved yet" in mock_ctx.state["patient_record"]

    # Case 2: State has credentials, fetch succeeds
    mock_fetch.return_value = {"patient_name": "patrick allen", "soap_note": "SOAP NOTE"}
    mock_ctx_with_creds = MagicMock()
    mock_ctx_with_creds.state = {"encounter_id": "D2N028", "patient_name": "patrick allen"}
    await init_state(mock_ctx_with_creds)
    assert mock_ctx_with_creds.state["patient_record"] == {"patient_name": "patrick allen", "soap_note": "SOAP NOTE"}

    # Case 3: State has credentials, fetch fails/returns None
    mock_fetch.return_value = None
    mock_ctx_fail = MagicMock()
    mock_ctx_fail.state = {"encounter_id": "D2N028", "patient_name": "patrick allen"}
    await init_state(mock_ctx_fail)
    assert "No record retrieved yet" in mock_ctx_fail.state["patient_record"]

def test_google_search_agent_setup():
    from app.agent import google_search_agent, root_agent
    from google.adk.tools import AgentTool
    
    assert google_search_agent.name == "google_search_agent"
    
    # Verify AgentTool is in root_agent tools
    agent_tools = [t for t in root_agent.tools if isinstance(t, AgentTool)]
    assert len(agent_tools) == 1
    assert agent_tools[0].agent == google_search_agent
