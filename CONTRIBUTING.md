# Contributing to DAVE

Thanks for helping improve DAVE. This project aims to be a production-grade AI scraping library with excellent developer experience.

## Development setup

```bash
git clone https://github.com/workwithlos-ui/dave.git
cd dave
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Standards

All code should be typed, documented, and covered by tests. Public APIs should stay small and obvious. Production behavior should be explicit, observable, and easy to configure.

## Pull requests

Open an issue before major architecture changes. Keep pull requests focused and include tests for new behavior.
