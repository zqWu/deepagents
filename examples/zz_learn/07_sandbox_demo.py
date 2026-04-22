import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()
"""
restapi方式, 使用 opensandbox-server
"""

OPEN_SANDBOX_API_KEY = os.getenv("OPEN_SANDBOX_API_KEY")


def create_sandbox() -> dict:
    """
    调用 sandbox-server api, 启动一个 sandbox, 也就是一个 docker容器
    """
    url = "http://118.145.224.211:8080/v1/sandboxes"

    headers = {
        "Content-Type": "application/json",
        "OPEN-SANDBOX-API-KEY": OPEN_SANDBOX_API_KEY
    }

    payload = {
        "image": {"uri": "ubuntu:22.04"},
        "entrypoint": ["tail", "-f", "/dev/null"],
        "timeout": 600,
        "volumes": [
            {
                "name": "agent-root",
                "host": {"path": "/agent-workspace"},
                "mountPath": "/agent-root-dir",
                "readOnly": False
            }
        ],
        "resourceLimits": {
            "cpu": "500m",
            "memory": "512Mi"
        }
    }

    response = requests.post(url, headers=headers, json=payload)

    # 输出响应结果
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")

    # 如果响应是 JSON 格式，可以解析
    if response.headers.get("Content-Type", "").startswith("application/json"):
        print(f"JSON Response: {json.dumps(response.json(), indent=2)}")
        return response.json()

    # result
    _ = """
        {
        "id": "e050c29d-dff3-4f38-8ba7-a84feaa0c057",
        "status": {
            "state": "Running", <======= 必须 running
            "reason": "CONTAINER_RUNNING",
            "message": "Sandbox container started successfully.",
            "lastTransitionAt": "2026-04-21T09:53:19.385908Z"
        },
        "expiresAt": "2026-04-21T10:23:19.385908Z",
        "createdAt": "2026-04-21T09:53:19.385908Z",
        "entrypoint": ["tail", "-f", "/dev/null"]
    }
    """


def get_exec_endpoint(sandbox_id):
    url = f"http://118.145.224.211:8080/v1/sandboxes/{sandbox_id}/endpoints/44772"
    headers = {
        "OPEN-SANDBOX-API-KEY": OPEN_SANDBOX_API_KEY
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    data = response.json()
    exec_endpoint = data.get("endpoint")
    print(f"Exec Endpoint: {exec_endpoint}")
    return exec_endpoint


def execute_command(exec_endpoint, command, background=False):
    url = f"{exec_endpoint}/command"

    headers = {
        "Content-Type": "application/json",
        "X-EXECD-ACCESS-TOKEN": OPEN_SANDBOX_API_KEY
    }

    payload = {
        "command": command,
        "background": background
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()

    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    return response


if __name__ == "__main__":
    resp = create_sandbox()
    if not resp["status"]["state"] == "Running":
        print(f"创建sandbox失败, 非 Running")
    else:
        sandbox_id = resp["id"]
        print(f"创建sandbox成功, id={sandbox_id}")  # id=2ee0a824-4fe6-4c70-9c81-a9805be6f118

        exec_ep = get_exec_endpoint(sandbox_id)
        print(f"exec_ep={exec_ep}")  # exec_ep=118.145.224.211:52979/proxy/44772
        exec_ep = f"http://{exec_ep}"

        exec_result = execute_command(exec_ep, command="ls -l /")
        print(exec_result)  # stream mode
        _ = """
Status Code: 200
Response: {"type":"init","text":"00821c9cbf30418cbcba3ef5ae0f5350","timestamp":1776822770408}

{"type":"ping","text":"pong","timestamp":1776822770408}

{"type":"stdout","text":"total 49","timestamp":1776822770409}

{"type":"stdout","text":"drwx------   1 root root    0 Jan  1  1970 agent-root-dir","timestamp":1776822770409}

{"type":"stdout","text":"lrwxrwxrwx   1 root root    7 Apr 10 02:21 bin -\u003e usr/bin","timestamp":1776822770409}

{"type":"stdout","text":"drwxr-xr-x   2 root root 4096 Apr 18  2022 boot","timestamp":1776822770409}

{"type":"stdout","text":"drwxr-xr-x   5 root root  340 Apr 22 01:52 dev","timestamp":1776822770409}

{"type":"stdout","text":"drwxr-xr-x   1 root root 4096 Apr 22 01:52 etc","timestamp":1776822770409}

{"type":"stdout","text":"drwxr-xr-x   2 root root 4096 Apr 18  2022 home","timestamp":1776822770409}

{"type":"stdout","text":"lrwxrwxrwx   1 root root    7 Apr 10 02:21 lib -\u003e usr/lib","timestamp":1776822770409}

{"type":"stdout","text":"lrwxrwxrwx   1 root root    9 Apr 10 02:21 lib32 -\u003e usr/lib32","timestamp":1776822770409}

{"type":"stdout","text":"lrwxrwxrwx   1 root root    9 Apr 10 02:21 lib64 -\u003e usr/lib64","timestamp":1776822770409}

{"type":"stdout","text":"lrwxrwxrwx   1 root root   10 Apr 10 02:21 libx32 -\u003e usr/libx32","timestamp":1776822770409}

{"type":"stdout","text":"drwxr-xr-x   2 root root 4096 Apr 10 02:21 media","timestamp":1776822770409}

{"type":"stdout","text":"drwxr-xr-x   2 root root 4096 Apr 10 02:21 mnt","timestamp":1776822770409}

{"type":"stdout","text":"drwxr-xr-x   1 root root 4096 Apr 22 01:52 opt","timestamp":1776822770409}

{"type":"stdout","text":"dr-xr-xr-x 219 root root    0 Apr 22 01:52 proc","timestamp":1776822770409}

{"type":"stdout","text":"drwx------   2 root root 4096 Apr 10 02:31 root","timestamp":1776822770409}

{"type":"stdout","text":"drwxr-xr-x   5 root root 4096 Apr 10 02:31 run","timestamp":1776822770409}

{"type":"stdout","text":"lrwxrwxrwx   1 root root    8 Apr 10 02:21 sbin -\u003e usr/sbin","timestamp":1776822770409}

{"type":"stdout","text":"drwxr-xr-x   2 root root 4096 Apr 10 02:21 srv","timestamp":1776822770409}

{"type":"stdout","text":"dr-xr-xr-x  13 root root    0 Apr 22 01:52 sys","timestamp":1776822770409}

{"type":"stdout","text":"drwxrwxrwt   1 root root 4096 Apr 22 01:52 tmp","timestamp":1776822770409}

{"type":"stdout","text":"drwxr-xr-x  14 root root 4096 Apr 10 02:21 usr","timestamp":1776822770409}

{"type":"stdout","text":"drwxr-xr-x  11 root root 4096 Apr 10 02:31 var","timestamp":1776822770409}

{"type":"execution_complete","execution_time":1,"timestamp":1776822770409}
"""
