import os
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()

HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")

# Initialize the Hugging Face Inference Client
# Qwen/Qwen2.5-72B-Instruct is excellent for instructions and grammar
MODEL = "Qwen/Qwen2.5-Coder-32B-Instruct" # Better general performance

# If the free tier blocks the 72B model, it will gracefully fallback to returning the raw text
client = InferenceClient(model=MODEL, token=HUGGINGFACE_API_TOKEN)

def clean_text(raw_text, mode="plain", tone="natural"):
    """
    Sends raw transcribed text to Qwen via Hugging Face to fix grammar, remove stutters, and format it.
    Fallback to raw text if the API fails or is loading.
    """
    if not raw_text or not raw_text.strip():
        return raw_text
        
    system_prompt = (
        "You are an AI dictation assistant. Your job is to clean up raw speech-to-text transcriptions.\n"
        "1. Remove all verbal fillers (um, uh, like, you know).\n"
        "2. Fix false starts, stutters, and grammatical mistakes.\n"
        "3. Apply proper punctuation and capitalization.\n"
        "4. DO NOT add any conversational responses like 'Here is the fixed text'. Output ONLY the clean text.\n"
        "5. Keep the original meaning intact.\n"
        f"6. Tone: Adjust the tone to be {tone}. (natural/professional/casual).\n"
        "7. If the user is listing items (e.g. they say 'one item two item' or 'first item second item'), actively format the output as a clean numbered or bulleted list with line breaks.\n"
        "8. Specifically look for dictation cues like 'next line', 'bullet point', 'number one', 'colon'."
    )
    
    if mode == "list":
         system_prompt += "\n9. Forcibly format the entire output as a clean markdown bulleted list regardless of the input structure."
         
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": raw_text}
    ]
    
    print(f"🧹 Cleaning & formatting text with AI ({MODEL})...")
    try:
        # Utilizing the built-in huggingface_hub chat completion
        response = client.chat_completion(
            messages=messages,
            max_tokens=1024,
            temperature=0.2
        )
        
        cleaned_text = response.choices[0].message.content.strip()
        return cleaned_text
             
    except Exception as e:
        print(f"❌ Error during AI cleanup: {e}")
        # Automatically fallback to the raw text so the tool doesn't break
        return raw_text

if __name__ == "__main__":
    import sys
    test_text = sys.argv[1] if len(sys.argv) > 1 else "um so yeah i was wondering like if we could maybe go to the store and get uh apples and stuff"
    print(f"Raw: {test_text}")
    print(f"Cleaned: {clean_text(test_text)}")
