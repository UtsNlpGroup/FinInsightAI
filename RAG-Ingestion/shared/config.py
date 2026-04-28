# Environment variable key names
CHROMA_HOST_KEY = "CHROMA_HOST"
CF_CLIENT_ID_KEY = "CF_ACCESS_CLIENT_ID"
CF_CLIENT_SECRET_KEY = "CF_ACCESS_CLIENT_SECRET"

# Supabase env var keys
SUPABASE_URL_KEY = "SUPABASE_URL"
SUPABASE_KEY_KEY = "SUPABASE_KEY"

# Chroma connection defaults
DEFAULT_CHROMA_PORT = 443
DEFAULT_CHROMA_SSL = True

# 10-K chunking defaults
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200

# News chunking defaults
# Smaller chunks keep each piece focused on a single idea/fact, reducing the
# chance that one long article becomes a single wall-of-text chunk.
# Overlap of 100 chars (~2-3 sentences) preserves cross-boundary context.
DEFAULT_NEWS_CHUNK_SIZE = 500
DEFAULT_NEWS_CHUNK_OVERLAP = 100

# 10-K collections (one per embedding backend)
DEFAULT_10K_COLLECTION = "sec_filings"           # legacy name kept for compat
DEFAULT_10K_COLLECTION_CHROMA = "sec_filings_chroma"
DEFAULT_10K_COLLECTION_OPENAI = "sec_filings_openai"

# FinBERT sentiment model (news ingestion)
DEFAULT_FINBERT_MODEL = "ProsusAI/finbert"
FINBERT_MAX_LENGTH = 512

# News collections (one per embedding backend)
DEFAULT_NEWS_COLLECTION = "news"                  # legacy name kept for compat
DEFAULT_NEWS_COLLECTION_CHROMA = "news_chroma"
DEFAULT_NEWS_COLLECTION_OPENAI = "news_openai"

# News fetching defaults
DEFAULT_NEWS_COUNT = 25

# News scraper defaults
DEFAULT_SCRAPE_TIMEOUT = 10
DEFAULT_MIN_ARTICLE_CHARS = 400
DEFAULT_MIN_SUMMARY_CHARS = 60
DEFAULT_RATE_LIMIT_SLEEP = 0.5
