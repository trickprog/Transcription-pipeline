# Transcription Pipeline

A full-stack application that converts audio files to text using OpenAI's Whisper model, with a React frontend and Flask backend.

## Architecture

```
User uploads audio -> React (port 3000) -> proxy -> Flask API (port 5000)
                                                        |
                                                    server.py
                                                    saves file to temp
                                                        |
                                                    pipeline.py
                                                    orchestrates stages
                                                        |
                                                Stage 1: transcribe.py
                                                loads audio, splits if needed,
                                                spawns parallel worker.py processes
                                                        |
                                                Stage 2: processor.py
                                                cleans text, builds summary
                                                        |
                                                    JSON response
                                                        |
                                                React displays result
```

## Design Decisions

### Using OpenAI Whisper
Whisper runs locally. It supports 90+ languages out of the box and handles noisy audio well. The `base` model balances speed and accuracy for most use cases.

### Using subprocess-based parallelism
Python's GIL prevents true parallel execution with threads for CPU-bound work. `ProcessPoolExecutor` crashes on Windows when called from Flask. The solution: spawn independent `worker.py` subprocesses via `subprocess.Popen`. Each worker is a clean Python process — no GIL, no Flask interference, true parallel execution across CPU cores.

### Using chunk audio into 5-minute segments
Long audio files (1+ hours) are slow to process sequentially. Splitting into chunks and processing them in parallel across multiple CPU cores reduces transcription time significantly. A 1-hour file processes in ~3 minutes on my PC (i9 13 Gen). The 2-second overlap between chunks prevents words from being cut at boundaries.

### Using Flask over FastAPI
Simplicity. Flask handles file uploads and JSON responses with minimal boilerplate. The API has a single endpoint — no need for async, WebSockets, or complex routing.

### Using a separate worker.py
Each subprocess needs to be a standalone script. `worker.py` loads Whisper, transcribes one chunk, and prints JSON to stdout. This avoids Flask module re-imports that crash `ProcessPoolExecutor` on Windows.

### Using proxy React through Flask
During development, React runs on port 3000 and Flask on port 5000. The `proxy` field in `package.json` forwards `/api/*` requests to Flask, avoiding CORS issues without extra configuration.

### Using ffmpeg
Whisper only understands raw audio waveforms. ffmpeg decodes all supported formats (MP3, WAV, M4A, OGG, FLAC, WEBM) into waveform data that Whisper can process. Without it, only WAV files would work.

### Using .env for configuration
The setup script auto-detects ffmpeg's location and writes it to `.env`. This avoids hardcoded paths and makes the project portable across systems. Each file that needs ffmpeg (`server.py`, `worker.py`, `transcribe.py`) loads `.env` at startup.

### Using frontend and backend
Clean separation of concerns. The backend is a standalone API that can be used via CLI (`main.py`) or HTTP (`server.py`). The frontend is a standard React app that can be swapped out or deployed independently.

## Project Structure

```
transcription-pipeline/
├── setup.py                  # One-click setup and run
├── .gitignore
├── backend/
│   ├── .env                  # Auto-generated config (ffmpeg path, model)
│   ├── .env.example          # Template for .env
│   ├── requirements.txt      # Python dependencies
│   ├── server.py             # Flask API server
│   ├── pipeline.py           # Orchestrates transcription + processing
│   ├── transcribe.py         # Whisper transcription with parallel chunking
│   ├── worker.py             # Subprocess worker for chunk transcription
│   ├── processor.py          # Text cleanup and summary builder
│   └── main.py               # CLI entry point
└── frontend/
    ├── package.json          # React dependencies + proxy config
    └── src/
        ├── App.js            # Upload UI, results display
        └── App.css           # Dark theme styling
```

## Supported Formats

WAV, MP3, M4A, OGG, FLAC, WEBM

## How It Works

1. User uploads audio on the React UI
2. React proxies the request to the Flask API
3. Flask saves the file to temp storage
4. Pipeline orchestrates transcription and processing
5. Short audio (<5 min) is transcribed directly by Whisper
6. Long audio (>5 min) is split into 5-min chunks and transcribed in parallel via worker subprocesses
7. Results are merged and text is cleaned
8. JSON response is sent back to React
9. React displays the transcription, stats, and timestamped segments

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- ffmpeg (`winget install ffmpeg` on Windows)

### Setup and Run

```bash
cd transcription-pipeline
python setup.py
```

This will:
1. Find ffmpeg on your system
2. Create a Python virtual environment
3. Install all dependencies
4. Download the Whisper base model
5. Install frontend dependencies and build
6. Start both servers

Then open http://localhost:3000

### CLI Usage

```bash
cd backend
python main.py                          # prompts for file path
python main.py path/to/audio.mp3        # direct path
```

## Whisper Models

| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| tiny | 39 MB | Fastest | Lower |
| base | 74 MB | Fast | Good |
| small | 244 MB | Medium | Better |
| medium | 769 MB | Slow | High |
| large | 1550 MB | Slowest | Best |

Default is `base`. Change in `backend/.env` via `WHISPER_MODEL`.

## API

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/transcribe` | Upload audio file, returns transcription JSON |

### Request
```
POST /api/transcribe
Content-Type: multipart/form-data
Body: file=<audio file>
```

### Response
```json
{
  "cleaned_text": "The transcribed text...",
  "word_count": 150,
  "language": "en",
  "segment_count": 12,
  "pipeline_duration_seconds": 4.52,
  "metadata": {
    "raw_text": "...",
    "segments": [
      {"start": 0.0, "end": 3.5, "text": "..."}
    ]
  }
}
```
