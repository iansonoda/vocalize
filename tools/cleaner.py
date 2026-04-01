import os
import re
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from tools.output import emit_stdout

load_dotenv()

HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")

# Initialize the Hugging Face Inference Client
# Qwen/Qwen2.5-72B-Instruct is excellent for instructions and grammar
MODEL = "Qwen/Qwen2.5-Coder-32B-Instruct" # Better general performance

# If the free tier blocks the 72B model, it will gracefully fallback to returning the raw text
client = InferenceClient(model=MODEL, token=HUGGINGFACE_API_TOKEN)

SUPPORTED_MODES = {
    "plain": {
        "label": "Plain",
        "instructions": (
            "For plain mode, return a natural prose version of the dictation with only minimal cleanup."
        ),
    },
    "notes": {
        "label": "Notes",
        "instructions": (
            "For notes mode, format the dictation as clean notes. Preserve the original order of ideas. "
            "Use bullets or short sections only when the content naturally breaks into multiple points. "
            "Do not invent headings, summaries, or action items that were not implied by the speaker."
        ),
    },
    "email": {
        "label": "Email",
        "instructions": (
            "For email mode, format the dictation as an email-ready message body. Preserve the speaker's wording and intent. "
            "Use paragraph breaks where helpful. Include greetings, sign-offs, or subject lines only if the speaker clearly dictated them. "
            "Do not invent recipients, pleasantries, or extra framing."
        ),
    },
    "code": {
        "label": "Code",
        "instructions": (
            "For code mode, be extremely literal and low-creativity. Preserve identifiers, developer vocabulary, numbers, and sequence. "
            "Convert explicit dictation cues such as colon, comma, open paren, close paren, underscore, tab, indent, new line, and bullet point "
            "into code or structured text where appropriate. Output raw code or raw technical text only, never explanations or markdown fences."
        ),
    },
    "list": {
        "label": "List",
        "instructions": (
            "For list mode, format the entire output as a clean markdown bulleted list while preserving the user's content."
        ),
    },
}

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


def normalize_mode(mode):
    normalized = (mode or "plain").strip().lower()
    return normalized if normalized in SUPPORTED_MODES else "plain"


def _tokenize(text):
    return re.findall(r"[a-z0-9_']+", text.lower())


def _strip_wrapping_code_fences(text):
    stripped = text.strip()
    fenced_match = re.match(r"^```[a-zA-Z0-9_-]*\n([\s\S]*?)\n```$", stripped)
    if fenced_match:
        return fenced_match.group(1).strip()
    return stripped


def _should_fallback_to_raw(raw_text, cleaned_text, mode="plain"):
    if not cleaned_text or not cleaned_text.strip():
        return "empty_output"

    cleaned_lower = cleaned_text.strip().lower()
    if cleaned_lower.startswith(ASSISTANT_STYLE_PREFIXES):
        return "assistant_style_prefix"

    raw_tokens = _tokenize(raw_text)
    cleaned_tokens = _tokenize(cleaned_text)

    if len(raw_tokens) < 12:
        return None

    min_ratio = 0.45
    overlap_floor = 0.6
    if mode == "code":
        min_ratio = 0.35
        overlap_floor = 0.45

    if len(cleaned_tokens) < max(4, int(len(raw_tokens) * min_ratio)):
        return "overcompressed_output"

    raw_vocabulary = set(raw_tokens)
    retained_token_count = sum(1 for token in cleaned_tokens if token in raw_vocabulary)
    if cleaned_tokens and (retained_token_count / len(cleaned_tokens)) < overlap_floor:
        return "low_token_overlap"

    return None

def _build_cleaner_result(
    raw_text,
    text,
    requested_mode,
    resolved_mode,
    status,
    fallback_reason=None,
    output_source="cleaned",
):
    return {
        "raw_text": raw_text,
        "text": text,
        "requested_mode": requested_mode,
        "resolved_mode": resolved_mode,
        "status": status,
        "fallback_reason": fallback_reason,
        "output_source": output_source,
    }


def clean_text(raw_text, mode="plain", tone="natural", telemetry=None, return_metadata=False):
    """
    Sends raw transcribed text to Qwen via Hugging Face to fix grammar, remove stutters, and format it.
    Fallback to raw text if the API fails or is loading.
    """
    requested_mode = mode or "plain"
    resolved_mode = normalize_mode(requested_mode)

    if not raw_text or not raw_text.strip():
        result = _build_cleaner_result(
            raw_text=raw_text,
            text=raw_text,
            requested_mode=requested_mode,
            resolved_mode=resolved_mode,
            status="skipped_empty_raw",
            output_source="raw_fallback",
        )
        return result if return_metadata else raw_text
        
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
        "9. When in doubt, prefer a more literal output over a more polished one.\n"
        f"10. Active formatting mode: {resolved_mode}.\n"
        f"11. {SUPPORTED_MODES[resolved_mode]['instructions']}"
    )
         
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": raw_text}
    ]
    
    emit_stdout(f"🧹 Cleaning & formatting text with AI ({MODEL})...")
    try:
        if telemetry:
            telemetry.mark(
                "cleanup_start",
                requested_mode=requested_mode,
                mode=resolved_mode,
                tone=tone,
                raw_chars=len(raw_text),
            )

        # Utilizing the built-in huggingface_hub chat completion
        response = client.chat_completion(
            messages=messages,
            max_tokens=1024,
            temperature=0.2
        )
        
        cleaned_text = _strip_wrapping_code_fences(
            response.choices[0].message.content.strip()
        )
        fallback_reason = _should_fallback_to_raw(raw_text, cleaned_text, mode=resolved_mode)
        if fallback_reason:
            if telemetry:
                telemetry.mark(
                    "cleanup_end",
                    status="fallback_to_raw",
                    requested_mode=requested_mode,
                    mode=resolved_mode,
                    cleaned_chars=len(cleaned_text),
                )
                telemetry.mark(
                    "cleanup_guardrail_fallback",
                    reason=fallback_reason,
                    requested_mode=requested_mode,
                    mode=resolved_mode,
                    cleaned_chars=len(cleaned_text),
                )
            result = _build_cleaner_result(
                raw_text=raw_text,
                text=raw_text,
                requested_mode=requested_mode,
                resolved_mode=resolved_mode,
                status="fallback_to_raw",
                fallback_reason=fallback_reason,
                output_source="raw_fallback",
            )
            return result if return_metadata else raw_text

        if telemetry:
            telemetry.mark(
                "cleanup_end",
                status="success",
                requested_mode=requested_mode,
                mode=resolved_mode,
                cleaned_chars=len(cleaned_text),
            )
        result = _build_cleaner_result(
            raw_text=raw_text,
            text=cleaned_text,
            requested_mode=requested_mode,
            resolved_mode=resolved_mode,
            status="success",
            output_source="cleaned",
        )
        return result if return_metadata else cleaned_text
             
    except Exception as e:
        if telemetry:
            telemetry.mark(
                "cleanup_end",
                status="exception",
                requested_mode=requested_mode,
                mode=resolved_mode,
                error=str(e),
            )
        emit_stdout(f"❌ Error during AI cleanup: {e}")
        # Automatically fallback to the raw text so the tool doesn't break
        result = _build_cleaner_result(
            raw_text=raw_text,
            text=raw_text,
            requested_mode=requested_mode,
            resolved_mode=resolved_mode,
            status="fallback_to_raw",
            fallback_reason="exception",
            output_source="raw_fallback",
        )
        return result if return_metadata else raw_text

if __name__ == "__main__":
    import sys
    test_text = sys.argv[1] if len(sys.argv) > 1 else "um so yeah i was wondering like if we could maybe go to the store and get uh apples and stuff"
    print(f"Raw: {test_text}")
    print(f"Cleaned: {clean_text(test_text)}")
