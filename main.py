from tools.recorder import AudioRecorder
from tools.transcriber import transcribe_audio
from tools.cleaner import clean_text
from tools.paster import paste_text
from tools.db import save_transcription, get_stats
from tools.telemetry import SessionTelemetry
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
            print(f"DEBUG: Could not hide dock icon: {e}", flush=True)

class AppController:
    def __init__(self):
        self.recorder = AudioRecorder()
        self.settings = {"mode": "plain", "tone": "natural"}
        self.recording_start_time = 0
        self.current_session = None
        print(f"👂 Listening for {TOGGLE_KEY} press...")

    def update_settings(self, settings_json):
        try:
            new_settings = json.loads(settings_json)
            self.settings.update(new_settings)
            print(f"DEBUG: Updated settings to {self.settings}", flush=True)
        except Exception as e:
            print(f"DEBUG: Failed to parse settings: {e}", flush=True)

    def on_press(self, key):
        if key == TOGGLE_KEY:
            if not self.recorder.is_recording:
                # Start recording
                self.current_session = SessionTelemetry()
                self.current_session.mark(
                    "record_start",
                    mode=self.settings.get("mode", "plain"),
                    tone=self.settings.get("tone", "natural"),
                    trigger_key=str(TOGGLE_KEY),
                )
                print("\n--- 🟢 Recording Started ---", flush=True)
                self.recording_start_time = time.time()
                self.recorder.start_recording()
            else:
                # Stop recording
                print("\n--- 🔴 Recording Stopped ---", flush=True)
                duration = time.time() - self.recording_start_time
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
                    self.current_session.mark("session_aborted", reason="no_audio_file")
                    self.current_session.emit_summary(outcome="no_audio_file")
                    self.current_session = None

    def on_release(self, key):
        # Stop listener if Escape is pressed (optional safety hatch)
        # if key == keyboard.Key.esc:
        #     return False
        pass

    def process_audio(self, audio_file, duration, session=None):
        """Transcribe, clean, output the result, and log to DB."""
        telemetry = session or SessionTelemetry()
        print("STATUS: loading", flush=True)

        try:
            raw_text = transcribe_audio(audio_file, telemetry=telemetry)
            if raw_text:
                # Clean text via AI formatting layer
                mode = self.settings.get("mode", "plain")
                tone = self.settings.get("tone", "natural")
                
                # Combine tone into cleaner logic if needed, or just pass it
                formatted_text = clean_text(raw_text, mode=mode, tone=tone, telemetry=telemetry)
                
                # Fallback if cleaner failed or returned empty
                if not formatted_text:
                    telemetry.mark("cleanup_fallback", reason="empty_cleaned_text")
                    formatted_text = raw_text

                # Paste into active window
                paste_success = paste_text(formatted_text + " ", telemetry=telemetry)
                
                # Emit for Electron
                payload = json.dumps({
                    "raw": raw_text,
                    "formatted": formatted_text,
                    "mode": mode,
                    "duration": duration,
                    "session_id": telemetry.session_id,
                })
                print(f"FINAL:{payload}", flush=True)
                telemetry.mark("final_event_emitted", event_name="FINAL")
                
                # Save the record in the database
                save_transcription(
                    raw_text,
                    formatted_text,
                    mode=mode,
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
                )
            else:
                telemetry.mark("session_aborted", reason="empty_transcription")
                telemetry.emit_summary(outcome="empty_transcription")
        finally:
            self.current_session = None

            # Optional: delete temporary audio file after processing to save disk space
            try:
                os.remove(audio_file)
            except Exception:
                pass

    def emit_stats(self, session_id=None):
        """Fetch stats from DB and print for Electron."""
        stats = get_stats()
        if session_id:
            stats["session_id"] = session_id
        print(f"STATS:{json.dumps(stats)}", flush=True)

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
