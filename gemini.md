# AI Speech Tool — Project Constitution

> This file is **law**. All schemas, rules, and architectural invariants live here.

## Data Schema

> ⚠️ Defined based on Discovery Questions.

### Database Schema (PostgreSQL `transcriptions` table)

```sql
CREATE TABLE transcriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  raw_transcription TEXT NOT NULL,
  formatted_transcription TEXT NOT NULL,
  formatting_mode VARCHAR(50) DEFAULT 'plain'
);
```

### Application Internal Payload

```json
{
  "audio_file_path": "/tmp/recording.wav",
  "raw_text": "I uh wanted to make a list of apples and bananas",
  "formatted_text": "- Apples\n- Bananas",
  "formatting_mode": "list"
}
```

## Behavioral Rules

- **Smart Formatting:** Auto-correct speech mistakes and clean output.
- **Multiple Modes:** Support different formatting modes (e.g., plain text, list formatting).
- **Global Operation:** Must be able to trigger recording via a global hotkey system-wide.
- **Direct Insertion:** Output text must be directly inserted into whatever text field the cursor is currently in.

## Architectural Invariants

- All business logic lives in deterministic `tools/` scripts.
- `.env` holds secrets; never hard-code credentials.
- `.tmp/` is used for all intermediate files.
- SOPs in `architecture/` must be updated before corresponding code changes.

## Maintenance Log

| Date       | Change              | Author       |
| ---------- | ------------------- | ------------ |
| 2026-03-04 | Project initialized | System Pilot |
