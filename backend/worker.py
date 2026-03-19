
import sys
import json
import os
from pathlib import Path

# Load .env file
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

# Add custom ffmpeg path from FFMPEG_PATH env var if set
_FFMPEG_DIR = os.environ.get("FFMPEG_PATH", "")
if _FFMPEG_DIR and os.path.isdir(_FFMPEG_DIR) and _FFMPEG_DIR not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _FFMPEG_DIR + os.pathsep + os.environ["PATH"]

import whisper

"""This is the standalone worker script — transcribes a single audio chunk."""


def main():
    chunk_path = sys.argv[1]
    model_name = sys.argv[2]
    offset = float(sys.argv[3])

    model = whisper.load_model(model_name)
    result = model.transcribe(chunk_path, fp16=False)

    segments = []
    for seg in result["segments"]:
        segments.append({
            "start": round(seg["start"] + offset, 2),
            "end": round(seg["end"] + offset, 2),
            "text": seg["text"].strip(),
        })

    output = {
        "text": result["text"].strip(),
        "segments": segments,
        "language": result["language"],
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
