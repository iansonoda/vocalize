import os
import requests
from dotenv import load_dotenv

load_dotenv()

HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
# New router URL
API_URL = "https://router.huggingface.co/hf-inference/models/openai/whisper-large-v3"
headers = {"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"}

def test_inference():
    print("Testing Hugging Face Inference API connection with dummy audio...")
    
    if not os.path.exists("dummy.wav"):
        print("Creating dummy.wav...")
        import subprocess
        subprocess.run(["python3", "tools/create_dummy.py"])

    with open("dummy.wav", "rb") as f:
        data = f.read()

    headers["Content-Type"] = "audio/wav"
    response = requests.post(API_URL, headers=headers, data=data)
    
    if response.status_code == 200:
        print("✅ Successfully authenticated and got transcription result!")
        print("Result:", response.json())
    elif response.status_code == 503:
        print("✅ Successfully authenticated. Model is currently loading/starting up.")
        print("Wait a few seconds and try again.")
    elif response.status_code == 401:
        print("❌ Authentication failed. Please check your HUGGINGFACE_API_TOKEN in .env.")
    else:
        print(f"⚠️ Unexpected response (Code: {response.status_code})")
        try:
            print("Error details:", response.json())
        except:
             print("Body (truncated):", response.text[:200])

if __name__ == "__main__":
    if not HUGGINGFACE_API_TOKEN or HUGGINGFACE_API_TOKEN.strip() == "":
        print("❌ HUGGINGFACE_API_TOKEN is not set in .env")
    else:
        test_inference()
