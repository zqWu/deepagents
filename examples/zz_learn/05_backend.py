from deepagents import create_deep_agent
from deepagents.backends.local_shell import LocalShellBackend
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

load_dotenv()


def main():
    # agent 底层用来处理 “文件系统/执行环境/状态存储” 的适配层
    # 提供统一的文件操作接口 ls/read/write/edit/glob/grep/文件上传和下载
    # /home/dormi330/ws/deepagents/libs/deepagents/deepagents/backends/protocol.py
    backend = LocalShellBackend(
        virtual_mode=False,  # 真实环境, 可以访问 .. | True的话 root_dir是设置的
        # root_dir="/home/dormi330/ws/deepagents/examples/zz_learn",
        timeout=60,  # 60秒超时
        max_output_bytes=50_000  # 最大输出50KB
    )

    # 创建 agent（backend含 execute 工具）
    agent = create_deep_agent(
        model=ChatOpenAI(model="gpt-35-turbo", temperature=0),
        backend=backend,
    )

    # 使用 execute 工具列出当前目录
    result = agent.invoke({
        "messages": [HumanMessage(content="列出根目录文件")]
    })

    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
