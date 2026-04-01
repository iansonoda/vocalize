import sounddevice as sd
import soundfile as sf
import numpy as np
import tempfile
import os
import time
import sys
import threading
from tools.output import emit_stdout, emit_stderr

class AudioRecorder:
    def __init__(self, sample_rate=44100, channels=1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.is_recording = False
        self.audio_data = []
        self.stream = None
        self.audio_lock = threading.Lock()

    def _audio_callback(self, indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            emit_stderr(str(status))
        with self.audio_lock:
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
            
        emit_stdout(f"BANDS:{json.dumps(bands)}")
        emit_stdout(f"VOL:{min(1.0, volume_norm)}")

    def start_recording(self):
        """Starts the audio recording."""
        self.is_recording = True
        with self.audio_lock:
            self.audio_data = []
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=self._audio_callback
        )
        self.stream.start()
        emit_stdout("🎙️ Recording started...")

    def get_audio_snapshot(self):
        with self.audio_lock:
            if not self.audio_data:
                return None, 0.0
            blocks = [block.copy() for block in self.audio_data]

        recording = np.concatenate(blocks, axis=0)
        duration_seconds = recording.shape[0] / float(self.sample_rate)
        return recording, duration_seconds

    def get_recording_duration_seconds(self):
        _, duration_seconds = self.get_audio_snapshot()
        return duration_seconds

    def write_snapshot_file(self, prefix="recording", session_id=None):
        recording, duration_seconds = self.get_audio_snapshot()
        if recording is None:
            return None, 0.0

        tmp_dir = os.path.join(os.getcwd(), ".tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        if session_id:
            tmp_dir = os.path.join(tmp_dir, "partials", session_id)
            os.makedirs(tmp_dir, exist_ok=True)

        temp_file = os.path.join(
            tmp_dir,
            f"{prefix}_{int(time.time() * 1000)}.wav",
        )
        sf.write(temp_file, recording, self.sample_rate)
        return temp_file, duration_seconds

    def stop_recording(self, telemetry=None):
        """Stops the recording and saves to a temporary WAV file."""
        if not self.is_recording:
            return None

        self.is_recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            
        emit_stdout("⏹️ Recording stopped.")

        with self.audio_lock:
            has_audio = bool(self.audio_data)

        if not has_audio:
            emit_stdout("⚠️ No audio data captured.")
            return None

        temp_file, _ = self.write_snapshot_file(prefix="recording")
        if telemetry:
            telemetry.mark(
                "temp_file_write_complete",
                audio_file=os.path.basename(temp_file),
                audio_size_bytes=os.path.getsize(temp_file),
            )
        emit_stdout(f"💾 Saved recording to {temp_file}")
        
        return temp_file

if __name__ == "__main__":
    # Simple test for the recorder
    recorder = AudioRecorder()
    print("Test: Will record for 3 seconds...")
    recorder.start_recording()
    time.sleep(3)
    saved_path = recorder.stop_recording()
    print(f"Test completed. File saved at: {saved_path}")
