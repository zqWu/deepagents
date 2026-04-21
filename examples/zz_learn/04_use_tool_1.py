from deepagents import create_deep_agent
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

load_dotenv()


def main():
    # 创建 agent（默认包含 ls 工具）
    agent = create_deep_agent(
        model=ChatOpenAI(model="gpt-35-turbo", temperature=0),
    )

    # 使用 ls 工具
    result = agent.invoke({
        "messages": [HumanMessage(content="请列出当前目录的文件")]
    })

    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
