import re
from datetime import datetime

def normalize(conversation: dict) -> dict:
    turns = conversation.get("turns", [])
    normalized = []
    for t in turns:
        speaker = t.get("speaker", "customer").lower()
        text = re.sub(r"\s+", " ", t.get("text", "")).strip()
        normalized.append({"speaker": speaker, "text": text, "ts": t.get("ts")})
    return {"turns": normalized, "meta": conversation.get("meta", {})}


def segment(conv: dict) -> list[dict]:
    """Split into issue segments using discourse markers."""
    markers = ["also", "separately", "another thing", "unrelated", "additionally"]
    segments, current = [], []
    for t in conv["turns"]:
        if t["speaker"] == "customer":
            low = t["text"].lower()
            if any(low.startswith(m) for m in markers) and current:
                segments.append({"turns": current})
                current = []
            current.append(t)
        else:
            current.append(t)
    if current:
        segments.append({"turns": current})
    return segments