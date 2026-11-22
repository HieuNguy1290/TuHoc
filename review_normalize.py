"""Shared Unicode-aware answer comparison for review and grading."""
import re
import unicodedata

def normalize(value):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC',str(value)).casefold().strip())
