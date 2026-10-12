"""Filesystem locations used by the harness (repo side and installed side)."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

IS_WINDOWS = os.name == "nt"

HOME = Path(os.environ.get("HARNESS_TEST_HOME", Path.home()))
CLAUDE_DIR = HOME / ".claude"
CODEX_DIR = HOME / ".codex"
HARNESS_HOME = Path(os.environ.get("HARNESS_HOME", CLAUDE_DIR / "harness"))
SETTINGS = CLAUDE_DIR / "settings.json"
CLAUDE_JSON = HOME / ".claude.json"
CONFIG = HARNESS_HOME / "config.json"

REPO = Path(__file__).resolve().parents[2]
REPO_CLAUDE = REPO / "claude"
REPO_CODEX = REPO / "codex"
REPO_TEMPLATE = REPO / "templates" / "project"

for _d in ("events", "sessions", "status", "state", "jev", "backups"):
    pass  # created lazily by ensure_dirs()


def shell_path(p: Path | str) -> str:
    """A path as hook commands spell it. Claude Code runs hooks through bash (Git Bash on Windows),
    where a backslash is an escape character, so always forward slashes."""
    return Path(p).as_posix()


def bash_cmd() -> list[str]:
    """Prefix for running one of our .sh scripts from Python: nothing on POSIX (the shebang does it),
    Git Bash on Windows. Never System32\\bash.exe, which is the WSL launcher."""
    if not IS_WINDOWS:
        return []
    cands = [os.environ.get("CLAUDE_CODE_GIT_BASH_PATH", "")]
    git = shutil.which("git")
    if git:  # <Git>\cmd\git.exe or <Git>\mingw64\bin\git.exe -> <Git>\bin\bash.exe
        cands += [str(d / "bin" / "bash.exe") for d in list(Path(git).resolve().parents)[1:3]]
    cands.append(r"C:\Program Files\Git\bin\bash.exe")
    found = shutil.which("bash") or ""
    if "system32" not in found.lower():
        cands.append(found)
    for c in cands:
        if c and Path(c).is_file():
            return [c]
    return ["bash"]


def pid_alive(pid: int) -> bool:
    """Is this process running? os.kill(pid, 0) is only a probe on POSIX: on Windows signal 0 is
    CTRL_C_EVENT, so it would send Ctrl+C to the process instead of testing for it."""
    if not IS_WINDOWS:
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    k32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    k32.CloseHandle.argtypes = (wintypes.HANDLE,)
    h = k32.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    try:
        code = wintypes.DWORD()
        return bool(k32.GetExitCodeProcess(h, ctypes.byref(code))) and code.value == 259   # STILL_ACTIVE
    finally:
        k32.CloseHandle(h)


def ensure_dirs() -> None:
    for d in ("events", "sessions", "status", "state", "jev", "backups"):
        (HARNESS_HOME / d).mkdir(parents=True, exist_ok=True)


def events_file(session_id: str) -> Path:
    return HARNESS_HOME / "events" / f"{session_id}.jsonl"


def session_file(session_id: str) -> Path:
    return HARNESS_HOME / "sessions" / f"{session_id}.json"


def status_file(session_id: str) -> Path:
    return HARNESS_HOME / "status" / f"{session_id}.json"


def jev_file(session_id: str) -> Path:
    return HARNESS_HOME / "jev" / f"{session_id}.jsonl"


def state_dir(session_id: str) -> Path:
    return HARNESS_HOME / "state" / session_id
