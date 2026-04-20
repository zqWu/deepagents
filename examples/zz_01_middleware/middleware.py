from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from deepagents.middleware._utils import append_to_system_message
from langchain.agents.middleware.types import (
    AgentMiddleware,
    ContextT,
    ModelRequest,
    ModelResponse,
    ResponseT,
)
from langchain_core.messages import SystemMessage


class AppendSystemPromptMiddleWare(AgentMiddleware[dict[str, Any], ContextT, ResponseT]):
    """
    修改prompt, 添加prompt = 使用中文回答
    """
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

    def modify_request(
        self,
        request: ModelRequest[ContextT],
    ) -> ModelRequest[ContextT]:
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
