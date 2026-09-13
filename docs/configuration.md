# Configuration

DAVE is configured through `DaveConfig`, nested config models, or environment variables.

| Setting | Purpose | Default |
| --- | --- | --- |
| `fetcher` | Selects `auto`, `http`, or `playwright` | `auto` |
| `retries` | Fetch retries with exponential backoff | `2` |
| `min_confidence` | Required extraction confidence | `0.65` |
| `chunk_size_chars` | Page chunk size before LLM calls | `12000` |
| `cache.enabled` | Enables SQLite cache | `true` |
| `rate_limit.requests_per_minute` | Per-domain request budget | `30` |

```python
from dave import DaveConfig, DaveEngine
from dave.core.config import LLMConfig

config = DaveConfig(
    fetcher="http",
    llm=LLMConfig(provider="ollama", model="llama3.1", base_url="http://localhost:11434"),
)
engine = DaveEngine(config=config)
```
