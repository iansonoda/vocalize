# AI Speech Tool

A premium, open-source AI dictation tool that transcribes, cleans, and formats your speech in real-time. Built as a Wispr Flow clone utilizing open-source models on Hugging Face.

## 🚀 Features

- **Global Hotkey (<kbd>F8</kbd>)**: Trigger recording system-wide.
- **Whisper Transcription**: High-accuracy speech-to-text via OpenAI Whisper-large-v3.
- **Smart AI Cleaner**: Automatically removes "ums", "uhs", and stutters using Qwen-2.5-72B.
- **Intelligent Formatting**: Smartly detects lists, bullets, and punctuation cues.
- **Direct Insertion**: Injects text directly into whatever application you are currently using.
- **Database Logging**: Keeps a history of all transcriptions in Supabase.

## 🛠️ Setup

### 1. Prerequisites

- Python 3.10+
- A Hugging Face account (for API Token)
- A Supabase account (for PostgreSQL database)

### 2. Installation

```bash
# Clone the repository and navigate to the folder
# Install virtual environment and dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configuration

1. Create a `.env` file from the `.env.template`.
2. Enter your `HUGGINGFACE_API_TOKEN`.
3. Enter your Supabase `DATABASE_URL`.

### 4. Permissions (macOS)

The first time you run the tool, macOS will ask for permissions.

- **Accessibility**: Required to simulate <kbd>Cmd</kbd>+<kbd>V</kbd> for pasting.
- **Input Monitoring**: Required for the global <kbd>F8</kbd> hotkey.
- **Microphone**: Required to record your voice.

## 🕹️ Usage

Run the tool:

```bash
./run.sh
```

- **Press <kbd>F8</kbd>**: Start recording.
- **Speak**: Dictate your thoughts (you can say "one", "two", "bullet point").
- **Press <kbd>F8</kbd>**: Stop and automatically paste the cleaned text.

## 🧪 Testing

Run the vigorous test suite to ensure everything is connected:

```bash
source venv/bin/activate
python3 tests/comprehensive_test.py
```
