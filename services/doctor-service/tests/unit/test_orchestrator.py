import json
import pytest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch
from google.adk.runners import InMemoryRunner
from google.adk.events.event import Event
from google.genai import types

from app.agent import app as main_app, root_agent, doctor_upload_agent, patient_upload_agent

@contextmanager
def patch_agent_run(agent, mock_run):
    agent.__dict__["run_async"] = mock_run
    try:
        yield
    finally:
        if "run_async" in agent.__dict__:
            del agent.__dict__["run_async"]

@pytest.mark.asyncio
async def test_encounter_orchestration_workflow():
    # 1. Define mock implementations for the agents' run_async methods

    async def mock_root_run(ctx):
        from google.adk.tools import ToolContext
        from app.agent import upload_transcript_to_gcs_tool, parallel_agent
        
        tool_ctx = ToolContext(invocation_context=ctx)
        
        # Get input from user message
        message_text = ctx.session.events[-1].content.parts[0].text
        input_data = json.loads(message_text)
        
        # Run step 1 tool
        await upload_transcript_to_gcs_tool(
            doctor_name=input_data["doctor_name"],
            doctor_dept=input_data["doctor_dept"],
            transcript=input_data["transcript"],
            tool_context=tool_ctx
        )
        
        yield Event(
            author="root_agent",
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text="Uploaded transcript to GCS.")]
            )
        )
        
        # Run step 2 parallel sub-agents and consume their events to run tools
        async for event in parallel_agent.run_async(ctx):
            pass
            
        # Return final summary output
        yield Event(
            author="root_agent",
            output={
                "status": "success",
                "encounter_id": ctx.session.state.get("encounter_id"),
                "doctor_upload": ctx.session.state.get("doctor_upload_result"),
                "patient_upload": ctx.session.state.get("patient_upload_result")
            }
        )

    async def mock_doctor_upload_run(ctx):
        from google.adk.tools import ToolContext
        from app.agent import upload_doctor_details_to_firestore_tool
        
        tool_ctx = ToolContext(invocation_context=ctx)
        res = await upload_doctor_details_to_firestore_tool(
            soap_note="SUBJECTIVE: Patient presents with abdominal pain.\nOBJECTIVE: Tenderness in epigastrium.\nASSESSMENT: Gastroenteritis.\nPLAN: Rehydration.",
            tool_context=tool_ctx
        )
        yield Event(author="doctor_upload_agent", output=res)

    async def mock_patient_upload_run(ctx):
        from google.adk.tools import ToolContext
        from app.agent import upload_patient_details_to_firestore_tool, PatientDetails
        
        tool_ctx = ToolContext(invocation_context=ctx)
        res = await upload_patient_details_to_firestore_tool(
            patient_details=PatientDetails(
                patient_name="patrick",
                patient_gender="male",
                patient_age="42",
                other_medical_entities=["abdominal pain", "diarrhea"]
            ),
            tool_context=tool_ctx
        )
        yield Event(author="patient_upload_agent", output=res)

    # 3. Setup client mocks and execute
    mock_storage_client = MagicMock()
    mock_firestore_client = MagicMock()

    with patch("google.cloud.storage.Client", return_value=mock_storage_client), \
         patch("google.cloud.firestore.Client", return_value=mock_firestore_client), \
         patch_agent_run(root_agent, mock_root_run), \
         patch_agent_run(doctor_upload_agent, mock_doctor_upload_run), \
         patch_agent_run(patient_upload_agent, mock_patient_upload_run):

        runner = InMemoryRunner(app=main_app)
        session = await runner.session_service.create_session(
            app_name="app", user_id="test_doctor"
        )

        input_data = {
            "doctor_name": "edwards",
            "doctor_dept": "Internal Medicine",
            "transcript": "Patient Patrick Allen, a 42-year-old male, presents with abdominal pain and diarrhea."
        }
        message_text = json.dumps(input_data)

        outputs = []
        async for event in runner.run_async(
            user_id="test_doctor",
            session_id=session.id,
            new_message=types.Content(role="user", parts=[types.Part.from_text(text=message_text)]),
        ):
            if event.output is not None:
                outputs.append(event.output)

        assert len(outputs) > 0
        final_output = outputs[-1]

        # Verify the final returned summary
        assert isinstance(final_output, dict)
        assert final_output["status"] == "success"
        
        # Encounter ID should be dynamically generated in D2N### format
        enc_id = final_output["encounter_id"]
        assert enc_id.startswith("D2N")
        assert len(enc_id) == 6
        assert enc_id[3:].isdigit()

        # Check doctor details upload output
        assert final_output["doctor_upload"]["encounter_id"] == enc_id
        assert final_output["doctor_upload"]["data"]["doctor_name"] == "edwards"
        assert final_output["doctor_upload"]["data"]["doctor_dept"] == "Internal Medicine"
        assert final_output["doctor_upload"]["data"]["soap_note"].startswith("SUBJECTIVE:")
        assert final_output["doctor_upload"]["data"]["transcript_gcs_url"].startswith("gs://doctor-patient-transcript-upload/")

        # Check patient details upload output
        assert final_output["patient_upload"]["encounter_id"] == enc_id
        assert final_output["patient_upload"]["data"]["patient_name"] == "patrick"
        assert final_output["patient_upload"]["data"]["patient_gender"] == "male"
