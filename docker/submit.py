#!/usr/bin/env python3
"""
Python client for submitting test requests to the MoonBit test server.
Supports SSE streaming for real-time test result display.
"""

import argparse
import json
import sys
import uuid
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


# ANSI color codes (optional, for terminal output)
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def supports_color():
    """Check if terminal supports color output."""
    if not hasattr(sys.stdout, "isatty"):
        return False
    if not sys.stdout.isatty():
        return False
    return True


USE_COLOR = supports_color()


def colorize(text: str, color: str) -> str:
    """Apply color to text if supported."""
    if USE_COLOR:
        return f"{color}{text}{Colors.RESET}"
    return text


def status_symbol(status: str) -> str:
    """Get display symbol for test status."""
    if status == "pass":
        return colorize("PASS", Colors.GREEN)
    elif status == "fail":
        return colorize("FAIL", Colors.RED)
    elif status == "timeout":
        return colorize("TIMEOUT", Colors.YELLOW)
    elif status == "oom":
        return colorize("OOM", Colors.YELLOW)
    else:
        return colorize(status.upper(), Colors.YELLOW)


def parse_sse_events(response):
    """
    Parse SSE events from response stream.

    Yields tuples of (event_type, data_dict).
    """
    event_type = None
    data_lines = []

    for line_bytes in response:
        line = line_bytes.decode("utf-8").rstrip("\r\n")

        if line.startswith(":"):
            # Comment (keep-alive), ignore
            continue
        elif line.startswith("event:"):
            event_type = line[6:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].strip())
        elif line == "":
            # End of event
            if data_lines:
                try:
                    data = json.loads("\n".join(data_lines))
                    yield (event_type, data)
                except json.JSONDecodeError:
                    pass
            event_type = None
            data_lines = []


def handle_event(event_type: str, data: dict, verbose: bool = False) -> bool:
    """
    Handle a single SSE event.

    Returns True to continue processing, False to stop.
    """
    if event_type == "phase":
        phase = data.get("phase", "unknown")
        status = data.get("status", "unknown")

        if status == "start":
            phase_name = phase.capitalize()
            print(f"{colorize('>>>', Colors.BLUE)} {phase_name} phase started", flush=True)
        elif status == "pass":
            print(f"{colorize('>>>', Colors.BLUE)} {phase.capitalize()} phase completed", flush=True)
        elif status == "fail":
            print(f"{colorize('>>>', Colors.RED)} {phase.capitalize()} phase failed", flush=True)

    elif event_type == "test_result":
        test_name = data.get("test_name", "unknown")
        status = data.get("status", "unknown")
        index = data.get("index", "?")
        total = data.get("total", "?")
        message = data.get("message", "")

        symbol = status_symbol(status)
        line = f"[{index}/{total}] {symbol}: {test_name}"
        print(line, flush=True)

        # Show failure message (always for failures, verbose for all)
        if message and (status != "pass" or verbose):
            # Indent multi-line messages for readability
            for msg_line in message.splitlines():
                print(f"    {msg_line}", flush=True)

    elif event_type == "summary":
        total = data.get("total", 0)
        passed = data.get("passed", 0)
        failed = data.get("failed", 0)

        print(flush=True)
        print(f"{colorize('Summary:', Colors.BOLD)}", flush=True)
        print(f"  Total:  {total}", flush=True)
        print(f"  Passed: {colorize(str(passed), Colors.GREEN)}", flush=True)
        if failed > 0:
            print(f"  Failed: {colorize(str(failed), Colors.RED)}", flush=True)
        else:
            print(f"  Failed: {failed}", flush=True)

    elif event_type == "error":
        phase = data.get("phase", "unknown")
        message = data.get("message", "Unknown error")
        print(
            f"{colorize('ERROR', Colors.RED)} [{phase}]: {message}",
            file=sys.stderr,
            flush=True,
        )

    elif event_type == "error_detail":
        message = data.get("message", "")
        if message:
            print(flush=True)
            print(f"{colorize('Failed test:', Colors.RED)}", flush=True)
            for line in message.splitlines():
                print(f"  {line}", flush=True)

    elif event_type == "request_id":
        # Informational; logged in verbose mode
        if verbose:
            print(f"Request ID: {data.get('request_id', 'unknown')}", flush=True)

    elif event_type == "done":
        success = data.get("success", False)
        if success:
            print(f"\n{colorize('All tests passed!', Colors.GREEN)}", flush=True)
        else:
            print(f"\n{colorize('Tests completed with failures.', Colors.RED)}", flush=True)
        return False  # Stop processing

    return True


def send_cancel(server_url, request_id):
    """Best-effort cancel request."""
    url = f"{server_url.rstrip('/')}/cancel"
    req = Request(url, data=json.dumps({"request_id": request_id}).encode(),
                  headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read().decode())
            print(f"Cancel: {result.get('status', 'unknown')}", file=sys.stderr)
    except Exception:
        pass  # Best effort


def stream_test_results(server_url: str, payload: dict, verbose: bool = False) -> int:
    """
    Stream test results via SSE.

    Returns exit code: 0 for success, 1 for test failures, 2 for errors.
    """
    url = f"{server_url.rstrip('/')}/test"

    # Prepare request
    data = json.dumps(payload).encode("utf-8")
    req = Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=600) as response:
            success = True
            for event_type, data in parse_sse_events(response):
                if event_type is None:
                    continue
                if event_type == "done":
                    success = data.get("success", False)
                    handle_event(event_type, data, verbose)
                    break
                elif not handle_event(event_type, data, verbose):
                    break

            return 0 if success else 1

    except HTTPError as e:
        if e.code == 409:
            try:
                error_body = json.loads(e.read().decode("utf-8"))
                active_id = error_body.get("active_request_id", "unknown")
                active_project = error_body.get("active_project_name")
                if active_project:
                    print(
                        f"A test is already running for project '{active_project}' "
                        f"(request_id: {active_id}).",
                        file=sys.stderr,
                    )
                else:
                    print(
                        f"A test is already running (request_id: {active_id}).",
                        file=sys.stderr,
                    )
                print(f"Cancel it first: POST /cancel with request_id={active_id}", file=sys.stderr)
            except (json.JSONDecodeError, UnicodeDecodeError):
                print("A test is already running. Cancel it first.", file=sys.stderr)
            return 2
        print(f"HTTP Error: {e.code} {e.reason}", file=sys.stderr)
        try:
            error_body = e.read().decode("utf-8")
            error_data = json.loads(error_body)
            print(f"Error: {error_data.get('error', error_body)}", file=sys.stderr)
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
        return 2

    except URLError as e:
        print(f"Connection Error: {e.reason}", file=sys.stderr)
        return 2

    except TimeoutError:
        print("Request timed out", file=sys.stderr)
        return 2

    except KeyboardInterrupt:
        print("\nInterrupted by user, cancelling...", file=sys.stderr)
        send_cancel(server_url, payload.get("request_id", ""))
        return 130


def main():
    parser = argparse.ArgumentParser(
        description="Submit test requests to MoonBit test server with SSE streaming"
    )
    parser.add_argument(
        "--project",
        help="Project name (required for test submission)",
    )
    parser.add_argument(
        "--request-id",
        help="Request ID for tracking",
    )
    parser.add_argument(
        "--cancel",
        metavar="REQUEST_ID",
        help="Cancel a running test by request_id",
    )
    parser.add_argument(
        "--server",
        default="http://server:8080",
        help="Server URL (default: http://server:8080)",
    )
    parser.add_argument(
        "--build-timeout",
        type=int,
        help="Build timeout in seconds",
    )
    parser.add_argument(
        "--test-timeout",
        type=int,
        help="Overall test timeout in seconds",
    )
    parser.add_argument(
        "--per-test-timeout",
        type=int,
        help="Per-test timeout in seconds (try.py projects only)",
    )
    parser.add_argument(
        "--test-name",
        help="Run a specific test by name (try.py projects only)",
    )
    parser.add_argument(
        "--test-file",
        help="Run tests from a specific file (try.py projects only)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show verbose output including error messages",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable color output",
    )

    args = parser.parse_args()

    # Disable color if requested
    global USE_COLOR
    if args.no_color:
        USE_COLOR = False

    # Handle --cancel mode
    if args.cancel:
        send_cancel(args.server, args.cancel)
        sys.exit(0)

    # --project is required for test submission
    if not args.project:
        parser.error("--project is required (unless using --cancel)")

    # Build request payload
    payload = {
        "project_name": args.project,
    }
    if args.request_id:
        payload["request_id"] = args.request_id
    else:
        payload["request_id"] = str(uuid.uuid4())
    if args.build_timeout:
        payload["build_timeout"] = args.build_timeout
    if args.test_timeout:
        payload["test_timeout"] = args.test_timeout
    if args.per_test_timeout:
        payload["per_test_timeout"] = args.per_test_timeout
    if args.test_name:
        payload["test_name"] = args.test_name
    if args.test_file:
        payload["test_file"] = args.test_file

    print(f"Submitting test request for project: {colorize(args.project, Colors.BOLD)}")
    print(f"Server: {args.server}")
    print(flush=True)

    exit_code = stream_test_results(args.server, payload, args.verbose)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
