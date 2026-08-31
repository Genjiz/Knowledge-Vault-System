
# ScienceDirect / Foreign Crawler Configuration

BASE_URL = "https://www.sciencedirect.com"

# Headers for requests
# Using a browser-like User-Agent
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
}

# Journal Name Slug Mapping
# Maps user-friendly name to ScienceDirect URL slug
JOURNAL_SLUGS = {
    "Information Processing & Management": "information-processing-and-management",
    "Journal of Informetrics": "journal-of-informetrics",
    "IP&M": "information-processing-and-management",
    "JOI": "journal-of-informetrics"
}

# Data Storage
DATA_DIR = "."  # Root directory as per user rule
