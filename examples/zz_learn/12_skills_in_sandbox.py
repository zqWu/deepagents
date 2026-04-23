import base64
import os
import traceback
from datetime import timedelta
from pathlib import PurePosixPath

from deepagents import create_deep_agent
from deepagents.backends.protocol import (
    EditResult,
    ExecuteResponse,
    FileData,
    FileDownloadResponse,
    FileInfo,
    FileUploadResponse,
    GlobResult,
    GrepMatch,
    GrepResult,
    LsResult,
    ReadResult,
    SandboxBackendProtocol,
    WriteResult,
)
from deepagents.backends.utils import _get_file_type, perform_string_replacement, slice_read_response
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from opensandbox.config import ConnectionConfigSync
from opensandbox.exceptions import SandboxException
from opensandbox.models.execd import RunCommandOpts
from opensandbox.models.filesystem import SearchEntry, WriteEntry
from opensandbox.models.sandboxes import Host, Volume
from opensandbox.sync.sandbox import SandboxSync

load_dotenv()

OPEN_SANDBOX_API_KEY = os.getenv("OPEN_SANDBOX_API_KEY")
SANDBOX_DOMAIN = os.getenv("OPEN_SANDBOX_DOMAIN", "118.145.224.211:8080")
SANDBOX_PROTOCOL = os.getenv("OPEN_SANDBOX_PROTOCOL", "http")
SANDBOX_WORKDIR = "/agent-root-dir"
MAX_OUTPUT_BYTES = 50_000


class OpenSandboxBackend(SandboxBackendProtocol):
    """ 使用 opensandbox 做为 文件系统+执行环境 """

    def __init__(
        self,
        sandbox: SandboxSync,
        *,
        root_dir: str = SANDBOX_WORKDIR,
        timeout: int = 60,
        max_output_bytes: int = MAX_OUTPUT_BYTES,
    ) -> None:
        self._sandbox = sandbox
        self._root_dir = self._normalize_root_dir(root_dir)
        self._default_timeout = timeout
        self._max_output_bytes = max_output_bytes

    @property
    def id(self) -> str:
        """Return the sandbox identifier."""
        return self._sandbox.id

    def execute(
        self,
        command: str,
        *,
        timeout: int | None = None,
    ) -> ExecuteResponse:
        """Execute a shell command in the sandbox working directory."""
        if not command.strip():
            return ExecuteResponse(
                output="Error: Command must be a non-empty string.",
                exit_code=1,
                truncated=False,
            )

        effective_timeout = self._default_timeout if timeout is None else timeout
        opts = RunCommandOpts(
            working_directory=self._root_dir,
            timeout=timedelta(seconds=effective_timeout),
        )

        try:
            execution = self._sandbox.commands.run(command, opts=opts)
        except SandboxException as exc:
            return ExecuteResponse(
                output=f"Error executing command: {exc}",
                exit_code=1,
                truncated=False,
            )

        chunks: list[str] = []
        for msg in execution.logs.stdout:
            chunks.append(msg.text.rstrip("\n"))
        for msg in execution.logs.stderr:
            chunks.append(f"[stderr] {msg.text.rstrip()}")
        if execution.error is not None:
            chunks.append(f"[error] {execution.error.name}: {execution.error.value}")

        output = "\n".join(chunk for chunk in chunks if chunk) or "<no output>"
        truncated_output, truncated = self._truncate_output(output)

        return ExecuteResponse(
            output=truncated_output,
            exit_code=execution.exit_code,
            truncated=truncated,
        )

    def ls(self, path: str) -> LsResult:
        sandbox_path = self._to_sandbox_path(path)
        base_path = PurePosixPath(sandbox_path)
        try:
            found = self._sandbox.files.search(SearchEntry(path=sandbox_path, pattern="*"))
        except SandboxException as exc:
            return LsResult(error=f"Error listing '{path}': {exc}")

        top_level_paths: set[str] = set()
        for item in found:
            try:
                entry_path = PurePosixPath(item.path)
                relative = entry_path.relative_to(base_path)
            except ValueError:
                continue
            if not relative.parts:
                continue
            top_level_path = str(base_path / relative.parts[0])
            top_level_paths.add(top_level_path)

        if not top_level_paths:
            return LsResult(entries=[])

        try:
            info_map = self._sandbox.files.get_file_info(sorted(top_level_paths))
        except SandboxException as exc:
            return LsResult(error=f"Error listing '{path}': {exc}")

        entries: list[FileInfo] = []
        for top_level_path in sorted(top_level_paths):
            item = info_map.get(top_level_path)
            if item is None:
                continue
            is_dir = item.size == 0
            result_path = item.path.rstrip("/") + "/" if is_dir else item.path
            entry: FileInfo = {
                "path": result_path,
                "is_dir": is_dir,
                "size": int(item.size),
                "modified_at": item.modified_at.isoformat(),
            }
            entries.append(entry)

        entries.sort(key=lambda item: item["path"])
        return LsResult(entries=entries)

    def read(
        self,
        file_path: str,
        offset: int = 0,
        limit: int = 2000,
    ) -> ReadResult:
        """Read a file from the sandbox filesystem."""
        sandbox_path = self._to_sandbox_path(file_path)
        try:
            if _get_file_type(file_path) != "text":
                raw = self._sandbox.files.read_bytes(sandbox_path)
                return ReadResult(
                    file_data=FileData(
                        content=base64.b64encode(raw).decode("ascii"),
                        encoding="base64",
                    )
                )

            try:
                text = self._sandbox.files.read_file(sandbox_path, encoding="utf-8")
            except UnicodeDecodeError:
                raw = self._sandbox.files.read_bytes(sandbox_path)
                return ReadResult(
                    file_data=FileData(
                        content=base64.b64encode(raw).decode("ascii"),
                        encoding="base64",
                    )
                )
        except SandboxException as exc:
            return ReadResult(error=f"File '{file_path}': {exc}")

        file_data = FileData(content=text, encoding="utf-8")
        sliced = slice_read_response(file_data, offset=offset, limit=limit)
        if isinstance(sliced, ReadResult):
            return sliced
        return ReadResult(file_data=FileData(content=sliced, encoding="utf-8"))

    def write(
        self,
        file_path: str,
        content: str,
    ) -> WriteResult:
        """Create a new file inside the sandbox."""
        sandbox_path = self._to_sandbox_path(file_path)
        if self._exists(sandbox_path):
            return WriteResult(error=f"Error: File already exists: '{file_path}'")

        parent = str(PurePosixPath(sandbox_path).parent)
        try:
            if parent not in ("", "."):
                self._sandbox.files.create_directories([WriteEntry(path=parent, mode=755)])
            self._sandbox.files.write_file(sandbox_path, content, encoding="utf-8", mode=644)
        except SandboxException as exc:
            return WriteResult(error=f"Failed to write file '{file_path}': {exc}")
        return WriteResult(path=file_path)

    def edit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> EditResult:
        """Edit a text file inside the sandbox by exact string replacement."""
        sandbox_path = self._to_sandbox_path(file_path)
        old_string = old_string.replace("\r\n", "\n").replace("\r", "\n")
        new_string = new_string.replace("\r\n", "\n").replace("\r", "\n")
        try:
            content = self._sandbox.files.read_file(sandbox_path, encoding="utf-8")
        except UnicodeDecodeError:
            return EditResult(error=f"Error: File '{file_path}' is not a text file")
        except SandboxException as exc:
            return EditResult(error=f"Error editing file '{file_path}': {exc}")

        replacement = perform_string_replacement(content, old_string, new_string, replace_all)
        if isinstance(replacement, str):
            return EditResult(error=replacement)

        updated_content, occurrences = replacement
        try:
            self._sandbox.files.write_file(sandbox_path, updated_content, encoding="utf-8", mode=644)
        except SandboxException as exc:
            return EditResult(error=f"Error editing file '{file_path}': {exc}")
        return EditResult(path=file_path, occurrences=int(occurrences))

    def glob(self, pattern: str, path: str = "/") -> GlobResult:
        search_path, search_pattern = self._resolve_search(path, pattern)
        try:
            found = self._sandbox.files.search(SearchEntry(path=search_path, pattern=search_pattern))
        except SandboxException as exc:
            return GlobResult(error=f"Error globbing '{pattern}' from '{path}': {exc}")

        matches: list[FileInfo] = []
        for item in found:
            if item.size == 0:
                continue
            try:
                virtual_path = self._to_virtual_path(item.path)
            except ValueError:
                continue
            matches.append(
                {
                    "path": virtual_path,
                    "is_dir": False,
                    "size": int(item.size),
                    "modified_at": item.modified_at.isoformat(),
                }
            )
        matches.sort(key=lambda item: item["path"])
        return GlobResult(matches=matches)

    def grep(
        self,
        pattern: str,
        path: str | None = None,
        glob: str | None = None,
    ) -> GrepResult:
        """Search for a literal string inside sandbox files."""
        matches: list[GrepMatch] = []
        search_path, search_pattern = self._resolve_search(path or "/", glob or "**/*")
        try:
            candidates = self._sandbox.files.search(SearchEntry(path=search_path, pattern=search_pattern))
        except SandboxException as exc:
            return GrepResult(error=f"Error grepping '{pattern}': {exc}")

        for item in candidates:
            if item.size == 0:
                continue
            try:
                content = self._sandbox.files.read_file(item.path, encoding="utf-8")
                virtual_path = self._to_virtual_path(item.path)
            except (SandboxException, UnicodeDecodeError, ValueError):
                continue
            for index, line in enumerate(content.splitlines(), 1):
                if pattern in line:
                    matches.append(
                        {
                            "path": virtual_path,
                            "line": index,
                            "text": line,
                        }
                    )

        return GrepResult(matches=matches)

    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        responses: list[FileUploadResponse] = []
        for path, content in files:
            sandbox_path = self._to_sandbox_path(path)
            parent = str(PurePosixPath(sandbox_path).parent)
            try:
                if parent not in ("", ".", "/"):
                    self._sandbox.files.create_directories([WriteEntry(path=parent, mode=755)])
                self._sandbox.files.write_file(sandbox_path, content, mode=644)
            except SandboxException as exc:
                traceback.print_exc()
                responses.append(FileUploadResponse(path=path, error=None))
                continue
            responses.append(FileUploadResponse(path=path, error=None))
        return responses

    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        responses: list[FileDownloadResponse] = []
        for path in paths:
            sandbox_path = self._to_sandbox_path(path)
            try:
                info_map = self._sandbox.files.get_file_info([sandbox_path])
                info = info_map.get(sandbox_path)
                if info is None:
                    responses.append(FileDownloadResponse(path=path, error="file_not_found"))
                    continue
                if info.size == 0:
                    responses.append(FileDownloadResponse(path=path, error="is_directory"))
                    continue
                content = self._sandbox.files.read_bytes(sandbox_path)
            except SandboxException as exc:
                error_text = str(exc).lower()
                if "not found" in error_text:
                    error = "file_not_found"
                elif "permission" in error_text:
                    error = "permission_denied"
                else:
                    error = str(exc)
                responses.append(FileDownloadResponse(path=path, error=error))
                continue

            responses.append(FileDownloadResponse(path=path, content=content, error=None))
        return responses

    def close(self) -> None:
        self._sandbox.close()

    def kill(self) -> None:
        self._sandbox.kill()

    @staticmethod
    def _normalize_root_dir(root_dir: str) -> str:
        parts = [part for part in PurePosixPath(root_dir).parts if part not in ("", "/")]
        return "/" + "/".join(parts) if parts else "/"

    def _to_sandbox_path(self, virtual_path: str) -> str:
        normalized = PurePosixPath("/" + virtual_path.lstrip("/"))
        if ".." in normalized.parts or "~" in normalized.parts:
            msg = f"Invalid path: {virtual_path}"
            raise ValueError(msg)
        return str(normalized)

    def _to_virtual_path(self, sandbox_path: str) -> str:
        normalized = PurePosixPath("/" + str(sandbox_path).lstrip("/"))
        if ".." in normalized.parts or "~" in normalized.parts:
            msg = f"Invalid path: {sandbox_path}"
            raise ValueError(msg)
        return str(normalized)

    def _exists(self, sandbox_path: str) -> bool:
        try:
            return sandbox_path in self._sandbox.files.get_file_info([sandbox_path])
        except SandboxException:
            return False

    def _resolve_search(self, path: str, pattern: str) -> tuple[str, str]:
        if pattern.startswith("/"):
            return self._root_dir, pattern.lstrip("/")
        return self._to_sandbox_path(path), pattern

    def _truncate_output(self, output: str) -> tuple[str, bool]:
        output_bytes = output.encode("utf-8")
        if len(output_bytes) <= self._max_output_bytes:
            return output, False

        truncated = output_bytes[: self._max_output_bytes].decode("utf-8", errors="ignore")
        return truncated + "\n[output truncated]", True


def create_sandbox() -> SandboxSync:
    if not OPEN_SANDBOX_API_KEY:
        msg = "OPEN-SANDBOX-API-KEY is not set"
        raise ValueError(msg)

    config = ConnectionConfigSync(
        domain=SANDBOX_DOMAIN,
        protocol=SANDBOX_PROTOCOL,
        api_key=OPEN_SANDBOX_API_KEY,
    )
    volumes = [
        Volume(
            name="agent-root",
            host=Host(path="/agent-workspace/agent-1"),
            mount_path=SANDBOX_WORKDIR,
            read_only=False,
        )
    ]

    sandbox = SandboxSync.create(
        image="ubuntu:22.04",  # 这里没有python环境, 测试在环境不足时, 系统是否正常工作
        entrypoint=["tail", "-f", "/dev/null"],
        timeout=timedelta(minutes=10),
        resource={"cpu": "500m", "memory": "512Mi"},
        volumes=volumes,
        connection_config=config,
    )

    info = sandbox.get_info()
    if info.status.state != "Running":
        msg = f"Sandbox is not running: {info.status.state}"
        raise RuntimeError(msg)

    return sandbox


def t_skill_in_sandbox(user_prompt: str) -> None:
    sandbox = create_sandbox()
    print(f"done: 创建 sandbox, id={sandbox.id}")
    backend = OpenSandboxBackend(sandbox)

    try:
        agent = create_deep_agent(
            model=ChatOpenAI(model="gpt-5.4", temperature=0),  # gpt-5.4 gpt-35-turbo
            backend=backend,
            skills=["/agent-root-dir/skills/"],  # 使用 backend 中的 skills
        )
        result = agent.invoke(
            {
                "messages": [
                    HumanMessage(content=user_prompt),
                ]
            }
        )
        print(result["messages"][-1].content)
    finally:
        # backend.kill()
        # backend.close()
        # 保留sandbox, 进行人工验证
        pass


if __name__ == "__main__":
    # sandbox = ubuntu, 没有python
    # t_skill_in_sandbox("research quantum computing。直接返回, 不要解读。")
#     _ = """
# done: 创建 sandbox, id=09d04f22-5f2b-4eb1-a43f-1dee6c6b1732
# 无法执行搜索脚本：当前环境没有可用的 `python` / `python3`。
# """
    t_skill_in_sandbox("检查有没有python3, 没有则进行安装")

