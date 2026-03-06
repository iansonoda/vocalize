import os
import sys
import time
from dotenv import load_dotenv

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.cleaner import clean_text
from tools.db import save_transcription
from tools.transcriber import transcribe_audio
from tools.recorder import AudioRecorder

load_dotenv()

def test_section(name):
    print(f"\n{'='*20} {name} {'='*20}")

def run_cleaner_stress_tests():
    test_section("AI CLEANER STRESS TESTS")
    
    test_cases = [
        {
            "name": "Heavy verbal fillers",
            "input": "Um, so, like, I was thinking, uh, maybe, sort of, we should, you know, go to the beach tomorrow? If that's like okay with you.",
            "expected_contain": ["beach tomorrow", "okay with you"]
        },
        {
            "name": "Numbered list dictation",
            "input": "number one finish the report number two send the email to Sarah number three prepare for the meeting",
            "expected_contain": ["1.", "2.", "3."]
        },
        {
            "name": "Bullet point cues",
            "input": "bullet point check task one bullet point review draft bullet point submit final version",
            "expected_contain": ["- ", "Check task", "Review draft"]
        },
        {
            "name": "Punctuation cues",
            "input": "Hello world comma this is a test period New line I am dictating now exclamation point",
            "expected_contain": ["Hello world,", "test.", "!", "\n"]
        },
        {
            "name": "Technical/Coding dictation",
            "input": "define a function named calculate underscore total with parameters a and b colon return a plus b",
            "expected_contain": ["def", "calculate_total", "(a, b):", "return a + b"]
        }
    ]

    for case in test_cases:
        print(f"Running: {case['name']}")
        print(f"Input: {case['input']}")
        start = time.time()
        result = clean_text(case['input'])
        duration = time.time() - start
        print(f"Output ({duration:.2f}s):\n{result}")
        print("-" * 40)

def test_database_logging():
    test_section("DATABASE LOGGING TEST")
    raw = "This is a raw test transcription"
    formatted = "This is a formatted test transcription."
    print(f"Attempting to save: {formatted}")
    save_transcription(raw, formatted, mode="test")
    print("✅ Database write command executed (Check Supabase for 'test' mode entries)")

def test_audio_hardware():
    test_section("AUDIO HARDWARE SANITY CHECK")
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        print("Available Devices:")
        print(devices)
        default_input = sd.query_devices(kind='input')
        print(f"\nDefault Input Device: {default_input['name']}")
        print("✅ Audio hardware accessible.")
    except Exception as e:
        print(f"❌ Audio hardware error: {e}")

def test_transcription_api():
    test_section("TRANSCRIPTION API CHECK")
    # Using dummy.wav if exists, else skip
    dummy_wav = "dummy.wav"
    if not os.path.exists(dummy_wav):
         from tools.create_dummy import create_dummy_wav
         create_dummy_wav(dummy_wav)
         
    print(f"Testing transcription with {dummy_wav}...")
    result = transcribe_audio(dummy_wav)
    if result:
        print(f"✅ Transcription Success: {result}")
    else:
        print("❌ Transcription Failed.")

if __name__ == "__main__":
    print("🚀 STARTING VIGOROUS TEST SUITE")
    
    test_audio_hardware()
    test_transcription_api()
    run_cleaner_stress_tests()
    test_database_logging()
    
    print("\n🚀 ALL TESTS COMPLETED")
