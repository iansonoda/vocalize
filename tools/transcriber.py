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

def transcribe_audio(
    file_path,
    telemetry=None,
    event_prefix="transcription_request",
    request_kind="final",
    request_metadata=None,
):
    """
    Sends the audio file to Hugging Face Inference API and returns the transcribed text.
    """
    request_metadata = request_metadata or {}

    if not os.path.exists(file_path):
        print(f"❌ Error: Audio file not found at {file_path}")
        if telemetry:
            telemetry.mark(
                f"{event_prefix}_end",
                status="missing_audio_file",
                request_kind=request_kind,
                **request_metadata,
            )
        return None

    print(f"⬆️ Uploading {file_path} to Whisper API...")
    
    try:
        with open(file_path, "rb") as f:
            data = f.read()

        if telemetry:
            telemetry.mark(
                f"{event_prefix}_start",
                audio_file=os.path.basename(file_path),
                audio_size_bytes=len(data),
                request_kind=request_kind,
                **request_metadata,
            )

        response = requests.post(API_URL, headers=HEADERS, data=data)

        if response.status_code == 200:
            result = response.json()
            # Whisper returns {"text": "transcribed text here"}
            text = result.get("text", "").strip()
            if telemetry:
                telemetry.mark(
                    f"{event_prefix}_end",
                    status="success",
                    http_status=response.status_code,
                    transcript_chars=len(text),
                    request_kind=request_kind,
                    **request_metadata,
                )
            print(f"✅ Transcription complete: '{text}'")
            return text
        elif response.status_code == 503:
            if telemetry:
                telemetry.mark(
                    f"{event_prefix}_end",
                    status="model_loading",
                    http_status=response.status_code,
                    request_kind=request_kind,
                    **request_metadata,
                )
            print("⏳ Model is loading. Please try again in a few seconds.")
            return None
        else:
            if telemetry:
                telemetry.mark(
                    f"{event_prefix}_end",
                    status="api_error",
                    http_status=response.status_code,
                    request_kind=request_kind,
                    **request_metadata,
                )
            print(f"❌ API Error ({response.status_code}): {response.text}")
            return None

    except Exception as e:
        if telemetry:
            telemetry.mark(
                f"{event_prefix}_end",
                status="exception",
                error=str(e),
                request_kind=request_kind,
                **request_metadata,
            )
        print(f"❌ Failed to transcribe: {e}")
        return None

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        transcribe_audio(test_file)
    else:
        print("Usage: python transcriber.py path_to_audio_file.wav")
