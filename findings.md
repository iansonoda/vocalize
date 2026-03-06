# AI Speech Tool — Findings

## Discovery Answers (2026-03-04)

| #   | Question             | Answer                                                                                               |
| --- | -------------------- | ---------------------------------------------------------------------------------------------------- |
| 1   | **North Star**       | Transcribe spoken audio from microphone into text using AI — a **Wispr Flow clone**                  |
| 2   | **Integrations**     | OpenAI Whisper via Hugging Face (free), PostgreSQL. API keys not yet ready.                          |
| 3   | **Source of Truth**  | PostgreSQL database for all transcriptions                                                           |
| 4   | **Delivery Payload** | Text inserted directly into whatever text field the cursor is in (system-wide)                       |
| 5   | **Behavioral Rules** | Smart formatting: auto-correct speech mistakes, list formatting, multiple format modes, clean output |

## Key Requirements

- Global hotkey to start/stop recording
- Microphone audio capture
- Whisper transcription via Hugging Face Inference API
- AI post-processing for cleanup & formatting
- Simulate keyboard input to paste into any active text field
- Store transcriptions in PostgreSQL
- Multiple formatting options (plain text, list, etc.)
