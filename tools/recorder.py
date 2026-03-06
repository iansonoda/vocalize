import sounddevice as sd
import soundfile as sf
import numpy as np
import tempfile
import os
import time

class AudioRecorder:
    def __init__(self, sample_rate=44100, channels=1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.is_recording = False
        self.audio_data = []
        self.stream = None

    def _audio_callback(self, indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            print(status, file=sys.stderr)
        self.audio_data.append(indata.copy())

    def start_recording(self):
        """Starts the audio recording."""
        self.is_recording = True
        self.audio_data = []
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=self._audio_callback
        )
        self.stream.start()
        print("🎙️ Recording started...")

    def stop_recording(self):
        """Stops the recording and saves to a temporary WAV file."""
        if not self.is_recording:
            return None

        self.is_recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            
        print("⏹️ Recording stopped.")

        if not self.audio_data:
            print("⚠️ No audio data captured.")
            return None

        # Concatenate all recorded blocks
        recording = np.concatenate(self.audio_data, axis=0)

        # Ensure the .tmp directory exists
        tmp_dir = os.path.join(os.getcwd(), ".tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        
        # Save to a temporary WAV file
        temp_file = os.path.join(tmp_dir, f"recording_{int(time.time())}.wav")
        
        # Save array to WAV
        sf.write(temp_file, recording, self.sample_rate)
        print(f"💾 Saved recording to {temp_file}")
        
        return temp_file

if __name__ == "__main__":
    # Simple test for the recorder
    recorder = AudioRecorder()
    print("Test: Will record for 3 seconds...")
    recorder.start_recording()
    time.sleep(3)
    saved_path = recorder.stop_recording()
    print(f"Test completed. File saved at: {saved_path}")
