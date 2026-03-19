
import logging
import time

from transcribe import transcribe_audio
from processor import build_summary

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

"""The pipeline arranger that chains transcription and processing."""

def run_pipeline(audio_path: str, model_name: str = "base") -> dict:
    
    
    start_time = time.time()

    # Stage 1: Transcription
    logger.info("Stage 1/2: Transcribing audio — %s", audio_path)
    try:
        transcription = transcribe_audio(audio_path, model_name=model_name)
    except Exception as e:
        logger.error("Transcription failed: %s", e)
        return {"error": f"Transcription failed: {e}"}

    logger.info("Transcription complete — detected language: %s", transcription)

    # Stage 2: Processing
    logger.info("Stage 2/2: Processing transcription")
    try:
        summary = build_summary(transcription)
    except Exception as e:
        logger.error("Processing failed: %s", e)
        return {"error": f"Processing failed: {e}"}

    elapsed = time.time() - start_time
    summary["pipeline_duration_seconds"] = round(elapsed, 2)
    logger.info("Pipeline complete in %.2f seconds", elapsed)

    return summary
