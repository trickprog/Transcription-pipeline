
import os
import sys
import json
import tempfile
import logging
import subprocess

import whisper
import whisper.audio
import soundfile as sf

# Add custom ffmpeg path from FFMPEG_PATH env var if set
_FFMPEG_DIR = os.environ.get("FFMPEG_PATH", "")
if _FFMPEG_DIR and os.path.isdir(_FFMPEG_DIR) and _FFMPEG_DIR not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _FFMPEG_DIR + os.pathsep + os.environ["PATH"]

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
CHUNK_DURATION = 300  # 5 minutes per chunk
OVERLAP = 2  # 2 second overlap to avoid cutting mid-word
WORKER_SCRIPT = os.path.join(os.path.dirname(__file__), "worker.py")

"""The core transcription logic using OpenAI Whisper with parallel chunking via subprocesses."""

def _split_audio(file_path):
    """Load audio and split into chunks. Returns list of (chunk_path, offset)."""
    audio = whisper.audio.load_audio(file_path)
    total_samples = len(audio)
    total_duration = total_samples / SAMPLE_RATE

    if total_duration <= CHUNK_DURATION:
        return [(file_path, 0.0)]

    chunk_samples = CHUNK_DURATION * SAMPLE_RATE
    overlap_samples = OVERLAP * SAMPLE_RATE
    step = chunk_samples - overlap_samples

    chunks = []
    tmp_dir = tempfile.mkdtemp(prefix="whisper_chunks_")

    for i, start in enumerate(range(0, total_samples, step)):
        end = min(start + chunk_samples, total_samples)
        chunk_audio = audio[start:end]

        chunk_path = os.path.join(tmp_dir, f"chunk_{i}.wav")
        sf.write(chunk_path, chunk_audio, SAMPLE_RATE)

        offset = start / SAMPLE_RATE
        chunks.append((chunk_path, offset))

        if end >= total_samples:
            break

    logger.info("Split audio into %d chunks of %ds each", len(chunks), CHUNK_DURATION)
    return chunks


def _merge_results(results):
    """Merge transcription results from multiple chunks."""
    all_text = []
    all_segments = []
    language = "unknown"

    for result in results:
        all_text.append(result["text"])
        all_segments.extend(result["segments"])
        if result["language"] != "unknown":
            language = result["language"]

    return {
        "text": " ".join(all_text),
        "segments": all_segments,
        "language": language,
    }


def transcribe_audio(file_path: str, model_name: str = "base", workers: int = None) -> dict:
    """Transcribe an audio file using Whisper with parallel subprocesses.

    Args:
        file_path: Path to the audio file.
        model_name: Whisper model size (tiny, base, small, medium, large).
        workers: Number of parallel workers. Defaults to half your CPU cores.

    Returns:
        Dict with keys: text, segments, language.
    """
    if workers is None:
        workers = max(1, os.cpu_count() // 2)

    chunks = _split_audio(file_path)

    # Short audio — no chunking needed
    if len(chunks) == 1 and chunks[0][1] == 0.0:
        logger.info("Short audio — transcribing directly")
        model = whisper.load_model(model_name)
        result = model.transcribe(file_path, fp16=False)
        return {
            "text": result["text"].strip(),
            "segments": [
                {
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"].strip(),
                }
                for seg in result["segments"]
            ],
            "language": result["language"],
        }

    # Launch parallel subprocesses — each is a clean Python process
    logger.info("Processing %d chunks with %d workers", len(chunks), min(len(chunks), workers))
    python_exe = sys.executable
    processes = []

    for chunk_path, offset in chunks:
        # Limit concurrent processes
        while len(processes) >= workers:
            _wait_for_one(processes)

        proc = subprocess.Popen(
            [python_exe, WORKER_SCRIPT, chunk_path, model_name, str(offset)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        processes.append((proc, chunk_path, offset))

    # Collect results in order
    results = []
    for proc, chunk_path, offset in processes:
        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            logger.error("Worker failed for chunk %s: %s", chunk_path, stderr.decode())
            continue
        result = json.loads(stdout.decode())
        results.append(result)
        logger.info("Chunk done: offset=%.0fs", offset)

    # Clean up temp chunk files
    for path, _ in chunks:
        if path != file_path:
            try:
                os.remove(path)
            except OSError:
                pass

    return _merge_results(results)


def _wait_for_one(processes):
    """Wait for any one process to finish."""
    while True:
        for i, (proc, _, _) in enumerate(processes):
            if proc.poll() is not None:
                processes.pop(i)
                return
