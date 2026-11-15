"""Conservative English paragraph/sentence segmentation for the tested model."""
import re

ABBREVIATIONS = {"mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "vs", "etc", "no", "fig", "inc"}
BOUNDARY = re.compile(r'''[.!?]+["'”’)\]]*(?:\s+|$)''')


def sentences(paragraph):
    start = 0
    for match in BOUNDARY.finditer(paragraph):
        end = match.end()
        prefix = paragraph[:match.start()+1]
        if paragraph[match.start()] == ".":
            token = prefix.split()[-1].strip('"“(‘')
            if token[:-1].lower() in ABBREVIATIONS or re.search(r"(?:[A-Za-z]\.){2,}$", token) or re.fullmatch(r"[A-Z]\.", token):
                continue
        yield paragraph[start:end].strip()
        start = end
    if paragraph[start:].strip():
        yield paragraph[start:].strip()


def segment_text(text, max_chars=350):
    if max_chars < 20:
        raise ValueError("Segment size must be at least 20 characters.")
    if not text.strip() or not any(c.isalnum() for c in text):
        raise ValueError("Enter a script containing letters or numbers.")
    result = []
    for paragraph in re.split(r"\n\s*\n", text.replace("\r\n", "\n").strip()):
        paragraph = re.sub(r"\s+", " ", paragraph).strip()
        current = ""
        for sentence in sentences(paragraph):
            pieces = []
            while len(sentence) > max_chars:
                cut = sentence.rfind(" ", 0, max_chars + 1)
                if cut <= 0:
                    cut = max_chars
                pieces.append(sentence[:cut].strip())
                sentence = sentence[cut:].strip()
            if sentence:
                pieces.append(sentence)
            for piece in pieces:
                if current and len(current) + len(piece) + 1 > max_chars:
                    result.append(current)
                    current = ""
                current = f"{current} {piece}".strip()
        if current:
            result.append(current)
    return result
