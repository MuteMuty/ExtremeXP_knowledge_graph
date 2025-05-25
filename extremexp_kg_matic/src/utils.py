import re

def sanitize_for_uri(text):
    """
    Sanitizes a string to be used as part of a URI.
    Replaces spaces and special characters with underscores.
    """
    if not text:
        return "unknown"
    # Remove special characters, replace spaces with underscores
    text = re.sub(r'[^\w\s-]', '', str(text).strip()) # Keep alphanumeric, whitespace, hyphen
    text = re.sub(r'[-\s]+', '_', text) # Replace one or more hyphens/spaces with a single underscore
    return text if text else "sanitized_empty"

def get_year_from_pdf_url(pdf_url):
    """
    Attempts to extract a 4-digit year from a PDF URL (e.g., arXiv format).
    This is a basic attempt and might need refinement.
    Example: https://arxiv.org/pdf/2103.14030v2.pdf -> 21
    We assume it's 20xx.
    """
    match = re.search(r'/(\d{2})(\d{2})\.\d+.*\.pdf$', pdf_url)
    if match:
        year_prefix = match.group(1)
        # Rudimentary check if it's a plausible arXiv year (e.g., 19xx, 20xx)
        if year_prefix.startswith('1') or year_prefix.startswith('2'):
            return int("20" + year_prefix) # Assuming 21st century for YYMM format
    match_yyyy = re.search(r'/(\d{4})[^/]*\.pdf$', pdf_url) # Try to find YYYY
    if match_yyyy:
        return int(match_yyyy.group(1))
    return None # Or a default if not found
