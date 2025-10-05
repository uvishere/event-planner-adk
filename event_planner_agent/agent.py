# @title Import necessary libraries
import logging
import os
import warnings

from dotenv import load_dotenv
from fastapi import HTTPException
from google.adk.agents import Agent, LlmAgent, SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import ToolContext, agent_tool, google_search
from google.adk.tools.mcp_tool.mcp_toolset import (MCPTool, MCPToolset,
                                                   StdioServerParameters)
from google.genai import types  # For creating message Content/Parts

load_dotenv()
warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

# Use one of the model constants defined earlier
MODEL_NAME = "gemini-2.0-flash"
# MODEL_NAME = "gemini-2.5-pro-preview-03-25"

GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
GOOGLE_CLOUD_PROJECT_ID = os.environ["GOOGLE_CLOUD_PROJECT_ID"]
GOOGLE_CLOUD_LOCATION = os.environ["GOOGLE_CLOUD_LOCATION"]
GOOGLE_GENAI_USE_VERTEXAI = os.environ["GOOGLE_GENAI_USE_VERTEXAI"]
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")

ROOT_AGENT_NAME = "event_planner_agent"

def check_availability(venue_name: str, date: str) -> dict:
    """Checks the availability of a venue on a specific date.  (Mock implementation)"""
    # In a real implementation, this would interact with a venue booking system.
    print(f"--- Tool: check_availability called for {venue_name} on {date} ---")
    # Mock data:
    if venue_name.lower() == "Darwin Showgrounds" and date == "2025-06-14":
        return {"status": "unavailable"}
    elif venue_name.lower() == "Darwin Waterfront" and date == "2025-06-15":
        return {"status": "unavailable"}
    else:
        return {"status": "available"}

def create_budget_and_fill_sheet(budget_data: dict, spreadsheet_name: str = "Event Budget") -> dict:
    """
    Mock implementation: Pretends to create a Google Spreadsheet and fill it with budget data.
    """
    print(f"--- Mock Tool: create_budget_and_fill_sheet called for '{spreadsheet_name}' ---")
    print("Budget Data:")
    for item, cost in budget_data.items():
        print(f"  {item}: {cost}")
    total = sum(budget_data.values())
    print(f"Total: {total}")
    # Return a mock response
    return {
        "status": "success",
        "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/mock-{spreadsheet_name.replace(' ', '-').lower()}"
    }

get_venues_agent = Agent(
    name="get_venues_agent",
    model=MODEL_NAME,
    description="Provides list of available venues for the event.",
    instruction=(
        f"""You are a Venue Finder Agent. Your primary responsibility is to find and recommend suitable venues for an event based on the user's requirements, such as capacity, location, and event type.

            - Use the available tools to search for venues.
            - If the user's request is unclear, ask for clarification (e.g., estimated number of guests).
            - Prioritize public venues unless otherwise specified.
            - After identifying potential venues, check their availability for the specified date using the `check_availability` tool.
            - Present a list of available venues to the user.
            - Your parent agent is `root_agent`. Once you have provided the venue options, transfer back to the `root_agent`.
        """
    ),
    tools=[check_availability],
    output_key="get_venues_agent_response"
)

catering_agent = LlmAgent(
    name="catering_agent",
    model=MODEL_NAME,
    description="Helps with catering arrangements for events.",
    instruction=(
        f"""You are a Catering Specialist Agent. Your role is to find and recommend catering services for an event based on the user's preferences, including cuisine, budget, and event size.

            - If the user's request is unclear, ask for clarification.
            - Provide a list of recommended caterers with details on their offerings and pricing.
            - Your parent agent is `root_agent`. Once you have provided the catering options, transfer back to the `root_agent`.
        """
    ),
    output_key="catering_agent_response"
)

social_media_agent = LlmAgent(
    name="social_media_agent",
    model=MODEL_NAME,
    description="Helps with creating social media posts for events.",
    instruction=(
        f"""You are a Social Media Marketing Agent. Your responsibility is to create engaging and effective social media content to promote an event.

            - Generate content that is attention-grabbing, shareable, and tailored to the target audience.
            - Optimize posts for various social media platforms, including relevant hashtags and calls-to-action.
            - If necessary, assume details about the event or target audience to fulfill the request.
            - Your parent agent is `root_agent`. Once you have created the social media content, transfer back to the `root_agent`.
        """
    ),
    output_key="social_media_agent_response"
)

budget_agent = LlmAgent(
    name="budget_agent",
    model=MODEL_NAME,
    description="Helps with creating a budget for events.",
    instruction=(
        f"""You are a Budget Specialist Agent. Your primary function is to create and manage the budget for an event.

            - When requested, use the `create_budget_and_fill_sheet` tool to generate a detailed budget.
            - Ensure all budget data is accurate and clearly presented.
            - If any information is unclear, ask the user for clarification.
            - Your parent agent is `root_agent`. Once you have created the budget, transfer back to the `root_agent`.
        """
    ),
    tools=[create_budget_and_fill_sheet],
    output_key="budget_agent_response"
)

proposal_agent = LlmAgent(
    name="proposal_agent",
    model=MODEL_NAME,
    description="Helps with creating a proposal for the event.",
    instruction=(
        f"""You are a Proposal Specialist Agent. Your responsibility is to generate a comprehensive and well-structured event proposal.

            - Use the following format as a reference, but feel free to add or remove topics as needed to fit the specific event.
            - Your parent agent is `root_agent`. Once you have generated the proposal, transfer back to the `root_agent`.

            **PROPOSAL FORMAT START**
            I. Project Overview:
            - A brief summary of the event, including its purpose, target audience, and key objectives.

            II. Key Areas of Focus:
            - **Timeline Creation:** A detailed timeline with key milestones and deadlines.
            - **Vendor Management:** A plan for selecting and managing vendors for services like catering and entertainment.
            - **Permits and Licenses:** A list of necessary permits and a plan for obtaining them.
            - **Marketing and Promotion:** A strategy for promoting the event to the target audience.
            - **Volunteer Coordination:** A plan for recruiting, training, and managing volunteers.
            - **Risk Management:** An assessment of potential risks and a plan to mitigate them.
            **PROPOSAL FORMAT END**
        """
    ),
    output_key="proposal_agent_response"
)

# workflow_agent = SequentialAgent(
#     name="workflow_agent",
#     description="Helps with the overall workflow of the event planning.",
#     sub_agents=[get_venues_agent, catering_agent, social_media_agent, budget_agent]
# )

root_agent = Agent(
    name=ROOT_AGENT_NAME,
    model=MODEL_NAME,  # Can be a string for Gemini or a LiteLlm object
    description="Provides event planning assistance.",
    instruction=(
        f"""You are a Root Agent, acting as a central coordinator for an event planning multi-agent system. Your primary role is to understand the user's event requirements and delegate tasks to the appropriate sub-agents.

            - **`get_venues_agent`**: For all venue-related queries, including finding and checking availability.
            - **`catering_agent`**: For all catering-related inquiries, such as finding and recommending caterers.
            - **`social_media_agent`**: For creating promotional content for social media.
            - **`budget_agent`**: For creating and managing the event budget.
            - **`proposal_agent`**: For generating a formal event proposal.

            When a user requests to plan an event, follow this workflow:
            1. Acknowledge the user's request and confirm your understanding of the requirements.
            2. Activate the specialized sub-agents in a logical sequence to address each aspect of the event plan.
            3. Synthesize the information from all sub-agents into a cohesive and comprehensive plan.
            4. Present the final plan to the user in a structured format, with clear headings for each section.
            5. If the user asks for assumptions to be made, feel free to do so to complete the task.
        """
    ),
    sub_agents=[ get_venues_agent ,catering_agent, social_media_agent, budget_agent, proposal_agent],
    generate_content_config=types.GenerateContentConfig(temperature=0.5),
)

# APP_NAME = "event_planner"
# USER_ID = "user123"
# SESSION_ID = "session1"

# session_service = InMemorySessionService()
# session = session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
# root_agent = root_agent

# runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)

# # Helper method to send query to the runner
# def call_agent(query, session_id, user_id):
#   content = types.Content(role='user', parts=[types.Part(text=query)])
#   events = runner.run(
#       user_id=user_id, session_id=session_id, new_message=content)

#   for event in events:
#       if event.is_final_response():
#           final_response = event.content.parts[0].text
#           print("Agent Response: ", final_response)
