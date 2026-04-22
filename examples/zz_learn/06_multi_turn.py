from deepagents import create_deep_agent
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()


def main():
    # 创建带持久化的 agent
    checkpointer = MemorySaver()
    agent = create_deep_agent(
        model=ChatOpenAI(model="gpt-35-turbo", temperature=0),
        checkpointer=checkpointer,
    )

    # 使用 thread_id 标识对话线程
    config = {"configurable": {"thread_id": "conversation-123"}}
    # 第一轮对话
    result1 = agent.invoke({"messages": [HumanMessage(content="创建一个a.txt, 并写入当前日期. 返回文件绝对路径")]},
                           config)

    # 第二轮对话 - 传递之前的历史
    result2 = agent.invoke({"messages": result1["messages"] + [HumanMessage(content="读取a.txt内容")], }, config)
    print(result2["messages"][-1].content)


if __name__ == "__main__":
    main()
