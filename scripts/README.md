# Ghost Bot — Scripts

Manual run scripts for one-off and maintenance tasks. Always run from the project root using `uv run`.

---

## backfill_rag.py

Backfill the RAG pipeline with historical Discord messages.

```bash
# Ingest a specific month from a channel
uv run scripts/backfill_rag.py --channel 1234567890 --start 2026-04-01 --end 2026-04-30

# Dry run — counts qualifying messages without calling any LLM or writing to MongoDB
uv run scripts/backfill_rag.py --channel 1234567890 --start 2026-01-01 --end 2026-04-30 --dry-run

# Large bulk load — skip arc summary triggers (run them manually after all chunks are in)
uv run scripts/backfill_rag.py --channel 1234567890 --start 2025-01-01 --end 2026-04-30 --skip-arc-summaries

# Custom batch size — process 14 days per batch instead of 7
uv run scripts/backfill_rag.py --channel 1234567890 --start 2026-01-01 --end 2026-04-30 --batch-days 14
```

**Prerequisites:**
- `DISCORD_TOKEN`, `GEMINI_API_KEY`, `MONGODB_URI` set in `.env`
- Ollama running: `ollama serve && ollama pull nomic-embed-large`
- Atlas Vector Search index `rag_vector_index` created (1024 dims, cosine)

**Options:**

| Flag | Default | Description |
|---|---|---|
| `--channel` | required | Discord channel ID |
| `--start` | required | Start date (YYYY-MM-DD, inclusive) |
| `--end` | required | End date (YYYY-MM-DD, inclusive) |
| `--batch-days` | `7` | Days per processing batch |
| `--dry-run` | false | Fetch and segment only, no LLM or storage |
| `--skip-arc-summaries` | false | Skip arc summary triggers after ingestion |
| `--force` | false | Ignore deduplication (re-process already-ingested IDs) |

**Notes:**
- Deduplication is active by default — re-running the same date range is safe, already-ingested segments are skipped
- For very large backfills (months/years), use `--skip-arc-summaries` and trigger arc summaries manually once the bulk load is done
- The `--dry-run` flag is useful to estimate how much content will be processed before committing to a long run
