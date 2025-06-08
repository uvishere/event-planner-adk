# @title Import necessary libraries
import logging
import os
import warnings

from dotenv import load_dotenv
from fastapi import HTTPException
from google.adk.agents import Agent, LlmAgent
from google.adk.models.lite_llm import LiteLlm  # For multi-model support
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
    instruction="""You are a helpful vnue finder. Help the user with mapping, directions, and finding places using google_search tool.
                    If you don't get proper places, ask user for one.
                    If you're confused about the size, ask user to supply an estimated number.
                    Focus of public venues first.
                """,
    generate_content_config=types.GenerateContentConfig(temperature=0.5),
)

catering_agent = LlmAgent(
    name="catering_agent",
    model=MODEL_NAME,
    description="Helps with catering arrangements for events.",
    instruction=("You are a catering specialist.  Find caterers based on cuisine, budget, and event size. "
                 "If you don't get proper caterers, ask user for one."
                 "Your parent agent is root_agent. If neither the other agents nor you are best for answering the question according to the descriptions, transfer to your parent agent. If you don't have parent agent, try answer by yourself."
                 ),
    tools=[check_availability],  # Or a more specific catering database tool
)

social_media_agent = LlmAgent(
    name="social_media_agent",
    model=MODEL_NAME,
    description="Helps with creating social media posts for events.",
    instruction=("You are a social media marketing specialist. Your role is to create engaging and effective social media content for events. "
                 "Focus on creating posts that are: \n"
                 "- Attention-grabbing and shareable\n"
                 "- Tailored to the event's target audience\n"
                 "- Optimized for different social media platforms\n"
                 "- Include relevant hashtags and calls-to-action\n"
                 "If you need more specific details about the event, target audience, ask the user for clarification."
                 "Never give what you worked on, just give the post."
                 "BUT opt in for autonomy"
                 "Always maintain a professional, informative, interesting and engaging tone while ensuring the content aligns with the event's goals and messaging."
                 "Ask user to install imagen mcp servier to create an image for the post"
                 )
)

budget_agent = LlmAgent(
    name="budget_agent",
    model=MODEL_NAME,
    description="Helps with creating a budget for events.",
    instruction=("You are a budget specialist.  Create a budget for the event."
                 "If the user asks for a budget, use the 'create_budget_and_fill_sheet' tool to create a budget and fill it with the data."
                 "Always maintain clear communication with users - if any aspect is unclear, proactively request clarification to ensure accurate and helpful responses."
                 "Don't disturb the user with your own thoughts, just answer the question."
                 ),
    tools=[create_budget_and_fill_sheet],
)

root_agent = Agent(
    name=ROOT_AGENT_NAME,
    model=MODEL_NAME,  # Can be a string for Gemini or a LiteLlm object
    description="Provides event planning assistance.",
    instruction=(
        "You are a comprehensive Event Planning Assistant. Your role is to coordinate and delegate tasks to specialized sub-agents while maintaining overall project oversight. "
        "For venue-related queries, utilize the 'get_venues_agent' to find suitable locations. "
        "For catering inquiries, delegate to the 'catering_agent' for specialized food service recommendations. "
        "For social media and marketing needs, engage the 'social_media_agent' to create engaging content. "
        "For search queries, use the 'get_venues_agent' to search the web. "
        "For budget queries, use the 'budget_agent' to create a budget and fill it with the data."
        "If you are the best to answer the question according to your description, you can answer it. "
        "When transferring tasks to sub-agents: \n"
        "- Ensure the task aligns with the agent's expertise\n"
        "- Provide clear context and requirements\n"
        "- Review and integrate their responses into a cohesive solution\n"
        "- Take initiative to follow up if responses are incomplete\n"
        "If the user asks for a budget, use the 'create_budget_and_fill_sheet' tool to create a budget and fill it with the data."
        "Always maintain clear communication with users - if any aspect is unclear, proactively request clarification to ensure accurate and helpful responses."
        "Don't disturb the user with your own thoughts, just answer the question."
    ),
    tools=[agent_tool.AgentTool(agent=get_venues_agent)],
    sub_agents=[ get_venues_agent ,catering_agent, social_media_agent, budget_agent],
    generate_content_config=types.GenerateContentConfig(temperature=0.2),

)

APP_NAME = "research_app"
USER_ID = "user123"
SESSION_ID = "session1"

session_service = InMemorySessionService()
session = session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)

async def call_agent(query):
    content = types.Content(role='user', parts=[types.Part(text=query)])
    events = runner.run(user_id=USER_ID, session_id=SESSION_ID, new_message=content)
    for event in events:
        if event.is_final_response():
            final_response = event.content.parts[0].text
            print("Agent Response:", final_response)


# Sample queries to test the agent:


### Examples to work on for sub agents
