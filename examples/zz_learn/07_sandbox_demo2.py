# pip install opensandbox==0.1.7
# server端版本保存一致
import os
from datetime import timedelta

from dotenv import load_dotenv
from opensandbox.config import ConnectionConfigSync
from opensandbox.models.sandboxes import Volume, Host
from opensandbox.sync.sandbox import SandboxSync

load_dotenv()
"""
sdk方式, 使用 opensandbox-server
"""

OPEN_SANDBOX_API_KEY = os.getenv("OPEN_SANDBOX_API_KEY")


def create_sandbox_with_sdk():
    """使用 SDK 创建 sandbox"""
    # 配置连接
    config = ConnectionConfigSync(
        domain="118.145.224.211:8080",
        protocol="http",
        api_key=OPEN_SANDBOX_API_KEY
    )

    # 定义卷挂载
    volumes = [
        Volume(
            name="agent-root",
            host=Host(path="/agent-workspace"),
            mount_path="/agent-root-dir",
            read_only=False
        )
    ]

    # 创建 sandbox
    sandbox = SandboxSync.create(
        image="ubuntu:22.04",
        entrypoint=["tail", "-f", "/dev/null"],
        timeout=timedelta(seconds=600),
        resource={"cpu": "500m", "memory": "512Mi"},
        volumes=volumes,
        connection_config=config
    )

    print(f"创建sandbox成功, id={sandbox.id}")

    # 验证状态
    info = sandbox.get_info()
    if info.status.state != "Running":
        print(f"创建sandbox失败, 状态: {info.status.state}")
        return None

    return sandbox


def execute_command_with_sdk(sandbox, command):
    """使用 SDK 执行命令"""
    # SDK 自动处理端点获取和认证
    execution = sandbox.commands.run(command)

    # 输出结果
    for msg in execution.logs.stdout:
        print(f"STDOUT: {msg.text}")

    if execution.logs.stderr:
        for msg in execution.logs.stderr:
            print(f"STDERR: {msg.text}")

    return execution


if __name__ == "__main__":
    # 创建 sandbox
    sandbox = create_sandbox_with_sdk()
    if not sandbox:
        exit(1)

    try:
        # 执行命令
        result = execute_command_with_sdk(sandbox, "ls -l /")
        print(f"命令执行完成，退出码: {result.exit_code}")
    finally:
        # 清理资源
        sandbox.kill()
        sandbox.close()
