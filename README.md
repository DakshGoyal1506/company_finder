
## Architecture Overview

1️⃣ **QueryGenerator** (`query_generator.py`)  
- **Goal:** Turn a raw input pair (industry, location) into 5–10 high-quality Google search queries.  
- **Key Methods:**  
  - `_tokenize(text: str) → List[str]`  
    Normalize, remove punctuation, lowercase, strip stopwords (NLTK).  
  - `_expand(tokens: Sequence[str]) → List[str]`  
    Embed tokens and a small candidate list via Sentence-Transformers (all-MiniLM-L6-v2), compute cosine similarity, pick top semantic neighbours + original tokens.  
  - `_compose_prompts(synonyms, city) → List[str]`  
    Templates like `{syn} companies in {city}`, `top {syn} startups near {city}`.  
  - `_rank(prompts, intent, top_k) → List[str]`  
    Embed each prompt + intent phrase, rank by cosine similarity, return top k.  
- **Why These Tools:**  
  - NLTK stopwords: simple, standard for English  
  - all-MiniLM-L6-v2: lightweight (~20 MB), fast CPU/GPU inference, good semantic quality  
  - Cosine similarity + templates: inexpensive fallback if no large LLM  

2️⃣ **SearchClient** (`search_client.py`)  
- **Goal:** Given a list of queries, asynchronously fetch search-engine results (default SerpAPI) and collect unique URLs.  
- **Key Functions:**  
  - `_fetch(session, query) → List[str]`  
    `aiohttp` GET to `https://serpapi.com/search.json` with `api_key`, returns `organic_results[].link`.  
  - `search(queries) → List[str]`  
    Fire off parallel `_fetch` tasks under a single `ClientSession`; flatten & dedupe URLs.  
- **Why These Tools:**  
  - `aiohttp`: scalable async HTTP client in Python  
  - SerpAPI: removes need to scrape Google directly, handles CAPTCHA  
  - Early de-duplication ensures we don’t re-scrape the same URL  

3️⃣ **PageScraper** (`page_scraper.py`)  
- **Goal:** Download page HTML concurrently, strip boilerplate, return cleaned plain text.  
- **Key Methods:**  
  - `_fetch(session, url) → str`  
    Guarded by an `asyncio.Semaphore` for concurrency limits, 15 s timeout, checks `Content-Type`.  
  - `_clean(html: str) → str`  
    `BeautifulSoup` to remove `<script>`, `<style>`, `<header>`, etc., then collapse whitespace.  
  - `scrape(urls) → Dict[url, text]`  
    Launch all `_fetch` tasks, pair HTML with URLs, filter out empty.  
- **Why These Tools:**  
  - `BeautifulSoup`: robust HTML parsing  
  - Async & semaphore: controls parallelism, prevents resource overload  
  - Clean text allows downstream NLP to focus on actual content  

4️⃣ **InfoExtractor** (`info_extractor.py`)  
- **Goal:** From raw page text, extract structured details into `CompanyRecord` instances.  
- **Workflow:**  
  - **NER**  
    `transformers.pipeline("ner", model="dslim/bert-base-NER")` to find `ORG` & `LOC` entities in first 20000 chars.  
  - **Heuristics**  
    - Take first `ORG` as company name  
    - Regex for 6-digit PIN code → snippet for address  
    - Regex for phone & email  
  - **Industry Scoring**  
    `zero-shot-classification` with `facebook/bart-large-mnli`, input: first 10000 chars, candidate: the input industry → `score[0]`.  
- **Why These Models:**  
  - `dslim/bert-base-NER`: pre-trained on CoNLL-2003, good ORG/LOC accuracy  
  - `bart-large-mnli`: SOTA zero-shot classification, maps any text to a candidate label without fine-tuning  
  - Regex fallback: catches simple patterns for contacts/pins  

5️⃣ **Deduplicator** (`deduplicator.py`)  
- **Goal:** Merge multiple records that refer to the same company.  
- **Steps:**  
  1. **Vectorize**  
     Embed `"name address"` with all-MiniLM-L6-v2 for every record.  
  2. **Cluster**  
     `HDBSCAN` (`min_cluster_size=2`, `euclidean`) assigns cluster labels.  
  3. **Merge**  
     - Label = -1 → outlier: keep as is  
     - Non-negative label → group: pick record with highest `industry_score`, fill in missing `phone`/`email`/`address` from siblings  
- **Why HDBSCAN?**  
  - Doesn’t require pre-defining number of clusters  
  - Robust to noise (outliers)  
  - Handles variable cluster densities  

6️⃣ **Enricher** (`enricher.py`)  
- **Goal:** Fill missing fields (`address`, `phone`, `website`) via Google Places or fallback to OpenStreetMap/Nominatim.  
- **Modes:**  
  - **Google** (if `GOOGLE_PLACES_KEY` provided)  
    `findplacefromtext` API → `formatted_address`, `phone`, `website`  
  - **Nominatim** (no key)  
    Public search endpoint → `display_name` as address, OSM link as website  
- **Why This Approach:**  
  - Google Places offers high-quality, up-to-date company info  
  - Nominatim is free, no signup, generous rate limits for modest usage  
  - Async ensures we don’t block on dozens of HTTP calls  

7️⃣ **OutputWriter** (`output_writer.py`)  
- **Goal:** Serialize final `CompanyRecord` list into user‐facing formats and print a CLI table.  
- **Features:**  
  - `to_dataframe(...)` → `pandas.DataFrame`  
  - `save_csv`, `save_excel`, `save_json`  
  - `print_pretty(...)` → `rich.Table` with columns (`name`, `address`, `phone`, `email`, `website`)  
  - CLI echo of record count & output path  
- **Why These Tools:**  
  - `pandas`: industry-standard for tabular exports  
  - `rich`: visually appealing, readable console tables  
  - JSON for API integration  

**Orchestrator** (`orchestrator.py`)  
- **Role:** Glue logic—runs each step in order, wiring outputs to inputs:  
  - `_run_async(...)`: core async flow  
  - `run(...)`: wraps with `asyncio.run` for sync CLI usage  
