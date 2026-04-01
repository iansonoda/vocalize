import argparse
import json
import os
from pathlib import Path
from statistics import mean


DEFAULT_PYTHON_LOG = Path(".tmp/telemetry.jsonl")
DEFAULT_ELECTRON_LOG = Path(".tmp/electron_telemetry.jsonl")


PYTHON_METRICS = [
    "recording_duration_ms",
    "first_partial_latency_ms",
    "temp_file_write_ms",
    "transcription_roundtrip_ms",
    "cleanup_roundtrip_ms",
    "insertion_latency_ms",
    "database_save_ms",
    "total_end_to_end_ms",
]

ELECTRON_METRICS = [
    "first_partial_ui_ms",
    "end_to_end_to_final_ui_ms",
    "end_to_end_to_stats_ui_ms",
]


def read_jsonl(path):
    if not path.exists():
        return []

    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def load_session_rows(path, record_type, include_smoke=False):
    rows = []
    for row in read_jsonl(path):
        if row.get("type") != record_type:
            continue
        if not include_smoke and row.get("session_id") == "smoke-session":
            continue
        rows.append(row)

    rows.sort(key=lambda row: row.get("unix_ms", 0))
    return rows


def ms_to_seconds(value):
    if value is None:
        return "-"
    return f"{value / 1000:.2f}s"


def summarize_metric(rows, metric_name):
    values = [row.get("metrics", {}).get(metric_name) for row in rows]
    values = [value for value in values if isinstance(value, (int, float))]
    if not values:
        return None

    return {
        "avg": mean(values),
        "min": min(values),
        "max": max(values),
    }


def build_session_index(python_rows, electron_rows):
    sessions = {}

    for row in python_rows:
        sessions.setdefault(row["session_id"], {})["python"] = row

    for row in electron_rows:
        sessions.setdefault(row["session_id"], {})["electron"] = row

    ordered = sorted(
        sessions.items(),
        key=lambda item: max(
            item[1].get("python", {}).get("unix_ms", 0),
            item[1].get("electron", {}).get("unix_ms", 0),
        ),
    )
    return ordered


def print_latest_sessions(session_rows, latest_count):
    selected = session_rows[-latest_count:] if latest_count else session_rows
    if not selected:
        print("No session summaries found.")
        return

    print("Latest Sessions")
    for session_id, rows in selected:
        python_row = rows.get("python", {})
        electron_row = rows.get("electron", {})
        metrics = python_row.get("metrics", {})
        ui_metrics = electron_row.get("metrics", {})
        short_id = session_id[:8]
        outcome = python_row.get("outcome", "unknown")
        print(
            f"- {short_id} outcome={outcome} "
            f"record={ms_to_seconds(metrics.get('recording_duration_ms'))} "
            f"first_partial={ms_to_seconds(metrics.get('first_partial_latency_ms'))} "
            f"transcribe={ms_to_seconds(metrics.get('transcription_roundtrip_ms'))} "
            f"cleanup={ms_to_seconds(metrics.get('cleanup_roundtrip_ms'))} "
            f"insert={ms_to_seconds(metrics.get('insertion_latency_ms'))} "
            f"total={ms_to_seconds(metrics.get('total_end_to_end_ms'))} "
            f"final_ui={ms_to_seconds(ui_metrics.get('end_to_end_to_final_ui_ms'))}"
        )


def print_metric_block(title, rows, metric_names):
    print(title)
    found_any = False
    for metric_name in metric_names:
        stats = summarize_metric(rows, metric_name)
        if not stats:
            continue
        found_any = True
        print(
            f"- {metric_name}: "
            f"avg={ms_to_seconds(stats['avg'])} "
            f"min={ms_to_seconds(stats['min'])} "
            f"max={ms_to_seconds(stats['max'])}"
        )

    if not found_any:
        print("- No data")


def main():
    parser = argparse.ArgumentParser(
        description="Summarize dictation telemetry from Python and Electron JSONL logs.",
    )
    parser.add_argument(
        "--python-log",
        default=str(DEFAULT_PYTHON_LOG),
        help=f"Path to the Python telemetry log. Default: {DEFAULT_PYTHON_LOG}",
    )
    parser.add_argument(
        "--electron-log",
        default=str(DEFAULT_ELECTRON_LOG),
        help=f"Path to the Electron telemetry log. Default: {DEFAULT_ELECTRON_LOG}",
    )
    parser.add_argument(
        "--latest",
        type=int,
        default=5,
        help="How many recent sessions to print in detail. Default: 5",
    )
    parser.add_argument(
        "--include-smoke",
        action="store_true",
        help="Include the synthetic smoke-session in the report.",
    )
    args = parser.parse_args()

    python_path = Path(args.python_log)
    electron_path = Path(args.electron_log)

    python_rows = load_session_rows(
        python_path,
        "benchmark_summary",
        include_smoke=args.include_smoke,
    )
    electron_rows = load_session_rows(
        electron_path,
        "electron_benchmark_summary",
        include_smoke=args.include_smoke,
    )
    sessions = build_session_index(python_rows, electron_rows)

    print(f"Python log: {python_path.resolve()}")
    print(f"Electron log: {electron_path.resolve()}")
    print(f"Sessions with Python summaries: {len(python_rows)}")
    print(f"Sessions with Electron summaries: {len(electron_rows)}")
    print("")

    print_latest_sessions(sessions, args.latest)
    print("")
    print_metric_block("Python Averages", python_rows, PYTHON_METRICS)
    print("")
    print_metric_block("Electron Averages", electron_rows, ELECTRON_METRICS)


if __name__ == "__main__":
    main()
