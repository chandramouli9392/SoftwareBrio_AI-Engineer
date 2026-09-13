"""Async job queue for batch extraction."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class Job:
    """A queued extraction job."""

    url: str
    schema_or_prompt: Any
    prompt: str | None = None
    id: str = field(default_factory=lambda: uuid4().hex)


@dataclass(slots=True)
class JobResult:
    """Result for a completed job."""

    job_id: str
    url: str
    ok: bool
    data: Any = None
    error: str | None = None
    finished_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class JobQueue:
    """Run extraction jobs with bounded concurrency."""

    def __init__(self, concurrency: int = 5) -> None:
        if concurrency < 1:
            raise ValueError("concurrency must be at least 1")
        self.concurrency = concurrency
        self.jobs: list[Job] = []

    def add(self, job: Job) -> None:
        """Add a job to the queue."""
        self.jobs.append(job)

    async def run(self, worker: Callable[[Job], Awaitable[Any]]) -> list[JobResult]:
        """Run all jobs and return ordered results."""
        semaphore = asyncio.Semaphore(self.concurrency)

        async def _run_one(job: Job) -> JobResult:
            async with semaphore:
                try:
                    data = await worker(job)
                    return JobResult(job_id=job.id, url=job.url, ok=True, data=data)
                except Exception as exc:
                    return JobResult(job_id=job.id, url=job.url, ok=False, error=str(exc))

        return await asyncio.gather(*(_run_one(job) for job in self.jobs))
