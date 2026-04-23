import os

from deepagents import create_deep_agent
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from libs.deepagents.deepagents.backends.filesystem import FilesystemBackend

load_dotenv()


def t_skill(user_prompt: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    agent = create_deep_agent(
        model=ChatOpenAI(model="gpt-5.4", temperature=0),  # gpt-35-turbo 效果差
        backend=FilesystemBackend(root_dir=base_dir),
        skills=[f"./skills/"],
    )
    result = agent.invoke(
        {
            "messages": [
                HumanMessage(content=user_prompt),
            ]
        }
    )
    print(result["messages"][-1].content)


if __name__ == "__main__":
    t_skill("web search news about JinSonZ . return directly, DO NOT INTERPRET OR SUMMARY")
