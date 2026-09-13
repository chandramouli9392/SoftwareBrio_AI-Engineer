# Quickstart

DAVE turns URLs into validated structured data. You can use a natural language prompt, a Pydantic schema, a built-in recipe, or no prompt at all.

## Install

```bash
pip install dave-ai
```

Install the Playwright extra when you need JavaScript rendering.

```bash
pip install "dave-ai[playwright]"
python -m playwright install chromium
```

## Zero-config extraction

```python
import dave

result = await dave.extract("https://example.com")
print(result)
```

Zero-config mode infers useful structure such as title, summary, key facts, links, contacts, products, prices, jobs, and calls to action.

## Prompt extraction

```python
import dave

result = await dave.extract("https://example.com", "get the title and description")
print(result)
```

## Recipe extraction

```python
import dave

company = await dave.recipes.company_info("https://example.com")
pricing = await dave.recipes.pricing("https://example.com/pricing")
```

The same recipes are available from the CLI.

```bash
dave extract "https://example.com" --recipe company_info
dave extract "https://example.com/pricing" --recipe pricing
```

## Pydantic extraction

```python
from pydantic import BaseModel, Field
import dave

class Product(BaseModel):
    name: str
    description: str | None = None
    features: list[str] = Field(default_factory=list)

product = await dave.extract("https://example.com", Product)
print(product.model_dump())
```

## Streaming

```bash
dave extract "https://example.com" --recipe company_info --stream
```

```python
from dave.core.engine import DaveEngine

engine = DaveEngine()
async for event in engine.stream_extract("https://example.com"):
    print(event.type, event.message, event.data)
```

## Batch mode

```bash
dave batch urls.txt --recipe pricing --output results.json
```

`urls.txt` should contain one URL per line. DAVE reports progress, retries failures, tracks cost, and writes JSON output.
