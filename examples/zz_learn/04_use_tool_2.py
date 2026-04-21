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

    # 在调用时预置文件
    result = agent.invoke({
        "messages": [HumanMessage(content="列出根目录文件")],
        "files": {
            "/test.txt": {"content": "Hello World", "encoding": "utf-8"},
            "/docs/readme.md": {"content": "# Documentation", "encoding": "utf-8"}
        }
    })

    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
