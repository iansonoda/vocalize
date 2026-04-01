import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone


_FILE_LOCK = threading.Lock()


def _iso_timestamp(unix_seconds):
    return datetime.fromtimestamp(unix_seconds, tz=timezone.utc).isoformat()


def append_jsonl(file_path, payload):
    directory = os.path.dirname(file_path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    line = json.dumps(payload, sort_keys=True)
    with _FILE_LOCK:
        with open(file_path, "a", encoding="utf-8") as log_file:
            log_file.write(line + "\n")


class SessionTelemetry:
    def __init__(self, session_id=None, log_path=None):
        self.session_id = session_id or uuid.uuid4().hex
        self.log_path = log_path or os.path.join(os.getcwd(), ".tmp", "telemetry.jsonl")
        self._events = {}
        self._lock = threading.Lock()

    def mark(self, event, **data):
        unix_seconds = time.time()
        perf_ns = time.perf_counter_ns()
        payload = {
            "type": "timing_event",
            "source": "python",
            "session_id": self.session_id,
            "event": event,
            "timestamp": _iso_timestamp(unix_seconds),
            "unix_ms": int(unix_seconds * 1000),
            "perf_ns": perf_ns,
            **data,
        }

        with self._lock:
            self._events[event] = perf_ns

        append_jsonl(self.log_path, payload)
        print(f"TIMING:{json.dumps(payload, sort_keys=True)}", flush=True)
        return payload

    def _duration_ms(self, start_event, end_event):
        with self._lock:
            start_ns = self._events.get(start_event)
            end_ns = self._events.get(end_event)

        if start_ns is None or end_ns is None or end_ns < start_ns:
            return None

        return round((end_ns - start_ns) / 1_000_000, 2)

    def emit_summary(self, **data):
        unix_seconds = time.time()
        metrics = {
            "recording_duration_ms": self._duration_ms("record_start", "record_stop"),
            "first_partial_latency_ms": self._duration_ms("record_start", "first_partial_emitted"),
            "temp_file_write_ms": self._duration_ms("record_stop", "temp_file_write_complete"),
            "audio_capture_to_transcript_ms": self._duration_ms("record_stop", "transcription_request_end"),
            "transcription_roundtrip_ms": self._duration_ms("transcription_request_start", "transcription_request_end"),
            "transcript_to_cleaned_ms": self._duration_ms("transcription_request_end", "cleanup_end"),
            "cleanup_roundtrip_ms": self._duration_ms("cleanup_start", "cleanup_end"),
            "cleaned_output_to_insertion_ms": self._duration_ms("cleanup_end", "insertion_result"),
            "insertion_latency_ms": self._duration_ms("insertion_attempt_start", "insertion_result"),
            "database_save_ms": self._duration_ms("database_save_start", "database_save_end"),
            "total_end_to_end_ms": self._duration_ms("record_start", "database_save_end"),
        }
        metrics = {key: value for key, value in metrics.items() if value is not None}

        payload = {
            "type": "benchmark_summary",
            "source": "python",
            "session_id": self.session_id,
            "timestamp": _iso_timestamp(unix_seconds),
            "unix_ms": int(unix_seconds * 1000),
            "metrics": metrics,
            **data,
        }

        append_jsonl(self.log_path, payload)
        print(f"BENCHMARK:{json.dumps(payload, sort_keys=True)}", flush=True)
        return payload
