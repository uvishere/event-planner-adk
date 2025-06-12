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
        f"""You are a helpful venue finder. Help the user with mapping, directions, and finding places.
            If you don't get proper places, ask user for one.
            If you're confused about the size, ask user to supply an estimated number.
            Focus of public venues first. Once a venue is selected, help to generate a detailed event planning document. \n
            Your parent agent is root_agent. If neither the other agents nor you are best for answering the question according to the descriptions, transfer to your parent agent. 
            Once your job is done, transfer to your parent agent.
        """),
    tools=[check_availability],
    output_key="get_venues_agent_response"
)

catering_agent = LlmAgent(
    name="catering_agent",
    model=MODEL_NAME,
    description="Helps with catering arrangements for events.",
    instruction=(
        f"""You are a catering specialist.  Find caterers based on cuisine, budget, and event size.
            If you don't get proper caterers, ask user for one.
            Your parent agent is root_agent. If neither the other agents nor you are best for answering the question according to the descriptions, transfer to your parent agent. 
            Once your job is done, transfer to your parent agent.
        """),
    output_key="catering_agent_response"
)

social_media_agent = LlmAgent(
    name="social_media_agent",
    model=MODEL_NAME,
    description="Helps with creating social media posts for events.",
    instruction=(
        f"""You are a social media marketing specialist. Your role is to create engaging and effective social media content for events.
            Focus on creating posts that are:
            - Attention-grabbing and shareable
            - Tailored to the event's target audience
            - Optimized for different social media platforms
            - Include relevant hashtags and calls-to-action
            If you need more specific details about the event, target audience, assume yourself.
            Never give what you worked on, just give the post.
            Opt in for autonomy
            Always maintain a professional, informative, interesting and engaging tone while ensuring the content aligns with the event's goals and messaging.
            Ask user to install imagen mcp servier to create an image for the post
            Your parent agent is root_agent. If neither the other agents nor you are best for answering the question according to the descriptions, transfer to your parent agent. 
            Once your job is done, transfer to your parent agent.
        """),
    output_key="social_media_agent_response"
)

budget_agent = LlmAgent(
    name="budget_agent",
    model=MODEL_NAME,
    description="Helps with creating a budget for events.",
    instruction=(
        f"""You are a budget specialist.  Create a budget for the event.
            If the user asks for a budget, use the 'create_budget_and_fill_sheet' tool to create a budget and fill it with the data.
            Always maintain clear communication with users - if any aspect is unclear, proactively request clarification to ensure accurate and helpful responses.
            Don't disturb the user with your own thoughts, just answer the question.
            Your parent agent is root_agent. If neither the other agents nor you are best for answering the question according to the descriptions, transfer to your parent agent. Once your job is done, transfer to your parent agent.
        """),
    tools=[create_budget_and_fill_sheet],
    output_key="budget_agent_response"
)

proposal_agent = LlmAgent(
    name="proposal_agent",
    model=MODEL_NAME,
    description="Helps with creating a proposal for the event.",
    instruction=(
        f"""You are a proposal specialist.  Create a proposal for the event.
            Use the proposa format below for reference but feel free to add/remove relevant topics.
            Your parent agent is root_agent. If neither the other agents nor you are best for answering the question according to the descriptions, transfer to your parent agent. 
            Once your job is done, transfer to your parent agent.

            **PROPOSAL FORMAT START**
            I. Project Overview:

            This proposal outlines the plan for organizing a large-scale cultural event in Darwin, targeting an audience of approximately 10,000 attendees. 
            The event aims to celebrate culture through food, music, dance, and other cultural activities. 
            The budget for this event is $100,000.

            II. Key Areas of Focus:

            Timeline Creation:

            Goal: Develop a comprehensive timeline to ensure all tasks are completed efficiently and on schedule.
            Action Items:
            Weeks 1-2: Define event scope, objectives, and key milestones.
            Weeks 3-4: Secure venue and obtain necessary permits/licenses.
            Weeks 5-8: Finalize vendor contracts (catering, entertainment, etc.).
            Weeks 9-12: Implement marketing and promotion plan.
            Weeks 13-16: Recruit and train volunteers.
            Weeks 17-20: Finalize event logistics and contingency plans.
            Event Day: Execute event plan and manage on-site operations.
            Post-Event: Evaluate event success and gather feedback.
            
            Vendor Management:
            Goal: Secure reliable and high-quality vendors for catering, entertainment, and other essential services.
            Action Items:
            Identify potential vendors based on event requirements and budget.
            Request proposals and compare pricing, services, and reviews.
            Negotiate contracts and ensure vendors meet all necessary requirements (e.g., insurance, licenses).
            Coordinate vendor logistics and schedules.
            Establish clear communication channels and points of contact.
            
            Permits and Licenses:
            Goal: Obtain all necessary permits and licenses to ensure legal compliance and event safety.
            Action Items:
            Research local regulations and permit requirements for large-scale events.x
            Prepare and submit permit applications to relevant authorities (e.g., city council, fire department).
            Ensure compliance with all permit conditions and regulations.
            Maintain accurate records of all permits and licenses.
            Marketing and Promotion:

            Goal: Create a comprehensive marketing plan to attract a large audience and generate excitement for the event.
            Action Items:
            Define target audience and key messaging.
            Develop a multi-channel marketing strategy (social media, local media, community outreach).
            Create engaging content (e.g., videos, photos, blog posts) to promote the event.
            Utilize social media platforms to reach a wider audience.
            Track marketing campaign performance and adjust strategies as needed.
            
            Volunteer Coordination:
            Goal: Recruit, train, and manage a team of volunteers to assist with event operations.
            Action Items:
            Develop a volunteer recruitment plan.
            Create volunteer job descriptions and schedules.
            Conduct volunteer training sessions to ensure volunteers are prepared for their roles.
            Provide ongoing support and supervision to volunteers during the event.
            Recognize and appreciate volunteer contributions.
            Risk Management:

            Goal: Identify and mitigate potential risks to ensure event safety and minimize disruptions.
            Action Items:
            Conduct a risk assessment to identify potential hazards (e.g., weather, security, medical emergencies).
            Develop a risk management plan to address identified risks.
            Implement safety protocols and emergency procedures.
            Secure event insurance to protect against potential liabilities.
            Establish communication channels for reporting and responding to incidents.
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
        f"""
        You are a comprehensive Event Planning Assistant. Your role is to coordinate and delegate tasks to specialized sub-agents while maintaining overall project oversight.
        For venue-related queries, utilize the 'get_venues_agent' to find suitable locations.
        For catering inquiries, delegate to the 'catering_agent' for specialized food service recommendations.
        For social media and marketing needs, engage the 'social_media_agent' to create engaging content.
        For budget queries, use the 'budget_agent' to create a budget and fill it with the data.
        For proposal queries, use the 'proposal_agent' to create a proposal.
        If you are the best to answer the question according to your description, you can answer it directly.
        When transferring tasks to sub-agents:
        - Ensure the task aligns with the agent's expertise
        - Provide clear context and requirements
        - Review and integrate their responses into a cohesive solution
        When a user provides an event planning request, you must follow this sequence:
            Acknowledge the request as the Root Agent and confirm your understanding of the event requirements.
            Activate each specialized agent in a logical order (e.g., Venue, then Budget, then catering, then social media, then proposal etc.).
            Present the output of each agent clearly under a specific heading for that agent.
            Conclude with the full Event Proposal generated by the sub agents, which ties everything together.
        If users asks to assume all the details, feel free to do so.
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
