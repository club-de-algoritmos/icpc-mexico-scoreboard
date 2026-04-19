_NORMALIZED_CHARS = {
    "á": "a",
    "é": "e",
    "í": "i",
    "ó": "o",
    "ú": "u",
    "ñ": "n",
}

def normalize(string: str) -> str:
    s = string.strip().lower()
    for char, normalized_char in _NORMALIZED_CHARS.items():
        s = s.replace(char, normalized_char)
    return s
