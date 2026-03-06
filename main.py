from tools.recorder import AudioRecorder
from tools.transcriber import transcribe_audio
from tools.cleaner import clean_text
from tools.paster import paste_text
from tools.db import save_transcription
import time
import os

from pynput import keyboard

# We'll use F8 or another key for the global toggle
# F8 is usually a safe choice on a Mac
TOGGLE_KEY = keyboard.Key.f8 

class AppController:
    def __init__(self):
        self.recorder = AudioRecorder()
        print(f"👂 Listening for {TOGGLE_KEY} press...")

    def on_press(self, key):
        if key == TOGGLE_KEY:
            if not self.recorder.is_recording:
                # Start recording
                print("\n--- 🟢 Recording Started ---")
                self.recorder.start_recording()
            else:
                # Stop recording
                print("\n--- 🔴 Recording Stopped ---")
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
            formatted_text = clean_text(raw_text, mode="plain")
            
            # Fallback if cleaner failed or returned empty
            if not formatted_text:
                formatted_text = raw_text

            # Paste into active window
            paste_text(formatted_text + " ")
            print(f"✨ Done: '{formatted_text}'")
            
            # Save the record in the database
            save_transcription(raw_text, formatted_text, mode="plain")
            
        # Optional: delete temporary audio file after processing to save disk space
        try:
             os.remove(audio_file)
        except Exception:
             pass

    def run(self):
        # We need to re-import keyboard specifically inside run scope or at module level properly
        from pynput import keyboard
        # Collect events until interrupted
        with keyboard.Listener(
                on_press=self.on_press,
                on_release=self.on_release) as listener:
            listener.join()

if __name__ == "__main__":
    app_controller = AppController()
    app_controller.run()
