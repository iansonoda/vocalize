import os
import requests
from dotenv import load_dotenv

load_dotenv()

HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
# Using the router URL for serverless inference
API_URL = "https://router.huggingface.co/hf-inference/models/openai/whisper-large-v3"
HEADERS = {
    "Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}",
    "Content-Type": "audio/wav"
}

def transcribe_audio(file_path):
    """
    Sends the audio file to Hugging Face Inference API and returns the transcribed text.
    """
    if not os.path.exists(file_path):
        print(f"❌ Error: Audio file not found at {file_path}")
        return None

    print(f"⬆️ Uploading {file_path} to Whisper API...")
    
    try:
        with open(file_path, "rb") as f:
            data = f.read()

        response = requests.post(API_URL, headers=HEADERS, data=data)

        if response.status_code == 200:
            result = response.json()
            # Whisper returns {"text": "transcribed text here"}
            text = result.get("text", "").strip()
            print(f"✅ Transcription complete: '{text}'")
            return text
        elif response.status_code == 503:
            print("⏳ Model is loading. Please try again in a few seconds.")
            return None
        else:
            print(f"❌ API Error ({response.status_code}): {response.text}")
            return None

    except Exception as e:
        print(f"❌ Failed to transcribe: {e}")
        return None

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        transcribe_audio(test_file)
    else:
        print("Usage: python transcriber.py path_to_audio_file.wav")
