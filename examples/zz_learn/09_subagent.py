from deepagents import SubAgent, create_deep_agent
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()
from langchain.agents.middleware.types import (
    AgentMiddleware,
)

_ = """
默认情况下，subagent 与主 agent 使用相同的 backend，但存在例外情况。
"""


class SubagentLogMiddleware(AgentMiddleware):
    def __init__(self, name: str | None = None):
        self._name = name

    def before_agent(self, state, runtime):
        print(f"before_agent {self._name}")

    def after_agent(self, state, runtime):
        print(f"after_agent {self._name}")


def main() -> None:
    math_adder: SubAgent = {
        "name": "math-adder",
        "description": "Specialized agent for addition operations",
        "system_prompt": "You perform addition calculations",
        "model": ChatOpenAI(model="gpt-35-turbo", temperature=0),
        "middleware": [SubagentLogMiddleware("math-adder")]
    }
    math_multiplier: SubAgent = {
        "name": "math-multiplier",
        "description": "Specialized agent for multiplication operations",
        "system_prompt": "You perform multiplication calculations",
        "model": ChatOpenAI(model="gpt-35-turbo", temperature=0),
        "middleware": [SubagentLogMiddleware("math-multiplier")]
    }

    # 主 agent 可以通过 task 工具把复杂任务委托给 planner
    agent = create_deep_agent(
        model=ChatOpenAI(model="gpt-35-turbo", temperature=0),
        subagents=[math_adder, math_multiplier],
    )

    result = agent.invoke({
        "messages": [{"role": "user", "content": "What is 5+7 and what is 4*6?"}]
    })

    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
