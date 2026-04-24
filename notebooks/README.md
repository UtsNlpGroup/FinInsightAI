# Financial News Sentiment Notebook

This notebook builds an end-to-end workflow for collecting, cleaning, storing, and analysing financial news sentiment for a small set of stocks.

It connects to a remote ChromaDB instance, discovers recent market news from Yahoo Finance, verifies article content from source pages, splits text into analysis-friendly chunks, stores the data in vector collections, and runs FinBERT to produce sentiment scores.

## Purpose

The goal of the notebook is to create a reusable news-processing pipeline that can support:

- stock sentiment monitoring
- retrieval-augmented financial analysis
- downstream charting or modelling
- experimentation with news quality filtering and text chunking strategies

## Stocks Covered

The notebook currently focuses on:

- **NVDA** — Nvidia
- **TSLA** — Tesla
- **AAPL** — Apple

These are used as the primary discovery targets for recent news ingestion.

## Workflow Overview

The notebook follows this sequence:

1. Load local environment variables
2. Connect to ChromaDB over HTTP
3. Create or reset the vector collections
4. Discover news articles for the selected tickers
5. Verify article relevance and extract clean article text
6. Fall back to summaries or headline-derived text when needed
7. Chunk documents into smaller analysis units
8. Store chunks and metadata in ChromaDB
9. Load the FinBERT sentiment model
10. Batch-score all stored chunks
11. Build a time-ordered pandas DataFrame for downstream use

## Data Sources

The notebook uses:

- **Yahoo Finance news search** for article discovery
- **Article pages fetched via HTTP** for content extraction
- **ChromaDB** for persistent vector storage
- **FinBERT** for financial sentiment classification

## Key Components

### 1. Environment and Connection Setup

The notebook reads configuration from a `.env` file and uses it to connect to a remote ChromaDB instance. This allows the notebook to work with a hosted vector database rather than a local-only store.

### 2. ChromaDB Collections

Two collections are used:

- `stream1_fundamentals`
- `stream2_sentiment`

The sentiment collection is the main focus of the notebook. It stores chunked news text along with metadata such as ticker, title, source, published time, and chunk position.

### 3. News Discovery

For each ticker, the notebook searches multiple Yahoo Finance queries to build a unified pool of recent articles. This reduces duplicate discovery and broadens coverage of relevant news.

### 4. Article Verification and Cleaning

The notebook does not blindly trust every news result. It applies filtering logic to ensure that the content is actually about the target company and not an unrelated article that only mentions the ticker briefly.

The verification process aims to:

- remove noisy page elements
- confirm relevance through title and text density
- avoid appended “read next” or related-story sections
- discard weak or very short content

### 5. Fallback Document Strategy

Not every article yields clean full text. Some are paywalled, partially empty, or only expose a summary.

To keep coverage broad, the notebook uses a three-tier ingestion strategy:

- **Full text** when available
- **Summary text** when the full article is unavailable
- **Synthetic headline text** when only minimal data is accessible

This ensures the pipeline still creates usable embeddings even when source articles are incomplete.

### 6. Chunking Strategy

The notebook uses sentence-aware chunking to preserve local context while still producing smaller units suitable for retrieval and sentiment analysis.

The chunking approach is specifically designed around a **sliding sentence window**:

- sentences are first split using a financial-aware sentence segmenter
- only sentences with enough textual content are kept
- overlapping chunks are then built by taking a moving window across adjacent sentences
- the default window size is **2 sentences**
- this means each chunk shares one sentence with the next chunk, creating overlap and preserving continuity across boundaries

This overlap is important because financial articles often have meaning that spans sentence boundaries. The overlapping design helps reduce context loss and improves both retrieval quality and sentiment classification consistency.

In practical terms, the sentence overlap provides:

- better local context for FinBERT
- smoother transitions between chunks
- more robust embeddings for article retrieval
- higher effective data density from each article

For shorter articles, the notebook falls back to using the available text or headline so that nothing is dropped unnecessarily.

Chunk metadata is preserved so each piece of text can be traced back to the original article.

### 7. Sentiment Analysis with FinBERT

The notebook loads **ProsusAI/finbert**, a finance-oriented transformer model, and applies it to the stored chunks in batches.

The resulting sentiment score is derived from the model’s positive and negative probabilities, producing a simple compound score that can be interpreted as:

- **positive**: bullish tone
- **negative**: bearish tone
- **near zero**: neutral or mixed tone

### 8. Output DataFrame

After scoring, the notebook assembles a pandas DataFrame containing:

- timestamp
- ticker
- sentiment score
- short text preview

The DataFrame is sorted chronologically so it can be aligned with price data, event timelines, or visualisations.

## Outputs Produced

Running the notebook typically produces:

- populated ChromaDB collections
- chunk-level document records
- article metadata linked to each chunk
- sentiment scores for all processed text
- a sorted DataFrame for further analysis
- useful console logs showing article counts and ingestion quality

## Why This Notebook Exists

This notebook is designed to bridge the gap between raw financial news and usable sentiment signals.

Instead of analysing headlines in isolation, it:

- gathers broader article context
- filters for relevance
- preserves sentence-level meaning
- stores reusable vectorised text
- generates structured sentiment output

That makes it more useful for both research and application development.

## Requirements

The notebook depends on the following Python packages:

- `chromadb`
- `python-dotenv`
- `yfinance`
- `beautifulsoup4`
- `requests`
- `time`
- `langchain-text-splitters`
- `pysbd`
- `transformers`
- `torch`
- `pandas`

## Environment Setup

The notebook expects a local `.env` file containing the ChromaDB connection details.

Typical values include:

- Chroma access credentials
- Chroma service URL

Keep this file private and do not commit it to version control.

## Recommended Execution Order

To run the notebook successfully, execute the cells in order:

1. imports
2. environment loading
3. ChromaDB connection
4. collection creation
5. stock list definition
6. article discovery and verification helpers
7. chunking helpers
8. bulk ingestion into ChromaDB
9. FinBERT loading
10. batch sentiment inference
11. final DataFrame inspection

## Notes and Limitations

- The notebook is intended as a research and prototype workflow.
- Some articles may be excluded if the content quality is too low.
- Paywalled pages may only contribute headline-based synthetic records.
- FinBERT is used without additional fine-tuning.
- The score is a lightweight proxy for sentiment and should not be treated as a complete market model.

## Potential Extensions

This notebook could be extended by adding:

- price history joins
- rolling sentiment averages
- per-source reliability scoring
- visual dashboards
- alerting for strong positive or negative shifts
- more tickers or sector-based tracking
- better deduplication across repeated syndications

## Summary

This notebook creates a complete financial news sentiment pipeline:

- discover news
- verify content
- chunk text with overlapping sentence windows
- store in ChromaDB
- classify with FinBERT
- prepare structured sentiment output

It is useful as a foundation for financial NLP experiments, portfolio research, and sentiment-aware market analysis.