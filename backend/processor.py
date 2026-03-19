
import re
from collections import Counter

"""This is the post-processing logic for transcription output."""

def clean_text(text: str) -> str:

    # Collapse multiple whitespace into single spaces
    text = re.sub(r"\s+", " ", text).strip()

    # Ensure the text starts with an uppercase letter
    if text:
        text = text[0].upper() + text[1:]

    # Ensure the text ends with a period if it doesn't end with punctuation
    if text and text[-1] not in ".!?":
        text += "."

    return text



def build_summary(transcription_result: dict) -> dict:

    raw_text = transcription_result.get("text", "")
    cleaned = clean_text(raw_text)
    words = cleaned.split()

    return {
        "cleaned_text": cleaned,
        "word_count": len(words),
        "language": transcription_result.get("language", "unknown"),
        "segment_count": len(transcription_result.get("segments", [])),
        "metadata": {
            "raw_text": raw_text,
            "segments": transcription_result.get("segments", []),
        },
    }
