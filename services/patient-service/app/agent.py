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

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import AgentTool, google_search
from google.genai import types

from app.firestore_tool import retrieve_patient_record_tool, fetch_patient_record

async def init_state(callback_context: CallbackContext) -> None:
    """Callback to initialize the patient_record placeholder in session state."""
    # Check if encounter_id and patient_name are present in state (passed from frontend during session creation)
    encounter_id = callback_context.state.get("encounter_id")
    patient_name = callback_context.state.get("patient_name")
    
    if encounter_id and patient_name:
        # Automatically load the patient record directly on session initiation
        try:
            record = fetch_patient_record(encounter_id, patient_name)
            if record:
                callback_context.state["patient_record"] = record
                return
        except Exception:
            pass

    if "patient_record" not in callback_context.state:
        callback_context.state["patient_record"] = (
            "No record retrieved yet. Please ask the user for their encounter ID and patient name, "
            "then call retrieve_patient_record_tool to load their SOAP note and details."
        )

# Sub-agent acting as a search tool to avoid mixing search and function tools (disabling AFC)
google_search_agent = Agent(
    name="google_search_agent",
    description="Useful for searching Google to answer general medical questions, definitions, and medical terminology.",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""
    You are a medical search specialist.
    Use the 'google_search' tool to find high-quality, accurate, and up-to-date medical explanations or definitions.
    Provide a direct, clear, and easy-to-understand response based on the search results.
    """,
    tools=[google_search],
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""
    You are a friendly and compassionate patient health assistant.
    Your goal is to answer the patient's questions about their medical records, diagnosis, and SOAP notes.
    
    Current loaded patient record:
    {patient_record}
    
    If the record is not loaded yet (or contains the 'No record retrieved yet' instructions):
    1. Prompt the user for their name and encounter ID (e.g. D2N###).
    2. Once provided, call 'retrieve_patient_record_tool' to load their details.
    
    Once the record is successfully loaded, warmly answer any questions they have about their SOAP note, provisional diagnosis, prescribed medications, symptoms, and planned next steps.
    
    If the patient asks general medical questions (e.g., about drug side effects, medical conditions, or definitions of terms) that are not detailed in their record, use the 'google_search_agent' tool to search for accurate details.
    
    IMPORTANT:
    - Never make up information. Use 'google_search_agent' for questions outside the record.
    - Always advise the patient to consult their primary healthcare physician for final clinical advice.
    """,
    tools=[retrieve_patient_record_tool, AgentTool(google_search_agent)],
    before_agent_callback=init_state,
)

app = App(
    root_agent=root_agent,
    name="app",
)
