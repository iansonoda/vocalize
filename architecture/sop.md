# AI Speech Tool — Standard Operating Procedures

## System Architecture

The AI Speech Tool is a modular Python-based desktop application designed for high-performance dictation cleanup.

### 1. Data Flow

1. **Audio Capture (`tools/recorder.py`)**: Uses `sounddevice` to capture microphone input into a NumPy array and exports it as a WAV file.
2. **Transcription (`tools/transcriber.py`)**: Sends the WAV file to the Hugging Face Whisper-large-v3 serverless inference endpoint.
3. **Cleaning/Formatting (`tools/cleaner.py`)**: The raw text is passed to the Qwen-2.5-72B-Instruct model (via Hugging Face) to remove verbal fillers and apply structured formatting.
4. **Injection (`tools/paster.py`)**: The polished text is moved to the system clipboard via `pyperclip` and injected into the active application using `pyautogui` keyboard simulation.
5. **Persistence (`tools/db.py`)**: Both raw and formatted text are logged asynchronously to a Supabase PostgreSQL instance.

### 2. Operational Guards

- **Environment**: All secrets are managed via `.env`.
- **Latency**: Each stage is timed and logged to stdout for performance monitoring.
- **Fail-safe**: If the AI Cleaner or Database fails, the system falls back to pasting the raw transcription to ensure no data loss.

### 3. Key Configurations

- **Hugging Face**: Uses the dedicated `InferenceClient` for robust connection.
- **Supabase**: Uses `psycopg2` with the `Transaction pooler` URI for low-latency logging.

## Maintenance

- **Temporary Files**: `main.py` automatically purges `.tmp/*.wav` files after successful transcription to prevent storage bloat.
- **Testing**: Use `tests/comprehensive_test.py` to verify individual module sanity.
