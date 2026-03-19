"""Entry point — runs the transcription pipeline."""

import json
import os
import sys
from pathlib import Path

# Load .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

from pipeline import run_pipeline

SUPPORTED = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm"}


def main():
    # Get audio path from CLI arg or prompt
    if len(sys.argv) > 1:
        audio_path = sys.argv[1]
    else:
        audio_path = input("Enter path to audio file: ").strip().strip('"')

    if not os.path.isfile(audio_path):
        print(f"Error: file not found — {audio_path}")
        sys.exit(1)

    ext = os.path.splitext(audio_path)[1].lower()
    if ext not in SUPPORTED:
        print(f"Error: unsupported format '{ext}'. Use: {', '.join(SUPPORTED)}")
        sys.exit(1)

    print(f"\nTranscribing: {audio_path}\n")
    result = run_pipeline(audio_path)

    if "error" in result:
        print(f"\nError: {result['error']}")
        sys.exit(1)

    # Save result to JSON file
    output_path = os.path.splitext(audio_path)[0] + "_result.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\nResult saved to {output_path}")

    print("\n" + "=" * 60)
    print("TRANSCRIPTION PIPELINE RESULT")
    print("=" * 60)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
