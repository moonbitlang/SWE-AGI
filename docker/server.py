#!/usr/bin/env python3
"""
Server for handling MoonBit project testing
Provides REST API for test execution requests
"""

import os
import json
import re
import selectors
import shutil
import subprocess
import signal
import threading
import uuid
from pathlib import Path
from datetime import datetime
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

# Directory paths
WORKSPACE_DIR = Path("/workspace")
CLIENT_DATA_DIR = WORKSPACE_DIR / "client_data"
SERVER_DATA_DIR = WORKSPACE_DIR / "server_data"

# Server configuration
HOST = "0.0.0.0"
PORT = 8080

# Timeout configuration (in seconds) - can be overridden via environment variables
GRACE_PERIOD = int(os.environ.get("GRACE_PERIOD", "5"))
BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "120"))
MOON_TEST_TIMEOUT = int(os.environ.get("MOON_TEST_TIMEOUT", "10800"))
CDCL_TEST_TIMEOUT = int(os.environ.get("CDCL_TEST_TIMEOUT", "10800"))
PER_TEST_TIMEOUT = int(os.environ.get("PER_TEST_TIMEOUT", "10"))
SSE_KEEPALIVE_INTERVAL = int(os.environ.get("SSE_KEEPALIVE_INTERVAL", "15"))

# Process registry for cancellation support (one active request per project_name)
_active_requests_by_project = (
    {}
)  # {project_name: {"request_id": str, "project_name": str, "proc": Popen | None, "cancelled": threading.Event}}
_request_to_project = {}  # {request_id: project_name}
_active_request_lock = threading.Lock()


def try_register_request(project_name, request_id):
    """Try to register as the active request for a project.

    Returns (cancelled_event, None) on success, or
    (None, conflict_info) if another request is already running.
    """
    event = threading.Event()
    project_name = project_name or "toml"

    with _active_request_lock:
        existing = _active_requests_by_project.get(project_name)
        if existing is not None:
            return None, {
                "reason": "project_busy",
                "request_id": existing["request_id"],
                "project_name": project_name,
            }

        existing_project = _request_to_project.get(request_id)
        if existing_project is not None:
            return None, {
                "reason": "request_id_busy",
                "request_id": request_id,
                "project_name": existing_project,
            }

        _active_requests_by_project[project_name] = {
            "request_id": request_id,
            "project_name": project_name,
            "proc": None,
            "cancelled": event,
        }
        _request_to_project[request_id] = project_name

    return event, None


def register_process(request_id, proc):
    """Associate subprocess with the active request."""
    with _active_request_lock:
        project_name = _request_to_project.get(request_id)
        if project_name is None:
            return
        active = _active_requests_by_project.get(project_name)
        if active is not None and active["request_id"] == request_id:
            active["proc"] = proc


def unregister_request(request_id):
    """Remove the active request (only if it matches request_id)."""
    with _active_request_lock:
        project_name = _request_to_project.pop(request_id, None)
        if project_name is None:
            return
        active = _active_requests_by_project.get(project_name)
        if active is not None and active["request_id"] == request_id:
            del _active_requests_by_project[project_name]


def cancel_request(request_id):
    """Cancel the active request. Returns status string."""
    with _active_request_lock:
        project_name = _request_to_project.get(request_id)
        if project_name is None:
            return "not_found"
        active = _active_requests_by_project.get(project_name)
        if active is None or active["request_id"] != request_id:
            return "not_found"

        active["cancelled"].set()
        proc = active["proc"]

    # Kill outside lock
    if proc is not None and proc.poll() is None:
        terminate_process_gracefully(proc)
        return "cancelled"
    return "no_process"


def send_sse_event(wfile, event_type: str, data: dict) -> bool:
    """
    Send SSE event: 'event: type\ndata: json\n\n'
    Returns True on success, False if client disconnected.
    """
    try:
        message = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        wfile.write(message.encode("utf-8"))
        wfile.flush()
        return True
    except (BrokenPipeError, ConnectionResetError, OSError):
        return False


def send_sse_comment(wfile, comment: str) -> bool:
    """
    Send SSE keep-alive comment: ': comment\n\n'
    Returns True on success, False if client disconnected.
    """
    try:
        message = f": {comment}\n\n"
        wfile.write(message.encode("utf-8"))
        wfile.flush()
        return True
    except (BrokenPipeError, ConnectionResetError, OSError):
        return False


def log(msg):
    """Log messages with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[SERVER {timestamp}] {msg}", flush=True)


def terminate_process_gracefully(proc, grace_period=GRACE_PERIOD):
    """
    Terminate a process gracefully, then forcefully if needed.

    1. Send SIGTERM to allow graceful shutdown
    2. Wait up to grace_period seconds
    3. If still running, send SIGKILL to force termination (including children)

    Args:
        proc: subprocess.Popen instance
        grace_period: seconds to wait after SIGTERM before SIGKILL

    Returns:
        tuple: (stdout, stderr) from the process
    """
    if proc.poll() is not None:
        # Process already terminated
        return proc.communicate()

    log(f"Terminating process {proc.pid} gracefully (SIGTERM)...")
    try:
        proc.terminate()  # Send SIGTERM
    except ProcessLookupError:
        # Process already died
        return proc.communicate()

    # Wait for graceful shutdown
    try:
        stdout, stderr = proc.communicate(timeout=grace_period)
        log(f"Process {proc.pid} terminated gracefully")
        return stdout, stderr
    except subprocess.TimeoutExpired:
        # Grace period expired, force kill
        log(
            f"Process {proc.pid} did not terminate after {grace_period}s, force killing (SIGKILL)..."
        )

        # Kill process group to ensure all child processes are terminated
        try:
            # Get process group ID and kill the entire group
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGKILL)
            log(f"Sent SIGKILL to process group {pgid}")
        except (ProcessLookupError, PermissionError, OSError) as e:
            # Fallback to killing just the main process
            log(f"Could not kill process group: {e}, killing main process")
            try:
                proc.kill()
            except ProcessLookupError:
                pass

        # Collect any remaining output
        try:
            stdout, stderr = proc.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            # Should not happen after SIGKILL, but handle it
            proc.kill()
            stdout, stderr = proc.communicate()

        log(f"Process {proc.pid} force killed")
        return stdout, stderr


def init_directories():
    """Initialize workspace directories"""
    CLIENT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    SERVER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    log(f"Initialized directories in {WORKSPACE_DIR}")


def copy_project(src_dir, dst_dir):
    """Copy project from client_data to server_data (merges with existing files)"""
    try:
        dst_dir = Path(dst_dir)
        if dst_dir.exists() and dst_dir.is_dir():
            # Before copying, keep:
            # - *_priv_test.mbt files
            # - *_priv_test directories (and their contents)
            # and delete everything else.
            #
            # This preserves private tests while ensuring other files are refreshed from src_dir.

            def _is_under_priv_test_dir(path: Path) -> bool:
                cur = path
                while True:
                    if cur.name.endswith("_priv_test"):
                        return True
                    if cur == dst_dir:
                        return False
                    parent = cur.parent
                    if parent == cur:
                        return False
                    cur = parent

            # Pass 1: delete files (skip private tests and anything inside *_priv_test/).
            for root, dirs, files in os.walk(dst_dir, topdown=True):
                root_path = Path(root)
                if root_path != dst_dir and _is_under_priv_test_dir(root_path):
                    # Preserve the whole subtree under *_priv_test/.
                    dirs[:] = []
                    continue
                for filename in files:
                    file_path = root_path / filename
                    if file_path.name.endswith("_priv_test.mbt"):
                        continue
                    try:
                        file_path.unlink()
                    except FileNotFoundError:
                        pass

            # Pass 2: remove now-empty directories (but never prune *_priv_test/ or its subtree).
            for root, dirs, _files in os.walk(dst_dir, topdown=False):
                root_path = Path(root)
                if root_path != dst_dir and _is_under_priv_test_dir(root_path):
                    continue
                for dirname in dirs:
                    dir_path = root_path / dirname
                    if _is_under_priv_test_dir(dir_path):
                        continue
                    try:
                        if dir_path.exists() and dir_path.is_dir() and not any(
                            dir_path.iterdir()
                        ):
                            dir_path.rmdir()
                    except (FileNotFoundError, OSError):
                        pass

        # Copy entire directory, merging with existing files
        # Ignore build artifacts that may contain symlinks or cause conflicts
        shutil.copytree(
            src_dir,
            dst_dir,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(".git", "target", "_build", ".mooncakes"),
        )
        log(f"Copied project from {src_dir} to {dst_dir}")
    except Exception as e:
        # Log error but continue - build/test will fail if critical files are missing
        log(f"Warning: Error during copy (continuing anyway): {e}")

    return True  # Always continue to evaluation


SUMMARY_RE = re.compile(r"Total tests:\s*(\d+),\s*passed:\s*(\d+),\s*failed:\s*(\d+)")

_TEST_DECL_RE_TEMPLATE = r'^\s*test\s+"{name}"\s*\{{\s*$'


def _parse_test_summary(output):
    match = SUMMARY_RE.search(output)
    if not match:
        return None
    return {
        "total": int(match.group(1)),
        "passed": int(match.group(2)),
        "failed": int(match.group(3)),
    }


def _parse_failure_jsonl(output):
    failures = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(item, dict):
            continue
        if "test_name" not in item:
            continue
        failures.append(item)
    return failures


def _extract_test_block_from_text(text, test_name):
    """
    Best-effort extraction of:

      test "..." { ... }

    Returns dict: {start_line, end_line, source} or None.
    """
    if not text or not test_name:
        return None

    lines = text.splitlines()
    decl_re = re.compile(_TEST_DECL_RE_TEMPLATE.format(name=re.escape(test_name)))

    start_line = None
    for idx, line in enumerate(lines):
        if decl_re.match(line):
            start_line = idx
            break
    if start_line is None:
        return None

    # Include MoonBit doc comments immediately preceding the test declaration, e.g.
    #   ///|
    #   /// some description
    header_start = start_line
    while header_start > 0:
        prev = lines[header_start - 1]
        if prev.strip() == "":
            # Keep blank lines inside a doc-comment block, but stop if we haven't
            # seen any doc comment yet.
            if header_start == start_line:
                break
            header_start -= 1
            continue
        if re.match(r"^\s*///", prev):
            header_start -= 1
            continue
        break

    brace_balance = 0
    saw_opening_brace = False
    in_string = False
    escape = False

    end_line = start_line
    for idx in range(start_line, len(lines)):
        end_line = idx
        line = lines[idx]
        for ch in line:
            if in_string:
                if escape:
                    escape = False
                    continue
                if ch == "\\":
                    escape = True
                    continue
                if ch == '"':
                    in_string = False
                continue

            if ch == '"':
                in_string = True
                continue
            if ch == "{":
                brace_balance += 1
                saw_opening_brace = True
                continue
            if ch == "}":
                brace_balance -= 1
                continue

        if saw_opening_brace and brace_balance == 0:
            break

    source = "\n".join(lines[header_start : end_line + 1])
    return {
        "start_line": header_start + 1,
        "end_line": end_line + 1,
        "source": source,
    }


def _find_test_file(project_dir, failure):
    if not project_dir:
        return None
    filename = failure.get("filename")
    package = failure.get("package")
    if not filename:
        return None

    project_dir = Path(project_dir)
    candidates = []
    if package:
        candidates.append(project_dir / package / filename)
    candidates.append(project_dir / filename)

    for path in candidates:
        try:
            if path.exists():
                return path
        except OSError:
            continue

    try:
        for path in project_dir.rglob(filename):
            if path.is_file():
                return path
    except OSError:
        return None

    return None


def _format_failure_message(failure, project_dir=None):
    test_name = failure.get("test_name", "unknown")
    message = failure.get("message", "")
    kind = failure.get("kind", "")
    expected = failure.get("expected", "")
    actual = failure.get("actual", "")

    if isinstance(message, dict):
        try:
            message = json.dumps(message, ensure_ascii=True)
        except TypeError:
            message = str(message)

    # Build comprehensive error message
    error_parts = [test_name]
    if kind:
        error_parts.append(f"[{kind}]")
    if message:
        error_parts.append(message)
    if expected and actual:
        error_parts.append(f"(expected: {expected}, actual: {actual})")

    summary = ": ".join(error_parts) if len(error_parts) > 1 else error_parts[0]

    test_file = _find_test_file(project_dir, failure)
    if not test_file or not test_name:
        return summary

    try:
        text = test_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return summary

    block = _extract_test_block_from_text(text, test_name)
    if not block:
        return summary

    source = block["source"]
    max_chars = 2000
    truncated = ""
    if len(source) > max_chars:
        source = source[:max_chars]
        truncated = "\n... (truncated)"

    return (
        f"{summary}\n\n"
        f"--- test case: {test_file}#L{block['start_line']} ---\n"
        f"{source}{truncated}\n"
        f"--- end test case ---"
    )


def _parse_cdcl_jsonl(output):
    """
    Parse JSONL output from cdcl/try.py --json

    Returns: tuple of (failures, summary)
    - failures: list of dicts with test_name, status, message for non-pass tests
    - summary: dict with total, passed, failed or None
    """
    failures = []
    summary = None
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(item, dict):
            continue
        if item.get("summary"):
            summary = {
                "total": item.get("total", 0),
                "passed": item.get("passed", 0),
                "failed": item.get("failed", 0),
            }
        elif item.get("status") and item.get("status") != "pass":
            failures.append(item)
    return failures, summary


def _is_selection_error(message: str) -> bool:
    if not message:
        return False
    lower = message.lower()
    return "not unique" in lower or "not found" in lower


def run_moon_build(project_dir, timeout=BUILD_TIMEOUT, request_id=None, cancelled=None):
    """
    Execute moon test --build-only in the project directory

    Returns: dict with status, exit_code, output (on failure), and message
    """
    if cancelled is not None and cancelled.is_set():
        return {"status": "cancelled", "exit_code": -1, "output": None, "message": "Cancelled"}

    log(f"Running moon test --build-only in {project_dir} (timeout={timeout}s)")

    proc = None
    try:
        proc = subprocess.Popen(
            ["moon", "test", "--build-only"],
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,  # Create new process group for better child management
        )
        if request_id:
            register_process(request_id, proc)

        stdout, stderr = proc.communicate(timeout=timeout)

        if cancelled is not None and cancelled.is_set():
            return {"status": "cancelled", "exit_code": -1, "output": None, "message": "Cancelled"}

        output = stdout + stderr

        if proc.returncode == 0:
            log("Build succeeded")
            return {
                "status": "pass",
                "exit_code": 0,
                "output": None,
                "message": "Build succeeded",
            }
        else:
            log(f"Build failed with exit code {proc.returncode}")
            return {
                "status": "fail",
                "exit_code": proc.returncode,
                "output": output,
                "message": "Build failed",
            }

    except subprocess.TimeoutExpired:
        log("Build timed out, attempting graceful termination")
        if proc is not None:
            stdout, stderr = terminate_process_gracefully(proc)
            output = stdout + stderr
        else:
            output = f"Build timed out after {timeout} seconds"

        return {
            "status": "error",
            "exit_code": -1,
            "output": output,
            "message": "Timeout",
        }
    except Exception as e:
        log(f"Error running build: {e}")
        return {
            "status": "error",
            "exit_code": -1,
            "output": str(e),
            "message": "Execution error",
        }


def run_moon_test(project_dir, timeout=MOON_TEST_TIMEOUT, request_id=None, cancelled=None):
    """
    Execute moon test in the project directory with JSON failure output

    moon test --test-failure-json behavior:
    - All tests pass: no JSON output, exit code 0
    - Any test fails: JSON output to stdout, exit code != 0

    Returns: dict with status, summary, and limited error information
    """
    if cancelled is not None and cancelled.is_set():
        return {"status": "cancelled", "exit_code": -1, "summary": None, "errors": None, "message": "Cancelled"}

    log(f"Running moon test in {project_dir} (timeout={timeout}s)")

    proc = None
    try:
        proc = subprocess.Popen(
            ["moon", "test", "--test-failure-json"],
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,  # Create new process group for better child management
        )
        if request_id:
            register_process(request_id, proc)

        stdout, stderr = proc.communicate(timeout=timeout)

        if cancelled is not None and cancelled.is_set():
            return {"status": "cancelled", "exit_code": -1, "summary": None, "errors": None, "message": "Cancelled"}

        output = stdout + stderr
        summary = _parse_test_summary(output)
        failures = _parse_failure_jsonl(output)

        # Format error messages (limit to 5)
        errors = None
        if failures:
            errors = [
                _format_failure_message(failure, project_dir=project_dir)
                for failure in failures[:5]
            ]

        if proc.returncode == 0:
            test_result = {
                "status": "pass",
                "exit_code": 0,
                "summary": summary,
                "errors": None,
                "message": "All tests passed",
            }
        elif failures:
            failed_count = summary["failed"] if summary else len(failures)
            test_result = {
                "status": "fail",
                "exit_code": proc.returncode,
                "summary": summary,
                "errors": errors,
                "message": f"{failed_count} test(s) failed",
            }
        else:
            # Tests failed but no JSON output (unexpected)
            test_result = {
                "status": "fail",
                "exit_code": proc.returncode,
                "summary": summary,
                "errors": [output],  # Return the entire raw output
                "message": "Tests failed (unable to parse results)",
            }

        log(
            f"Moon test completed: {test_result['status']} (exit code: {proc.returncode})"
        )
        return test_result

    except subprocess.TimeoutExpired:
        log("Moon test timed out, attempting graceful termination")
        if proc is not None:
            stdout, stderr = terminate_process_gracefully(proc)
            output = stdout + stderr
        else:
            output = ""

        return {
            "status": "error",
            "exit_code": -1,
            "summary": None,
            "errors": [f"Test execution timed out after {timeout} seconds"],
            "message": "Timeout",
        }
    except Exception as e:
        log(f"Error running moon test: {e}")
        return {
            "status": "error",
            "exit_code": -1,
            "summary": None,
            "errors": [str(e)],
            "message": "Execution error",
        }


def run_cdcl_test(
    project_dir,
    timeout=CDCL_TEST_TIMEOUT,
    per_test_timeout=PER_TEST_TIMEOUT,
    test_name=None,
    test_file=None,
    request_id=None,
    cancelled=None,
):
    """
    Execute python try.py --json in the project directory for CDCL tests

    Args:
        project_dir: Path to the project directory
        timeout: Overall timeout for the test execution in seconds
        per_test_timeout: Per-test timeout passed to try.py --timeout (optional)

    Returns: dict with status, summary, and limited error information
    """
    if cancelled is not None and cancelled.is_set():
        return {"status": "cancelled", "exit_code": -1, "summary": None, "errors": None, "message": "Cancelled"}

    log(
        f"Running CDCL tests (try.py --json) in {project_dir} (timeout={timeout}s, per_test_timeout={per_test_timeout})"
    )

    cmd = ["python3", "try.py", "--json"]
    if per_test_timeout is not None:
        cmd.extend(["--timeout", str(per_test_timeout)])
    if test_name:
        cmd.extend(["--test-name", str(test_name)])
    if test_file:
        cmd.extend(["--test-file", str(test_file)])

    proc: subprocess.Popen[str] | None = None
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,  # Create new process group for better child management
        )
        if request_id:
            register_process(request_id, proc)

        stdout, stderr = proc.communicate(timeout=timeout)

        if cancelled is not None and cancelled.is_set():
            return {"status": "cancelled", "exit_code": -1, "summary": None, "errors": None, "message": "Cancelled"}

        output = stdout + stderr

        failures, summary = _parse_cdcl_jsonl(output)

        # Format error messages (limit to 5)
        errors = None
        if failures:
            errors = []
            for f in failures[:5]:
                test_name = f.get("test_name", "unknown")
                status = f.get("status", "fail")
                message = f.get("message", "")
                if message:
                    errors.append(f"{test_name} [{status}]: {message[:200]}")
                else:
                    errors.append(f"{test_name} [{status}]")

        if proc.returncode == 0 and (not summary or summary.get("failed", 0) == 0):
            test_result = {
                "status": "pass",
                "exit_code": 0,
                "summary": summary,
                "errors": None,
                "message": "All tests passed",
            }
        elif proc.returncode != 0 and not failures and summary is None:
            message = output.strip() or "Tests failed (unable to parse results)"
            if _is_selection_error(message):
                test_result = {
                    "status": "error",
                    "exit_code": proc.returncode,
                    "summary": None,
                    "errors": [message],
                    "message": message,
                }
            else:
                test_result = {
                    "status": "fail",
                    "exit_code": proc.returncode,
                    "summary": summary,
                    "errors": [message],
                    "message": "Tests failed (unable to parse results)",
                }
        elif failures or (summary and summary.get("failed", 0) > 0):
            failed_count = summary["failed"] if summary else len(failures)
            test_result = {
                "status": "fail",
                "exit_code": proc.returncode,
                "summary": summary,
                "errors": errors,
                "message": f"{failed_count} test(s) failed",
            }
        else:
            # Tests failed but no structured output
            test_result = {
                "status": "fail",
                "exit_code": proc.returncode,
                "summary": summary,
                "errors": [output],  # Return the entire raw output
                "message": "Tests failed (unable to parse results)",
            }

        log(
            f"CDCL test completed: {test_result['status']} (exit code: {proc.returncode})"
        )
        return test_result

    except subprocess.TimeoutExpired:
        log("CDCL test timed out, attempting graceful termination")
        if proc is not None:
            stdout, stderr = terminate_process_gracefully(proc)
            output = stdout + stderr
            log(f"CDCL test timed out, captured {len(output)} bytes of output")
        else:
            output = ""
            log("CDCL test timed out, but no process was running")
        # Parse whatever results we got
        failures, summary = _parse_cdcl_jsonl(output)

        # Format error messages (same as success path)
        errors = None
        if failures:
            errors = []
            for f in failures[:5]:
                test_name = f.get("test_name", "unknown")
                status = f.get("status", "fail")
                message = f.get("message", "")
                if message:
                    errors.append(f"{test_name} [{status}]: {message[:200]}")
                else:
                    errors.append(f"{test_name} [{status}]")

        if not output.strip():
            # No output at all - complete timeout
            return {
                "status": "error",
                "exit_code": -1,
                "summary": None,
                "errors": [
                    f"Test execution timed out after {timeout} seconds (no results)"
                ],
                "message": "Timeout",
            }

        # We have partial results
        return {
            "status": "timeout",
            "exit_code": -1,
            "summary": summary,  # May be None if timeout occurred before summary
            "errors": errors,
            "message": "Timeout with partial results",
            "partial": True,
        }
    except Exception as e:
        log(f"Error running CDCL test: {e}")
        return {
            "status": "error",
            "exit_code": -1,
            "summary": None,
            "errors": [str(e)],
            "message": "Execution error",
        }


def run_cdcl_test_streaming(
    wfile,
    project_dir,
    timeout=CDCL_TEST_TIMEOUT,
    per_test_timeout=PER_TEST_TIMEOUT,
    keepalive_interval=SSE_KEEPALIVE_INTERVAL,
    test_name=None,
    test_file=None,
    request_id=None,
    cancelled=None,
):
    """
    Execute python try.py --json in the project directory with SSE streaming.

    Reads stdout line-by-line and forwards results as SSE events in real-time.

    Args:
        wfile: HTTP response file object for writing SSE events
        project_dir: Path to the project directory
        timeout: Overall timeout for the test execution in seconds
        per_test_timeout: Per-test timeout passed to try.py --timeout
        keepalive_interval: Seconds between keep-alive comments

    Returns: dict with status, summary, and limited error information
    """
    if cancelled is not None and cancelled.is_set():
        return {"status": "cancelled", "exit_code": -1, "summary": None, "errors": None, "message": "Cancelled"}

    log(
        f"Running CDCL tests (streaming) in {project_dir} (timeout={timeout}s, per_test_timeout={per_test_timeout})"
    )

    cmd = ["python3", "try.py", "--json"]
    if per_test_timeout is not None:
        cmd.extend(["--timeout", str(per_test_timeout)])
    if test_name:
        cmd.extend(["--test-name", str(test_name)])
    if test_file:
        cmd.extend(["--test-file", str(test_file)])

    proc: subprocess.Popen[str] | None = None
    sel = None
    failures = []
    summary = None
    test_index = 0
    test_total: int | None = None  # Set when we receive test_count event
    client_disconnected = False

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
            start_new_session=True,
        )
        if request_id:
            register_process(request_id, proc)

        sel = selectors.DefaultSelector()
        if proc.stdout is None:
            raise RuntimeError("Failed to capture stdout from subprocess")
        stdout_stream = proc.stdout
        sel.register(stdout_stream, selectors.EVENT_READ, "stdout")

        start_time = datetime.now()
        last_keepalive = start_time

        while proc.poll() is None and not client_disconnected:
            # Check overall timeout
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > timeout:
                log(f"CDCL streaming test timed out after {elapsed:.1f}s")
                break

            # Select with 1 second timeout for keepalive checks
            events = sel.select(timeout=1.0)

            if not events:
                # No data available, check if we need to send keepalive
                now = datetime.now()
                if (now - last_keepalive).total_seconds() >= keepalive_interval:
                    if not send_sse_comment(wfile, "keep-alive"):
                        client_disconnected = True
                        log("Client disconnected during keepalive")
                        break
                    last_keepalive = now
                continue

            for key, _ in events:
                if key.data == "stdout":
                    line = stdout_stream.readline()
                    if not line:
                        continue

                    line = line.strip()
                    if not line:
                        continue

                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if not isinstance(item, dict):
                        continue

                    if "test_count" in item:
                        # This is the test count event (emitted before tests run)
                        test_total = item.get("test_count", 0)
                    elif item.get("summary"):
                        # This is the summary line
                        summary = {
                            "total": item.get("total", 0),
                            "passed": item.get("passed", 0),
                            "failed": item.get("failed", 0),
                        }
                        if not send_sse_event(wfile, "summary", summary):
                            client_disconnected = True
                            break
                    elif "test_name" in item:
                        # This is a test result
                        test_index += 1
                        status = item.get("status", "unknown")

                        # Track failures for final result
                        if status != "pass":
                            failures.append(item)

                        # Build SSE event data
                        event_data = {
                            "test_name": item.get("test_name", "unknown"),
                            "status": status,
                            "index": test_index,
                        }
                        if test_total is not None:
                            event_data["total"] = test_total
                        if item.get("message"):
                            event_data["message"] = item.get("message", "")

                        if not send_sse_event(wfile, "test_result", event_data):
                            client_disconnected = True
                            break

        # Clean up selector
        if sel:
            sel.close()

        # Handle client disconnect
        if client_disconnected:
            log("Client disconnected, terminating test process")
            if proc and proc.poll() is None:
                terminate_process_gracefully(proc)
            return {
                "status": "cancelled",
                "exit_code": -1,
                "summary": summary,
                "errors": None,
                "message": "Client disconnected",
            }

        # Handle cancellation
        if cancelled is not None and cancelled.is_set():
            log("CDCL streaming test cancelled")
            if proc and proc.poll() is None:
                terminate_process_gracefully(proc)
            return {
                "status": "cancelled",
                "exit_code": -1,
                "summary": summary,
                "errors": None,
                "message": "Cancelled",
            }

        # Check if we exited due to timeout
        if proc.poll() is None:
            log("CDCL streaming test timed out, terminating process")
            terminate_process_gracefully(proc)

            # Send error event for timeout
            send_sse_event(
                wfile,
                "error",
                {
                    "phase": "test",
                    "message": f"Test execution timed out after {timeout} seconds",
                },
            )

            return {
                "status": "timeout",
                "exit_code": -1,
                "summary": summary,
                "errors": [f"Test execution timed out after {timeout} seconds"],
                "message": "Timeout with partial results",
                "partial": True,
            }

        # Process completed normally - read any remaining stderr
        _, stderr = proc.communicate(timeout=1)
        if stderr:
            log(f"CDCL test stderr: {stderr[:500]}")

        if proc.returncode != 0 and not failures and summary is None:
            message = (stderr or "").strip() or "Tests failed (unable to parse results)"
            if _is_selection_error(message):
                send_sse_event(
                    wfile,
                    "error",
                    {"phase": "test", "message": message},
                )
                return {
                    "status": "error",
                    "exit_code": proc.returncode,
                    "summary": None,
                    "errors": [message],
                    "message": message,
                }

        # Build result
        if proc.returncode == 0 and (not summary or summary.get("failed", 0) == 0):
            test_result = {
                "status": "pass",
                "exit_code": 0,
                "summary": summary,
                "errors": None,
                "message": "All tests passed",
            }
        elif failures or (summary and summary.get("failed", 0) > 0):
            failed_count = summary["failed"] if summary else len(failures)
            errors = []
            for f in failures[:5]:
                test_name = f.get("test_name", "unknown")
                status = f.get("status", "fail")
                message = f.get("message", "")
                if message:
                    errors.append(f"{test_name} [{status}]: {message[:200]}")
                else:
                    errors.append(f"{test_name} [{status}]")

            test_result = {
                "status": "fail",
                "exit_code": proc.returncode,
                "summary": summary,
                "errors": errors if errors else None,
                "message": f"{failed_count} test(s) failed",
            }
        else:
            test_result = {
                "status": "fail",
                "exit_code": proc.returncode,
                "summary": summary,
                "errors": None,
                "message": "Tests failed (unable to parse results)",
            }

        log(f"CDCL streaming test completed: {test_result['status']}")
        return test_result

    except Exception as e:
        log(f"Error running CDCL streaming test: {e}")
        if sel:
            sel.close()
        if proc and proc.poll() is None:
            terminate_process_gracefully(proc)
        return {
            "status": "error",
            "exit_code": -1,
            "summary": None,
            "errors": [str(e)],
            "message": "Execution error",
        }


def handle_proj_submit_streaming(wfile, request_data, cancelled=None):
    """
    Handle proj_submit request with SSE streaming.

    1. Copy project from client_data to server_data
    2. Run build (non-streaming, but emit phase events)
    3. Run tests with streaming
    4. Return final result

    Emits SSE events during execution.
    """
    log("Handling proj_submit request (streaming)")
    request_id = request_data.get("request_id")

    # Get project path from request
    project_name = request_data.get("project_name", "toml")
    src_project = CLIENT_DATA_DIR / project_name
    dst_project = SERVER_DATA_DIR / project_name

    # Validate source exists
    if not src_project.exists():
        log(f"Error: Source project not found at {src_project}")
        send_sse_event(
            wfile,
            "error",
            {"phase": "copy", "message": f"Project not found: {project_name}"},
        )
        send_sse_event(wfile, "done", {"success": False})
        return {"status": "error", "error": f"Project not found: {project_name}"}

    # Emit request_id event
    if request_id:
        send_sse_event(wfile, "request_id", {"request_id": request_id})

    # Emit copy phase start
    send_sse_event(
        wfile,
        "phase",
        {"phase": "copy", "project_name": project_name, "status": "start"},
    )

    # Copy project
    if not copy_project(src_project, dst_project):
        send_sse_event(
            wfile, "error", {"phase": "copy", "message": "Failed to copy project"}
        )
        send_sse_event(wfile, "done", {"success": False})
        return {"status": "error", "error": "Failed to copy project"}

    send_sse_event(
        wfile,
        "phase",
        {"phase": "copy", "project_name": project_name, "status": "pass"},
    )

    # Get optional timeouts from request
    build_timeout = request_data.get("build_timeout", BUILD_TIMEOUT)
    test_timeout = request_data.get("test_timeout", CDCL_TEST_TIMEOUT)
    per_test_timeout = request_data.get("per_test_timeout")
    test_name = request_data.get("test_name")
    test_file = request_data.get("test_file")

    # Detect if project uses try.py runner
    uses_try_py = (dst_project / "try.py").exists()

    # Validate per_test_timeout/test selection is only used with try.py projects
    if (per_test_timeout is not None or test_name or test_file) and not uses_try_py:
        send_sse_event(
            wfile,
            "error",
            {
                "phase": "build",
                "message": (
                    "per_test_timeout/test selection is only supported for projects with try.py"
                ),
            },
        )
        send_sse_event(wfile, "done", {"success": False})
        return {
            "status": "error",
            "error": "per_test_timeout/test selection is only supported for projects with try.py",
        }

    # Emit build phase start
    send_sse_event(
        wfile,
        "phase",
        {"phase": "build", "project_name": project_name, "status": "start"},
    )

    # Run build
    build_result = run_moon_build(dst_project, timeout=build_timeout,
                                  request_id=request_id, cancelled=cancelled)

    if build_result["status"] == "cancelled":
        send_sse_event(wfile, "error", {"phase": "build", "message": "Cancelled"})
        send_sse_event(wfile, "done", {"success": False})
        return {
            "request_id": request_id,
            "project_name": project_name,
            "build_result": build_result,
            "test_result": None,
            "timestamp": datetime.now().isoformat(),
        }

    if build_result["status"] != "pass":
        send_sse_event(
            wfile,
            "phase",
            {"phase": "build", "project_name": project_name, "status": "fail"},
        )
        send_sse_event(
            wfile,
            "error",
            {"phase": "build", "message": build_result.get("message", "Build failed")},
        )
        send_sse_event(wfile, "done", {"success": False})
        return {
            "request_id": request_id,
            "project_name": project_name,
            "build_result": build_result,
            "test_result": None,
            "timestamp": datetime.now().isoformat(),
        }

    send_sse_event(
        wfile,
        "phase",
        {"phase": "build", "project_name": project_name, "status": "pass"},
    )

    # Check cancellation between build and test
    if cancelled is not None and cancelled.is_set():
        send_sse_event(wfile, "error", {"phase": "test", "message": "Cancelled"})
        send_sse_event(wfile, "done", {"success": False})
        return {
            "request_id": request_id,
            "project_name": project_name,
            "build_result": build_result,
            "test_result": {"status": "cancelled", "message": "Cancelled"},
            "timestamp": datetime.now().isoformat(),
        }

    # Emit test phase start
    send_sse_event(
        wfile,
        "phase",
        {"phase": "test", "project_name": project_name, "status": "start"},
    )

    # Run tests with streaming (only for try.py projects for now)
    if uses_try_py:
        test_result = run_cdcl_test_streaming(
            wfile,
            dst_project,
            timeout=test_timeout,
            per_test_timeout=per_test_timeout,
            test_name=test_name,
            test_file=test_file,
            request_id=request_id,
            cancelled=cancelled,
        )
    else:
        # For non-try.py projects, fall back to non-streaming
        test_result = run_moon_test(dst_project, timeout=test_timeout,
                                    request_id=request_id, cancelled=cancelled)
        # Emit summary event for consistency
        if test_result.get("summary"):
            send_sse_event(wfile, "summary", test_result["summary"])
        # Send errors for failed tests
        if test_result.get("errors"):
            for error in test_result["errors"]:
                send_sse_event(wfile, "error_detail", {"message": error})

    # Emit test phase completion
    test_status = "pass" if test_result["status"] == "pass" else "fail"
    send_sse_event(
        wfile,
        "phase",
        {"phase": "test", "project_name": project_name, "status": test_status},
    )

    # Emit done event
    success = build_result["status"] == "pass" and test_result["status"] == "pass"
    send_sse_event(wfile, "done", {"success": success})

    return {
        "request_id": request_id,
        "project_name": project_name,
        "build_result": build_result,
        "test_result": test_result,
        "timestamp": datetime.now().isoformat(),
    }


def handle_proj_submit(request_data, cancelled=None):
    """
    Handle proj_submit request
    1. Copy project from client_data to server_data
    2. Run moon test
    3. Return results
    """
    log("Handling proj_submit request")
    request_id = request_data.get("request_id")

    # Get project path from request
    project_name = request_data.get("project_name", "toml")
    src_project = CLIENT_DATA_DIR / project_name
    dst_project = SERVER_DATA_DIR / project_name

    # Validate source exists
    if not src_project.exists():
        log(f"Error: Source project not found at {src_project}")
        return {"status": "error", "error": f"Project not found: {project_name}"}

    # Copy project
    if not copy_project(src_project, dst_project):
        return {"status": "error", "error": "Failed to copy project"}

    # Get optional timeouts from request (use defaults if not specified)
    build_timeout = request_data.get("build_timeout", BUILD_TIMEOUT)
    test_timeout = request_data.get("test_timeout")  # Falls back to function default
    per_test_timeout = request_data.get("per_test_timeout")  # try.py projects only
    test_name = request_data.get("test_name")
    test_file = request_data.get("test_file")

    # Detect if project uses try.py runner (e.g., CDCL tests)
    uses_try_py = (dst_project / "try.py").exists()

    # Validate per_test_timeout/test selection is only used with try.py projects
    if (per_test_timeout is not None or test_name or test_file) and not uses_try_py:
        return {
            "status": "error",
            "error": "per_test_timeout/test selection is only supported for projects with try.py",
        }

    # Run build first
    build_result = run_moon_build(dst_project, timeout=build_timeout,
                                  request_id=request_id, cancelled=cancelled)

    # If build failed or cancelled, return early
    if build_result["status"] != "pass":
        return {
            "request_id": request_id,
            "project_name": project_name,
            "build_result": build_result,
            "test_result": None,
            "timestamp": datetime.now().isoformat(),
        }

    # Check cancellation between build and test
    if cancelled is not None and cancelled.is_set():
        return {
            "request_id": request_id,
            "project_name": project_name,
            "build_result": build_result,
            "test_result": {"status": "cancelled", "message": "Cancelled"},
            "timestamp": datetime.now().isoformat(),
        }

    # Run tests (use try.py runner if present, otherwise moon test)
    if uses_try_py:
        if test_timeout is not None:
            if per_test_timeout is not None:
                test_result = run_cdcl_test(
                    dst_project,
                    timeout=test_timeout,
                    per_test_timeout=per_test_timeout,
                    test_name=test_name,
                    test_file=test_file,
                    request_id=request_id,
                    cancelled=cancelled,
                )
            else:
                test_result = run_cdcl_test(
                    dst_project,
                    timeout=test_timeout,
                    test_name=test_name,
                    test_file=test_file,
                    request_id=request_id,
                    cancelled=cancelled,
                )
        else:
            test_result = run_cdcl_test(
                dst_project, test_name=test_name, test_file=test_file,
                request_id=request_id, cancelled=cancelled,
            )
    else:
        if test_timeout is not None:
            test_result = run_moon_test(dst_project, timeout=test_timeout,
                                        request_id=request_id, cancelled=cancelled)
        else:
            test_result = run_moon_test(dst_project,
                                        request_id=request_id, cancelled=cancelled)

    return {
        "request_id": request_id,
        "project_name": project_name,
        "build_result": build_result,
        "test_result": test_result,
        "timestamp": datetime.now().isoformat(),
    }


class APIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for REST API"""

    def log_message(self, format, *args):
        """Override to use our log function"""
        pass  # Suppress default HTTP logs

    def _send_json_response(self, status_code, data):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())

    def do_GET(self):
        """Handle GET requests"""
        if self.path == "/health":
            self._send_json_response(
                200, {"status": "healthy", "timestamp": datetime.now().isoformat()}
            )
        elif self.path == "/":
            self._send_json_response(
                200,
                {
                    "service": "MoonBit Test Server",
                    "version": "1.0",
                    "endpoints": {
                        "POST /test": "Submit project for testing",
                        "POST /cancel": "Cancel a running test by request_id",
                        "GET /health": "Health check",
                    },
                },
            )
        else:
            self._send_json_response(404, {"error": "Not found"})

    def _wants_sse(self):
        """Check if client wants SSE streaming"""
        accept = self.headers.get("Accept", "")
        return "text/event-stream" in accept

    def _send_sse_headers(self):
        """Send SSE response headers"""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_POST(self):
        """Handle POST requests"""
        if self.path == "/test":
            request_id = None
            try:
                # Read request body
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                request_data = json.loads(body) if body else {}

                project_name = request_data.get("project_name", "toml")
                request_data["project_name"] = project_name

                # Auto-generate request_id if not provided
                request_id = request_data.get("request_id") or str(uuid.uuid4())
                request_data["request_id"] = request_id

                log(f"Received test request: {project_name} (request_id={request_id})")

                # Try to register as the active request (one-at-a-time per project)
                cancelled, conflict = try_register_request(project_name, request_id)
                if cancelled is None and conflict is not None:
                    active_id = conflict["request_id"]
                    active_project = conflict["project_name"]
                    if conflict.get("reason") == "request_id_busy":
                        error_msg = (
                            f"request_id '{request_id}' is already running for "
                            f"project '{active_project}'. Use a unique request_id."
                        )
                    else:
                        error_msg = (
                            f"A test for project '{project_name}' is already running "
                            f"(request_id: {active_id}). "
                            f"Cancel it first with POST /cancel"
                        )

                    if self._wants_sse():
                        self._send_sse_headers()
                        send_sse_event(
                            self.wfile,
                            "error",
                            {
                                "phase": "request",
                                "message": error_msg,
                                "active_request_id": active_id,
                                "active_project_name": active_project,
                            },
                        )
                        send_sse_event(self.wfile, "done", {"success": False})
                    else:
                        self._send_json_response(
                            409,
                            {
                                "error": error_msg,
                                "active_request_id": active_id,
                                "active_project_name": active_project,
                            },
                        )
                    return

                try:
                    # Check if client wants SSE streaming
                    if self._wants_sse():
                        log("Client requested SSE streaming")
                        self._send_sse_headers()
                        try:
                            handle_proj_submit_streaming(self.wfile, request_data,
                                                        cancelled=cancelled)
                        except (BrokenPipeError, ConnectionResetError):
                            log("Client disconnected during SSE streaming")
                    else:
                        # Legacy JSON response
                        response = handle_proj_submit(request_data, cancelled=cancelled)
                        status_code = 200 if response.get("status") != "error" else 500
                        self._send_json_response(status_code, response)
                finally:
                    unregister_request(request_id)

            except json.JSONDecodeError as e:
                log(f"Invalid JSON: {e}")
                if self._wants_sse():
                    self._send_sse_headers()
                    send_sse_event(
                        self.wfile,
                        "error",
                        {"phase": "request", "message": "Invalid JSON"},
                    )
                    send_sse_event(self.wfile, "done", {"success": False})
                else:
                    self._send_json_response(
                        400, {"status": "error", "error": "Invalid JSON"}
                    )
            except Exception as e:
                log(f"Error processing request: {e}")
                if request_id:
                    unregister_request(request_id)
                if self._wants_sse():
                    try:
                        self._send_sse_headers()
                        send_sse_event(
                            self.wfile, "error", {"phase": "request", "message": str(e)}
                        )
                        send_sse_event(self.wfile, "done", {"success": False})
                    except (BrokenPipeError, ConnectionResetError):
                        pass
                else:
                    self._send_json_response(500, {"status": "error", "error": str(e)})

        elif self.path == "/cancel":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                cancel_data = json.loads(body) if body else {}
                request_id = cancel_data.get("request_id")
                if not request_id:
                    self._send_json_response(400, {"error": "request_id required"})
                    return
                status = cancel_request(request_id)
                log(f"Cancel request for {request_id}: {status}")
                self._send_json_response(200, {"request_id": request_id, "status": status})
            except Exception as e:
                log(f"Error processing cancel request: {e}")
                self._send_json_response(500, {"error": str(e)})

        else:
            self._send_json_response(404, {"error": "Not found"})


def main():
    """Main server - start HTTP server"""
    log("REST API Server starting...")

    # Initialize directories
    init_directories()

    # Create threaded HTTP server (supports concurrent /cancel during /test)
    server = ThreadingHTTPServer((HOST, PORT), APIHandler)
    server.daemon_threads = True

    log(f"Server listening on {HOST}:{PORT}")
    log("Endpoints:")
    log("  GET  / - API info")
    log("  GET  /health - Health check")
    log("  POST /test - Submit project for testing")
    log("  POST /cancel - Cancel a running test")
    log("")
    log("Server ready!")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("Server shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
