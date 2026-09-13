# Production Guide

DAVE is built around production concerns that are usually bolted on later.

| Concern | DAVE capability |
| --- | --- |
| Reliability | Retries with exponential backoff |
| Cost control | Token usage and estimated cost tracking |
| Rate limits | Per-domain request pacing |
| Repeatability | Response caching |
| Quality | Pydantic validation, confidence scoring, source evidence |
| Monitoring | Diff detection between extraction runs |

DAVE detects CAPTCHAs and raises a clear error. It does not solve CAPTCHAs or bypass access controls.
