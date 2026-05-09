from deepagents import create_deep_agent
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

load_dotenv()


# Define custom tools for our sub-agents
@tool
def get_weather(city: str) -> str:
    """Get weather information for a city."""
    return f"Weather in {city}: 22°C, sunny"


@tool
def get_soccer_scores(team: str) -> str:
    """Get latest soccer scores for a team."""
    return f"Latest scores for {team}: Won 3-1"


agent_model = ChatOpenAI(model="gpt-5.4", temperature=0)


def main():
    subagents = [
        {
            "name": "weather_agent",
            "description": "Use this agent to get weather information",
            "system_prompt": "You are a weather agent. Use the get_weather tool to provide weather information.",
            "tools": [get_weather],
            # "model": agent_model,  # override main agent's model
        },
        {
            "name": "soccer_agent",
            "description": "Use this agent to get latest soccer scores",
            "system_prompt": "You are a soccer agent. Use the get_soccer_scores tool to provide match information.",
            "tools": [get_soccer_scores],
        },
        # Pre-compiled sub-agent example
        # {
        #     "name": "research_agent",
        #     "description": "General research agent",
        #     "runnable": create_agent(
        #         model="openai:gpt-4o",
        #         tools=[get_weather, get_soccer_scores],
        #         system_prompt="You are a research assistant that can gather various information."
        #     ),
        # }
    ]

    main_agent = create_deep_agent(
        model=agent_model,
        subagents=subagents,
        system_prompt="You are an orchestrator agent that delegates tasks to specialized sub-agents."
    )

    result = main_agent.invoke({
        "messages": [
            HumanMessage(content="What's the weather in Tokyo and what are the latest scores for Manchester City?")]
    })

    print(result)
    # The agent will:
    # 1. Call task tool with weather_agent for weather query
    # 2. Call task tool with soccer_agent for scores query
    # 3. Synthesize both results into a final response


if __name__ == "__main__":
    main()
