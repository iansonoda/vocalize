import os
import re
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()

HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")

# Initialize the Hugging Face Inference Client
# Qwen/Qwen2.5-72B-Instruct is excellent for instructions and grammar
MODEL = "Qwen/Qwen2.5-Coder-32B-Instruct" # Better general performance

# If the free tier blocks the 72B model, it will gracefully fallback to returning the raw text
client = InferenceClient(model=MODEL, token=HUGGINGFACE_API_TOKEN)

ASSISTANT_STYLE_PREFIXES = (
    "here is",
    "here's",
    "sure",
    "certainly",
    "cleaned text",
    "revised text",
    "corrected text",
    "formatted text",
)


def _tokenize(text):
    return re.findall(r"[a-z0-9_']+", text.lower())


def _should_fallback_to_raw(raw_text, cleaned_text):
    if not cleaned_text or not cleaned_text.strip():
        return "empty_output"

    cleaned_lower = cleaned_text.strip().lower()
    if cleaned_lower.startswith(ASSISTANT_STYLE_PREFIXES):
        return "assistant_style_prefix"

    raw_tokens = _tokenize(raw_text)
    cleaned_tokens = _tokenize(cleaned_text)

    if len(raw_tokens) < 12:
        return None

    if len(cleaned_tokens) < max(4, int(len(raw_tokens) * 0.45)):
        return "overcompressed_output"

    raw_vocabulary = set(raw_tokens)
    retained_token_count = sum(1 for token in cleaned_tokens if token in raw_vocabulary)
    if cleaned_tokens and (retained_token_count / len(cleaned_tokens)) < 0.6:
        return "low_token_overlap"

    return None

def clean_text(raw_text, mode="plain", tone="natural", telemetry=None):
    """
    Sends raw transcribed text to Qwen via Hugging Face to fix grammar, remove stutters, and format it.
    Fallback to raw text if the API fails or is loading.
    """
    if not raw_text or not raw_text.strip():
        return raw_text
        
    system_prompt = (
        "You are an AI dictation assistant. Your job is to clean up raw speech-to-text transcriptions.\n"
        "1. Your highest priority is fidelity. Preserve the speaker's wording, sequence, level of detail, names, numbers, and intent.\n"
        "2. Remove only obvious verbal fillers such as um, uh, like, and you know when they are truly filler.\n"
        "3. Fix false starts only with the smallest possible edit. Do not compress multiple thoughts into a shorter summary.\n"
        "4. Apply punctuation and capitalization, but do NOT reword, paraphrase, shorten, summarize, or omit meaningful content.\n"
        "5. Output ONLY the cleaned text. Do NOT add prefaces such as 'Here is the fixed text'.\n"
        f"6. Maintain the user's original tone. Ignore requests to change the tone to {tone} if it would alter their words.\n"
        "7. Preserve dictated structure cues such as next line, bullet point, number one, colon, indentation cues, and list structure when clearly intended.\n"
        "8. If the transcript is already clean enough, return it nearly unchanged aside from punctuation/capitalization and filler removal.\n"
        "9. When in doubt, prefer a more literal output over a more polished one."
    )
    
    if mode == "list":
         system_prompt += "\n9. Forcibly format the entire output as a clean markdown bulleted list regardless of the input structure."
         
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": raw_text}
    ]
    
    print(f"🧹 Cleaning & formatting text with AI ({MODEL})...")
    try:
        if telemetry:
            telemetry.mark(
                "cleanup_start",
                mode=mode,
                tone=tone,
                raw_chars=len(raw_text),
            )

        # Utilizing the built-in huggingface_hub chat completion
        response = client.chat_completion(
            messages=messages,
            max_tokens=1024,
            temperature=0.2
        )
        
        cleaned_text = response.choices[0].message.content.strip()
        fallback_reason = _should_fallback_to_raw(raw_text, cleaned_text)
        if fallback_reason:
            if telemetry:
                telemetry.mark(
                    "cleanup_end",
                    status="fallback_to_raw",
                    cleaned_chars=len(cleaned_text),
                )
                telemetry.mark(
                    "cleanup_guardrail_fallback",
                    reason=fallback_reason,
                    cleaned_chars=len(cleaned_text),
                )
            return raw_text

        if telemetry:
            telemetry.mark(
                "cleanup_end",
                status="success",
                cleaned_chars=len(cleaned_text),
            )
        return cleaned_text
             
    except Exception as e:
        if telemetry:
            telemetry.mark("cleanup_end", status="exception", error=str(e))
        print(f"❌ Error during AI cleanup: {e}")
        # Automatically fallback to the raw text so the tool doesn't break
        return raw_text

if __name__ == "__main__":
    import sys
    test_text = sys.argv[1] if len(sys.argv) > 1 else "um so yeah i was wondering like if we could maybe go to the store and get uh apples and stuff"
    print(f"Raw: {test_text}")
    print(f"Cleaned: {clean_text(test_text)}")
