import os
import threading
import time

from tools.transcriber import transcribe_audio


class StreamingTranscriptionSession:
    def __init__(
        self,
        recorder,
        session_id,
        emit_event,
        telemetry=None,
        poll_interval_seconds=0.35,
        min_audio_seconds=1.6,
        partial_interval_seconds=1.8,
    ):
        self.recorder = recorder
        self.session_id = session_id
        self.emit_event = emit_event
        self.telemetry = telemetry
        self.poll_interval_seconds = poll_interval_seconds
        self.min_audio_seconds = min_audio_seconds
        self.partial_interval_seconds = partial_interval_seconds
        self.stop_event = threading.Event()
        self.thread = None
        self.last_requested_duration = 0.0
        self.last_emitted_text = ""
        self.partial_count = 0
        self.error_count = 0

    def start(self):
        if self.thread and self.thread.is_alive():
            return

        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()

    def join(self, timeout=None):
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=timeout)

    def get_stats(self):
        return {
            "partial_count": self.partial_count,
            "partial_error_count": self.error_count,
        }

    def _run(self):
        while not self.stop_event.is_set():
            duration_seconds = self.recorder.get_recording_duration_seconds()
            if duration_seconds < self.min_audio_seconds:
                time.sleep(self.poll_interval_seconds)
                continue

            if (
                duration_seconds - self.last_requested_duration
                < self.partial_interval_seconds
            ):
                time.sleep(self.poll_interval_seconds)
                continue

            snapshot_path, snapshot_duration = self.recorder.write_snapshot_file(
                prefix="partial",
                session_id=self.session_id,
            )
            if not snapshot_path or snapshot_duration < self.min_audio_seconds:
                time.sleep(self.poll_interval_seconds)
                continue

            self.last_requested_duration = snapshot_duration
            partial_index = self.partial_count + 1

            try:
                text = transcribe_audio(
                    snapshot_path,
                    telemetry=self.telemetry,
                    event_prefix="partial_transcription_request",
                    request_kind="partial",
                    request_metadata={
                        "partial_index": partial_index,
                        "snapshot_duration_seconds": round(snapshot_duration, 2),
                    },
                )
                if self.stop_event.is_set():
                    break

                if text is None:
                    self.error_count += 1
                    self.emit_event(
                        "error",
                        session_id=self.session_id,
                        phase="partial",
                        message="Partial transcription request returned no text.",
                    )
                    time.sleep(self.poll_interval_seconds)
                    continue

                normalized_text = (text or "").strip()
                if not normalized_text or normalized_text == self.last_emitted_text:
                    time.sleep(self.poll_interval_seconds)
                    continue

                self.last_emitted_text = normalized_text
                self.partial_count += 1

                if self.telemetry and self.partial_count == 1:
                    self.telemetry.mark(
                        "first_partial_emitted",
                        partial_index=self.partial_count,
                        transcript_chars=len(normalized_text),
                    )

                self.emit_event(
                    "partial",
                    session_id=self.session_id,
                    text=normalized_text,
                    partial_index=self.partial_count,
                    duration_seconds=round(snapshot_duration, 2),
                )

            except Exception as exc:
                self.error_count += 1
                self.emit_event(
                    "error",
                    session_id=self.session_id,
                    phase="partial",
                    message=str(exc),
                )
            finally:
                try:
                    os.remove(snapshot_path)
                except Exception:
                    pass

            time.sleep(self.poll_interval_seconds)
