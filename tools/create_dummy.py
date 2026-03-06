import wave
import struct

def create_dummy_wav(filename):
    sample_rate = 44100
    duration = 0.5  # seconds
    n_samples = int(sample_rate * duration)
    
    with wave.open(filename, 'w') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for _ in range(n_samples):
            wav.writeframesraw(struct.pack('<h', 0))

if __name__ == "__main__":
    create_dummy_wav("dummy.wav")
    print("Created dummy.wav")
