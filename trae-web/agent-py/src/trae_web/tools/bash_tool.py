# copilotkit-work/trae-web/agent-py/src/tools/bash_tool.py
import asyncio
import os
from typing import Optional
from langchain_core.tools import tool


class _BashSession:
    """A session of a bash shell with persistent state."""

    _started: bool
    _timed_out: bool

    command: str = "/bin/bash"
    _output_delay: float = 0.2  # seconds
    _timeout: float = 120.0  # seconds
    _sentinel: str = ",,,,bash-command-exit-__ERROR_CODE__-banner,,,,"

    def __init__(self):
        self._started = False
        self._timed_out = False
        self._process: Optional[asyncio.subprocess.Process] = None

    async def start(self):
        if self._started:
            return

        if os.name != "nt":  # Unix-like systems
            self._process = await asyncio.create_subprocess_shell(
                self.command,
                shell=True,
                bufsize=0,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=os.setsid,
            )
        else:
            # Windows compatibility
            self._process = await asyncio.create_subprocess_shell(
                self.command,
                shell=True,
                bufsize=0,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

        self._started = True

    async def execute(self, command: str) -> str:
        if not self._started:
            await self.start()

        if self._timed_out:
            raise Exception("Bash session timed out")

        full_command = (
            f'{command}; echo "{self._sentinel.replace("__ERROR_CODE__", "$?")}"'
        )

        assert self._process and self._process.stdin
        self._process.stdin.write(full_command.encode() + b"\n")
        await self._process.stdin.drain()

        output_lines = []
        stderr_lines = []
        sentinel_found = False

        try:
            async with asyncio.timeout(self._timeout):
                while not sentinel_found:
                    await asyncio.sleep(self._output_delay)

                    # Read stdout
                    if self._process.stdout:
                        stdout_data = await self._process.stdout.read(4096)
                        if stdout_data:
                            output = stdout_data.decode()
                            output_lines.append(output)
                            if self._sentinel.replace("__ERROR_CODE__", "") in output:
                                sentinel_found = True

                    # Read stderr
                    if self._process.stderr:
                        stderr_data = await self._process.stderr.read(4096)
                        if stderr_data:
                            stderr_lines.append(stderr_data.decode())

        except asyncio.TimeoutError:
            self._timed_out = True
            raise Exception(f"Command timed out after {self._timeout} seconds")

        full_output = "".join(output_lines)
        full_stderr = "".join(stderr_lines)

        # Extract the actual command output (before sentinel)
        if sentinel_found:
            output_parts = full_output.split(
                self._sentinel.replace("__ERROR_CODE__", "")
            )
            command_output = output_parts[0].strip()
        else:
            command_output = full_output.strip()

        if full_stderr:
            command_output += f"\nSTDERR:\n{full_stderr}"

        return command_output

    async def close(self):
        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except:
                try:
                    self._process.kill()
                except:
                    pass
        self._started = False
        self._timed_out = False


# Global bash session
_bash_session: Optional[_BashSession] = None


@tool
async def bash_tool(command: str, restart: bool = False) -> str:
    """Execute shell commands in a persistent bash session.

    Features:
    - Commands run in a shared bash session that maintains state
    - 120-second timeout per command
    - Session restart capability
    - Background process support

    Usage notes:
    - Use `restart: true` to reset the session
    - Avoid commands with excessive output
    - Long-running commands should use `&` for background execution

    Args:
        command: The bash command to execute
        restart: Whether to restart the bash session (clears previous state)
    """
    global _bash_session

    if restart or _bash_session is None:
        if _bash_session:
            await _bash_session.close()
        _bash_session = _BashSession()

    try:
        result = await _bash_session.execute(command)
        return result
    except Exception as e:
        return f"Error executing command: {str(e)}"
