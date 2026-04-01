import sounddevice as sd
import soundfile as sf
import numpy as np
import tempfile
import os
import time
import sys

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
        
        # Calculate volume for UI
        volume_norm = float(np.max(np.abs(indata)))
        
        import json
        audio_mono = indata[:, 0] if indata.ndim > 1 else indata
        
        # Simple high-sensitivity frequency bands using FFT
        fft_result = np.abs(np.fft.rfft(audio_mono))
        num_bands = 15
        bands = []
        if len(fft_result) >= num_bands:
            band_size = len(fft_result) // num_bands
            for i in range(num_bands):
                # We multiply by 15.0 to increase the sensitivity of the waveform heavily as requested
                band_val = float(np.mean(fft_result[i*band_size : (i+1)*band_size])) * 15.0
                bands.append(min(1.0, band_val))
        else:
            bands = [volume_norm] * num_bands
            
        print(f"BANDS:{json.dumps(bands)}", flush=True)
        print(f"VOL:{min(1.0, volume_norm)}", flush=True)

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

    def stop_recording(self, telemetry=None):
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
        if telemetry:
            telemetry.mark(
                "temp_file_write_complete",
                audio_file=os.path.basename(temp_file),
                audio_size_bytes=os.path.getsize(temp_file),
            )
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
