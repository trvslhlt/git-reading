# Git Reading Q&A

A lightweight CLI that scans a git repository's tracked files and recent history, then lets you search for relevant snippets using keyword-style questions.

## Features

- Loads the current contents of every tracked file (with optional byte limits).
- Captures recent commit summaries and truncated patches for added historical context.
- Uses a simple TF-IDF retrieval engine to surface relevant snippets from files and commits.
- Supports one-off questions or an interactive shell.

## Usage

```bash
python -m repo_reader.cli --repo /path/to/repo "Where are database migrations created?"
```

Or start an interactive session:

```bash
python -m repo_reader.cli --repo /path/to/repo --interactive
```

Adjust `--max-commits`, `--max-file-bytes`, and `--limit` to control how much history is scanned and how many answers are returned.

## Implementation Notes

- Relies only on Python's standard library plus the system `git` executable.
- Treats each file in chunks of ~120 lines to improve answer granularity.
- Uses a simple TF-IDF cosine similarity to rank results; it does not perform true natural-language reasoning, but provides helpful starting points for developer exploration.
