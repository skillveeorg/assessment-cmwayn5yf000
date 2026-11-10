# Halden Mutual pilot

This repository is nearly empty on purpose. What gets built here depends on what you learn from Marit.

## What's here

| Path | What it is |
|---|---|
| `compressor/stub.py` | A stand-in for our compressor. Same call as the real tool, but it finishes in seconds. Treat it as a black box and don't change it. You don't need to know how compression works. |
| `sample_models/` | Three placeholder model files to run it on. |
| `tests/test_stub.py` | Tests for the stand-in, so you can see how it behaves. |

## Getting started

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Python and Docker are what we normally ship, but use whatever framework or libraries you think fit.

## Working with your coding agent

Use whichever coding agent or LLM you normally work with. We expect it to write most of the code. What we're looking at is how you direct it and what you do with its output.

Keep your session: at the end you'll upload an export of it (a `.md` or `.txt` file). If your tool can't export, copy the conversation into a text file.

## Handing in

Open a Pull Request. In the description, say:

- what you built
- what you left out
- anything you assumed instead of asking
