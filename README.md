# Build an Event Planner Agent with Google ADK (Python)

id: event-planner-adk-python
summary: Build an interactive Event Planner Agent using Google ADK (Python)
authors: Yuba Raj (UV) Panta
categories: AI, Bot Development
environments: Python, Virtualenv, Google Cloud
status: Draft
feedback link: [https://github.com/uvishere/event-planner-adk/issues/new](https://github.com/uvishere/event-planner-adk/issues/new)

```js
Last Updated: 12 June 2025
Authors: Yuba Raj (UV) Panta
```

## Overview

duration: 1:00

Getting started with AI often means asking yourself, “Can a model really tackle the challenge on my mind?” That’s exactly where Google AI Studio shines—letting you spin up quick experiments whenever inspiration strikes. Imagine you’re organizing a big conference and need help lining up venues, catering, budgets and marketing—but you’re not an event planner by trade. You might not even know the right questions to ask. So first, you hand that problem to Gemini: have it draft the perfect, detailed prompt; turn that into a complete event plan; even produce a mock-up of the venue layout.

Great—but how do you turn these one-off prompts into a repeatable, end-to-end service your company can use? Enter **Agents**.

An **agent** is a self-directed program that interacts with an AI model, leverages available tools and context, and makes decisions autonomously to achieve a specific goal.

But how to build these agents?

### The Agent Development Kit (ADK)

The **Agent Development Kit** is a modular framework for building and deploying AI agents. With ADK you can break a complex workflow into multiple specialized agents—each responsible for a piece of the puzzle—and then compose them into a **Multi-Agent System (MAS)** that collaborates to reach a bigger objective.

Structuring your solution as a MAS brings clear benefits:

* **Modularity & Specialization:** Each agent focuses on a single domain (e.g., venue selection, budgeting, marketing).
* **Reusability:** Swap or upgrade individual agents without overhauling the entire system.
* **Maintainability:** Smaller, well-defined components are easier to test and debug.
* **Controlled Workflows:** Use dedicated “orchestrator” agents to manage the sequence of steps and decision logic.

### What You’ll Build

In this codelab, you’ll transform our prompt-centric prototype into a fully fledged agent: one that generates a polished **Event Proposal Document** for your conference. You’ll learn how to:

1. **Implement** a basic ADK agent that collects requirements and drafts the proposal.
2. **Persist** the generated document to a Google Cloud Storage bucket.
3. **Run** and **test** your agent both locally (Cloud Shell) and via a simple web endpoint.

### Requirements

* A modern browser (Chrome, Firefox, etc.)
* A Google Cloud project with billing enabled
* Python 3.10+ and virtualenv (or your preferred env tool)
* A cup of coffee (or beer), you choose!

---

## Before you Begin

### **Create a Google Cloud Project**

Jump to **step 4** if you've already created a project and setup the billing/credits.

1. **Select or create a project**

   * In the Google Cloud Console, go to the project selector and either pick an existing project or click **New Project** to make one.

2. **Enable billing**

   * Ensure your project has billing turned on. You can verify this under **Billing → Overview**. If it isn’t enabled, follow the steps in the Cloud Console to attach a billing account.

3. **Redeem free credits (optional)**

   * If you’d like some starter credits for Google Cloud and ADK, contact the organisers. Follow the on-screen instructions to apply the credit to your project.

4. **Open Cloud Shell**

   * Click the “Activate Cloud Shell” button in the Console (or use this direct link).
   * In Cloud Shell you can switch between the **Terminal** (for `gcloud` commands) and the **Editor** (for editing files) using the buttons at the top of the Cloud Shell window.

5. **Confirm authentication and project**

   * Run `gcloud auth list` to see your logged-in accounts.
   * Run `gcloud config list project` to check which project is active.
   * If it’s not set to your desired project, run: `gcloud config set project YOUR_PROJECT_ID`

6. **Verify Python version**

   * Make sure you have **Python 3.9+** installed in your Cloud Shell environment (or locally, if you’re developing on your machine).

7. **Further reading**

   * For additional details on `gcloud` commands and usage, see the [Cloud SDK documentation](https://cloud.google.com/sdk/docs).

---

## Step 1: Explore the AI studio

Duration: 00:05

```bash
# Clone the repository
git clone https://github.com/uvishere/event-planner-adk.git
cd event-planner-adk
```

The main agent implementation is in `event-planner-agent/agent.py`.

---

## Step 2: Set up the Python Environment

Duration: 10 minutes

1. **Create and activate a virtual environment:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

1. **Install dependencies:**

   ```bash
   pip install google-adk 
   ```

1. Create necesary files and folders
   Create the following folder structure:

   ```md
   event-planner-adk/  # Project folder
   └── event-planner-agent/ # Agent folder
      ├── __init__.py # Python package
      └── agent.py # Agent definition
      └── .env # environment file
   ```

Create and go inside the directory:
`mkdir event-planner-agent && cd event-planner-agent`

create followign empty files

`touch __init__.py agent.py .env`

1. **Create a `.env` file in the project root and populate it:**

   ```text
   GOOGLE_API_KEY=YOUR_GOOGLE_API_KEY
   GOOGLE_CLOUD_PROJECT_ID=YOUR_PROJECT_ID
   GOOGLE_CLOUD_LOCATION=YOUR_LOCATION  # e.g. us-central1
   GOOGLE_GENAI_USE_VERTEXAI=true
   GOOGLE_MAPS_API_KEY=YOUR_MAPS_API_KEY  # optional, for venue tools
   ```

1. **Load environment variables:**

   ```bash
   source .env
   ```

---

## Step 3: Explore the Code Structure

Duration: 15 minutes

Open `event-planner-agent/agent.py` in your editor. Key components:

* **Tool implementations** (mock examples):
  * `check_availability(venue_name, date)` – checks venue availability (mocked).
  * `create_budget_and_fill_sheet(budget_data, spreadsheet_name)` – mocks budget creation and returns a spreadsheet URL.

* **Sub-agents:**
  * `get_venues_agent` – an `Agent` that uses `check_availability` and web search for venues.
  * `catering_agent` – an `LlmAgent` for catering recommendations.
  * `social_media_agent` – an `LlmAgent` to craft social media posts.
  * `budget_agent` – an `LlmAgent` that calls `create_budget_and_fill_sheet`.

* **Root agent:**
  * `root_agent` – an `Agent` with all sub-agents registered, delegating tasks based on user requests.

* **Runner and sessions:**
  * `InMemorySessionService`, `Runner`, and `call_agent(query)` function for testing.

Take a moment to read through the intent instructions and tool wiring in the code.

---

## Step 4: Add a Test Harness

Duration: 5 minutes

Although `agent.py` includes a `call_agent` coroutine, you can add a simple test script `test_agent.py` in the `event-planner-agent/` directory:

```python
# event-planner-agent/test_agent.py
import asyncio
from dotenv import load_dotenv
from agent import call_agent

if __name__ == "__main__":
    load_dotenv()
    # Example: Create an event
    asyncio.run(call_agent("Schedule an event at Darwin Waterfront on 2025-06-15"))
```

Run it:

```bash
python event-planner-agent/test_agent.py
```

Observe console output for the agent's response.

---

## Step 5: Deploy the Agent on cloud Run

Duration: 00:02

Setup environment variables

```bash
   export $GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT_ID
   export $GOOGLE_CLOUD_LOCATION=$GOOGLE_CLOUD_LOCATION
   export $SERVICE_NAME=event-planner-agent
   export $APP_NAME=event-planner-agent
   export $AGENT_PATH=./event-planner-agent
```

Run the following command to deploy

```bash
adk deploy cloud_run \
--project=$GOOGLE_CLOUD_PROJECT \
--region=$GOOGLE_CLOUD_LOCATION \
--service_name=$SERVICE_NAME \
--app_name=$APP_NAME \
--with_ui \
$AGENT_PATH
```

Now just wait for few minutes as

---

## Step 6: Exercises and Next Steps

* **Add a `delete_event` tool** to remove events from storage.
* **Integrate real Firestore storage** instead of mock implementations.
* **Enhance `social_media_agent`** to generate images via MCPTool.
* **Connect to Google Calendar API** for live event creation.

Feel free to file issues or submit PRs: [https://github.com/uvishere/event-planner-adk/issues/new](https://github.com/uvishere/event-planner-adk/issues/new)

---

Congratulations—your Event Planner Agent is up and running with ADK in Python! 🎉
