from tools.recorder import AudioRecorder
from tools.transcriber import transcribe_audio
from tools.cleaner import clean_text
from tools.paster import paste_text
from tools.db import save_transcription
import time
import os

import json
import sys
from pynput import keyboard

# We'll use F8 or another key for the global toggle
# F8 is usually a safe choice on a Mac
TOGGLE_KEY = keyboard.Key.alt_r 

class AppController:
    def __init__(self):
        self.recorder = AudioRecorder()
        self.settings = {"mode": "plain", "tone": "natural"}
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
                print("\n--- 🟢 Recording Started ---", flush=True)
                self.recorder.start_recording()
            else:
                # Stop recording
                print("\n--- 🔴 Recording Stopped ---", flush=True)
                audio_file = self.recorder.stop_recording()
                
                if audio_file:
                    # Pass the audio to the transcription and then paste it
                    self.process_audio(audio_file)

    def on_release(self, key):
        # Stop listener if Escape is pressed (optional safety hatch)
        # if key == keyboard.Key.esc:
        #     return False
        pass

    def process_audio(self, audio_file):
        """Transcribe, clean, output the result, and log to DB."""
        raw_text = transcribe_audio(audio_file)
        if raw_text:
            # Clean text via AI formatting layer
            mode = self.settings.get("mode", "plain")
            tone = self.settings.get("tone", "natural")
            
            # Combine tone into cleaner logic if needed, or just pass it
            formatted_text = clean_text(raw_text, mode=mode, tone=tone)
            
            # Fallback if cleaner failed or returned empty
            if not formatted_text:
                formatted_text = raw_text

            # Paste into active window
            paste_text(formatted_text + " ")
            
            # Emit for Electron
            payload = json.dumps({
                "raw": raw_text,
                "formatted": formatted_text,
                "mode": mode
            })
            print(f"FINAL:{payload}", flush=True)
            
            # Save the record in the database
            save_transcription(raw_text, formatted_text, mode=mode)
            
        # Optional: delete temporary audio file after processing to save disk space
        try:
             os.remove(audio_file)
        except Exception:
             pass

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
        
        t = threading.Thread(target=input_thread, daemon=True)
        t.start()

        # Collect events until interrupted
        with keyboard.Listener(
                on_press=self.on_press,
                on_release=self.on_release) as listener:
            listener.join()

if __name__ == "__main__":
    app_controller = AppController()
    app_controller.run()
