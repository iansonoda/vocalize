from tools.recorder import AudioRecorder
from tools.transcriber import transcribe_audio
from tools.cleaner import clean_text, normalize_mode
from tools.paster import paste_text
from tools.db import save_transcription, get_stats
from tools.telemetry import SessionTelemetry
from tools.streaming_transcriber import StreamingTranscriptionSession
from tools.output import emit_stdout
import time
import os

import json
import sys
from pynput import keyboard

# We'll use F8 or another key for the global toggle
# F8 is usually a safe choice on a Mac
TOGGLE_KEY = keyboard.Key.alt_r 

def hide_dock_icon():
    if sys.platform == "darwin":
        try:
            import AppKit
            # NSApplicationActivationPolicyProhibited = 2
            # This hides the dock icon for the Python process
            AppKit.NSApplication.sharedApplication().setActivationPolicy_(2)
        except Exception as e:
            emit_stdout(f"DEBUG: Could not hide dock icon: {e}")

class AppController:
    def __init__(self):
        self.recorder = AudioRecorder()
        self.settings = {"mode": "plain", "tone": "natural"}
        self.recording_start_time = 0
        self.current_session = None
        self.streaming_session = None
        emit_stdout(f"👂 Listening for {TOGGLE_KEY} press...")

    def update_settings(self, settings_json):
        try:
            new_settings = json.loads(settings_json)
            if "mode" in new_settings:
                new_settings["mode"] = normalize_mode(new_settings["mode"])
            self.settings.update(new_settings)
            emit_stdout(f"DEBUG: Updated settings to {self.settings}")
        except Exception as e:
            emit_stdout(f"DEBUG: Failed to parse settings: {e}")

    def on_press(self, key):
        if key == TOGGLE_KEY:
            if not self.recorder.is_recording:
                # Start recording
                self.current_session = SessionTelemetry()
                selected_mode = normalize_mode(self.settings.get("mode", "plain"))
                self.current_session.mark(
                    "record_start",
                    mode=selected_mode,
                    tone=self.settings.get("tone", "natural"),
                    trigger_key=str(TOGGLE_KEY),
                )
                emit_stdout("\n--- 🟢 Recording Started ---")
                self.recording_start_time = time.time()
                self.recorder.start_recording()
                self.streaming_session = StreamingTranscriptionSession(
                    recorder=self.recorder,
                    session_id=self.current_session.session_id,
                    emit_event=self.emit_transcript_event,
                    telemetry=self.current_session,
                )
                self.streaming_session.start()
            else:
                # Stop recording
                emit_stdout("\n--- 🔴 Recording Stopped ---")
                duration = time.time() - self.recording_start_time
                if self.streaming_session:
                    self.streaming_session.stop()
                if self.current_session:
                    self.current_session.mark(
                        "record_stop",
                        duration_ms=round(duration * 1000, 2),
                    )
                audio_file = self.recorder.stop_recording(telemetry=self.current_session)
                
                if audio_file:
                    # Pass the audio to the transcription and then paste it
                    self.process_audio(audio_file, duration, session=self.current_session)
                elif self.current_session:
                    self.emit_transcript_event(
                        "error",
                        session_id=self.current_session.session_id,
                        phase="recording",
                        message="No audio file was created for this session.",
                    )
                    self.emit_transcript_event(
                        "session-complete",
                        session_id=self.current_session.session_id,
                        outcome="no_audio_file",
                    )
                    self.current_session.mark("session_aborted", reason="no_audio_file")
                    self.current_session.emit_summary(outcome="no_audio_file")
                    self.current_session = None
                    self.streaming_session = None

    def on_release(self, key):
        # Stop listener if Escape is pressed (optional safety hatch)
        # if key == keyboard.Key.esc:
        #     return False
        pass

    def process_audio(self, audio_file, duration, session=None):
        """Transcribe, clean, output the result, and log to DB."""
        telemetry = session or SessionTelemetry()
        streaming_stats = (
            self.streaming_session.get_stats() if self.streaming_session else {}
        )
        emit_stdout("STATUS: loading")

        try:
            raw_text = transcribe_audio(audio_file, telemetry=telemetry)
            if raw_text:
                self.emit_transcript_event(
                    "final",
                    session_id=telemetry.session_id,
                    text=raw_text,
                    phase="final_batch",
                )
                # Clean text via AI formatting layer
                mode = normalize_mode(self.settings.get("mode", "plain"))
                tone = self.settings.get("tone", "natural")
                
                # Combine tone into cleaner logic if needed, or just pass it
                cleanup_result = clean_text(
                    raw_text,
                    mode=mode,
                    tone=tone,
                    telemetry=telemetry,
                    return_metadata=True,
                )
                formatted_text = cleanup_result["text"]
                cleanup_status = cleanup_result["status"]
                cleanup_source = cleanup_result["output_source"]
                cleanup_fallback_reason = cleanup_result["fallback_reason"]
                resolved_mode = cleanup_result["resolved_mode"]
                
                # Fallback if cleaner failed or returned empty
                if not formatted_text:
                    telemetry.mark("cleanup_fallback", reason="empty_cleaned_text")
                    formatted_text = raw_text
                    cleanup_status = "fallback_to_raw"
                    cleanup_source = "raw_fallback"
                    cleanup_fallback_reason = "empty_cleaned_text"
                    resolved_mode = mode

                # Paste into active window
                paste_success = paste_text(formatted_text + " ", telemetry=telemetry)
                
                # Emit for Electron
                payload = json.dumps({
                    "raw": raw_text,
                    "formatted": formatted_text,
                    "mode": resolved_mode,
                    "duration": duration,
                    "session_id": telemetry.session_id,
                    "cleanup_status": cleanup_status,
                    "cleanup_source": cleanup_source,
                    "cleanup_fallback_reason": cleanup_fallback_reason,
                })
                emit_stdout(f"FINAL:{payload}")
                telemetry.mark("final_event_emitted", event_name="FINAL")
                
                # Save the record in the database
                save_transcription(
                    raw_text,
                    formatted_text,
                    mode=resolved_mode,
                    duration=duration,
                    telemetry=telemetry,
                )
                
                # Emit updated stats
                self.emit_stats(session_id=telemetry.session_id)
                telemetry.emit_summary(
                    outcome="success",
                    insertion_success=paste_success,
                    raw_chars=len(raw_text),
                    formatted_chars=len(formatted_text),
                    partial_count=streaming_stats.get("partial_count", 0),
                    partial_error_count=streaming_stats.get("partial_error_count", 0),
                )
                self.emit_transcript_event(
                    "session-complete",
                    session_id=telemetry.session_id,
                    outcome="success",
                    partial_count=streaming_stats.get("partial_count", 0),
                )
            else:
                self.emit_transcript_event(
                    "error",
                    session_id=telemetry.session_id,
                    phase="final_batch",
                    message="Final transcription did not return text.",
                )
                telemetry.mark("session_aborted", reason="empty_transcription")
                telemetry.emit_summary(
                    outcome="empty_transcription",
                    partial_count=streaming_stats.get("partial_count", 0),
                    partial_error_count=streaming_stats.get("partial_error_count", 0),
                )
                self.emit_transcript_event(
                    "session-complete",
                    session_id=telemetry.session_id,
                    outcome="empty_transcription",
                    partial_count=streaming_stats.get("partial_count", 0),
                )
        finally:
            self.current_session = None
            if self.streaming_session:
                self.streaming_session.join(timeout=0.1)
            self.streaming_session = None

            # Optional: delete temporary audio file after processing to save disk space
            try:
                os.remove(audio_file)
            except Exception:
                pass

    def emit_transcript_event(self, event_type, session_id, **data):
        payload = {
            "event": event_type,
            "session_id": session_id,
            **data,
        }
        emit_stdout(f"TRANSCRIPT_EVENT:{json.dumps(payload)}")

    def emit_stats(self, session_id=None):
        """Fetch stats from DB and print for Electron."""
        stats = get_stats()
        if session_id:
            stats["session_id"] = session_id
        emit_stdout(f"STATS:{json.dumps(stats)}")

    def run(self):
        # We need to re-import keyboard specifically inside run scope or at module level properly
        from pynput import keyboard
        
        # Start command listener for settings from Electron
        import threading
        def input_thread():
            while True:
                line = sys.stdin.readline()
                if not line:
                    break
                if line.startswith("SETTINGS:"):
                    self.update_settings(line[9:].strip())
                elif line.startswith("GET_STATS"):
                    self.emit_stats()
        
        t = threading.Thread(target=input_thread, daemon=True)
        t.start()
        
        # Initial stats emission
        self.emit_stats()

        # Collect events until interrupted
        with keyboard.Listener(
                on_press=self.on_press,
                on_release=self.on_release) as listener:
            listener.join()

if __name__ == "__main__":
    hide_dock_icon()
    app_controller = AppController()
    app_controller.run()
