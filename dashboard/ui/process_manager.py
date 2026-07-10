"""
ProcessManager — QProcess wrapper for orchestrating the server and client processes.

Exposes clean signals for UI logging and state changes.
Ensures subprocesses are cleaned up correctly upon exit.
"""

from __future__ import annotations

import sys
from pathlib import Path
from PyQt6.QtCore import QObject, QProcess, QProcessEnvironment, pyqtSignal

from dashboard.setup.setup_manager import VENV_PYTHON

# Resolve paths relative to repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SERVER_DIR = _REPO_ROOT / "balkontech-server"
_CLIENT_DIR = _REPO_ROOT / "balkontech-client"

# Prefer fwa venv python; fall back to the current interpreter
_PYTHON = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable


class ProcessManager(QObject):
    """Manages external subprocesses (balkontech-server and balkontech-client)."""

    # Emitted with (process_name, text_chunk)
    log_received = pyqtSignal(str, str)
    # Emitted with (process_name, is_running)
    state_changed = pyqtSignal(str, bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._server_proc: QProcess | None = None
        self._client_proc: QProcess | None = None
        # Clean up port 8000 on startup to prevent orphaned backend instances
        self.free_port()

    @property
    def server_running(self) -> bool:
        return (
            self._server_proc is not None
            and self._server_proc.state() == QProcess.ProcessState.Running
        )

    @property
    def client_running(self) -> bool:
        return (
            self._client_proc is not None
            and self._client_proc.state() == QProcess.ProcessState.Running
        )

    # ── Server Subprocess ─────────────────────────────────────────────────────

    def free_port(self) -> None:
        """Ensures port 8000 is completely free on Linux."""
        import subprocess
        self.log_received.emit("server", "[Dashboard] Cleaning up port 8000...\n")
        try:
            subprocess.run(["fuser", "-k", "8000/tcp"], capture_output=True)
        except Exception:
            pass
        try:
            subprocess.run("kill -9 $(lsof -t -i:8000)", shell=True, capture_output=True)
        except Exception:
            pass

    def start_server(self) -> None:
        """Starts the FastAPI uvicorn server in a separate process."""
        if self.server_running:
            return

        # Ensure port 8000 is free first
        self.free_port()

        self._server_proc = QProcess(self)
        self._server_proc.setWorkingDirectory(str(_SERVER_DIR))
        self._server_proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        # Force unbuffered Python stdout/stderr so logs appear instantly
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        self._server_proc.setProcessEnvironment(env)

        self._server_proc.readyReadStandardOutput.connect(self._read_server_output)
        self._server_proc.finished.connect(self._server_finished)

        python_bin = _PYTHON
        args = [
            "-m", "uvicorn",
            "api.main:app",
            "--host", "127.0.0.1",
            "--port", "8000",
            "--log-level", "info",
        ]
        self._server_proc.start(python_bin, args)
        self.state_changed.emit("server", True)
        self.log_received.emit("server", f"[Dashboard] Spawning Server: {python_bin} {' '.join(args)}\n")

    def stop_server(self) -> None:
        """Gracefully terminates the server process."""
        if not self.server_running or self._server_proc is None:
            # Always ensure the port is freed
            self.free_port()
            return
        self.log_received.emit("server", "[Dashboard] Terminating Server...\n")
        self._terminate_proc(self._server_proc)
        self._server_proc = None
        self.state_changed.emit("server", False)
        self.free_port()

    def _read_server_output(self) -> None:
        if self._server_proc:
            data = self._server_proc.readAllStandardOutput()
            text = bytes(data).decode("utf-8", errors="replace")
            self.log_received.emit("server", text)

    def _server_finished(self, exit_code: int) -> None:
        self.state_changed.emit("server", False)
        self.log_received.emit("server", f"[Dashboard] Server exited with code {exit_code}.\n")
        self.free_port()

    # ── Client Subprocess ─────────────────────────────────────────────────────

    def start_client(self) -> None:
        """Starts the PyQt6 client in a separate process."""
        if self.client_running:
            return

        self._client_proc = QProcess(self)
        self._client_proc.setWorkingDirectory(str(_CLIENT_DIR))
        self._client_proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        # Force unbuffered Python stdout/stderr
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        self._client_proc.setProcessEnvironment(env)

        self._client_proc.readyReadStandardOutput.connect(self._read_client_output)
        self._client_proc.finished.connect(self._client_finished)

        python_bin = _PYTHON
        args = ["main.py"]
        self._client_proc.start(python_bin, args)
        self.state_changed.emit("client", True)
        self.log_received.emit("client", f"[Dashboard] Spawning Client: {python_bin} {' '.join(args)}\n")

    def stop_client(self) -> None:
        """Gracefully terminates the client process."""
        if not self.client_running or self._client_proc is None:
            return
        self.log_received.emit("client", "[Dashboard] Terminating Client...\n")
        self._terminate_proc(self._client_proc)
        self._client_proc = None
        self.state_changed.emit("client", False)

    def _read_client_output(self) -> None:
        if self._client_proc:
            data = self._client_proc.readAllStandardOutput()
            text = bytes(data).decode("utf-8", errors="replace")
            self.log_received.emit("client", text)

    def _client_finished(self, exit_code: int) -> None:
        self.state_changed.emit("client", False)
        self.log_received.emit("client", f"[Dashboard] Client exited with code {exit_code}.\n")

    # ── Lifecycle / Cleanup ───────────────────────────────────────────────────

    def terminate_all(self) -> None:
        """Stops all running child processes and cleans up port."""
        self.stop_client()
        self.stop_server()
        self.free_port()

    def _terminate_proc(self, proc: QProcess) -> None:
        proc.terminate()
        if not proc.waitForFinished(3000):
            proc.kill()
            proc.waitForFinished(1000)
