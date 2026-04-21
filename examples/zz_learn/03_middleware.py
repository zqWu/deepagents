from __future__ import annotations

import sys
from collections.abc import Awaitable, Callable
from typing import Any

from deepagents import create_deep_agent
from deepagents.middleware._utils import append_to_system_message
from dotenv import load_dotenv
from langchain.agents.middleware.types import (
    AgentMiddleware,
    ContextT,
    ModelRequest,
    ModelResponse,
    ResponseT,
)
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from rich.console import Console
from rich.panel import Panel


class AppendSystemPromptMiddleWare(AgentMiddleware[dict[str, Any], ContextT, ResponseT]):
    """ 在system prompt中添加 内容= 使用中文回答"""
    def __init__(self, *, instruction: str = "使用中文回答") -> None:
        self._instruction = instruction

    def _system_message_text(self, system_message: SystemMessage | None) -> str:
        if system_message is None:
            return ""
        text_blocks = []
        for block in system_message.content_blocks:
            if block.get("type") == "text":
                text = block.get("text")
                if isinstance(text, str):
                    text_blocks.append(text)
        return "\n".join(text_blocks)

    def modify_request(self, request: ModelRequest[ContextT], ) -> ModelRequest[ContextT]:
        if self._instruction in self._system_message_text(request.system_message):
            return request

        new_system_message = append_to_system_message(request.system_message, self._instruction)
        return request.override(system_message=new_system_message)

    def wrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[[ModelRequest[ContextT]], ModelResponse[ResponseT]],
    ) -> ModelResponse[ResponseT]:
        modified_request = self.modify_request(request)
        return handler(modified_request)

    async def awrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[[ModelRequest[ContextT]], Awaitable[ModelResponse[ResponseT]]],
    ) -> ModelResponse[ResponseT]:
        modified_request = self.modify_request(request)
        return await handler(modified_request)


load_dotenv()


def main():
    console = Console()
    agent = create_deep_agent(
        model=ChatOpenAI(model="gpt-35-turbo", temperature=0),
        middleware=[AppendSystemPromptMiddleWare()],
    )
    try:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": "brief introduction of yourself"}]}
        )

        # Extract and display the final answer
        final_message = result["messages"][-1]
        answer = (
            final_message.content
            if hasattr(final_message, "content")
            else str(final_message)
        )

        console.print(
            Panel(f"[bold green]Answer:[/bold green]\n\n{answer}", border_style="green")
        )

    except Exception as e:
        console.print(
            Panel(f"[bold red]Error:[/bold red]\n\n{str(e)}", border_style="red")
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
