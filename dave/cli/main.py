"""CLI entry point for DAVE."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Annotated, Any

import typer
from rich import box
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.prompt import Confirm
from rich.table import Table

from dave import recipes
from dave.core.config import DaveConfig, LLMConfig
from dave.core.engine import DaveEngine, DaveExtraction

app = typer.Typer(help="DAVE, Data Acquisition and Validation Engine", no_args_is_help=True)
console = Console()


@app.callback()
def callback() -> None:
    """DAVE command line tools."""


def _make_engine(provider: str, model: str, fetcher: str) -> DaveEngine:
    if fetcher == "stealth":
        from dave.fetchers.stealth import register_stealth_fetcher

        register_stealth_fetcher()
    config = DaveConfig(fetcher=fetcher, llm=LLMConfig(provider=provider, model=model))
    return DaveEngine(config=config)


def _schema_and_prompt(recipe: str | None, prompt: str | None) -> tuple[type[Any] | str | None, str | None]:
    if recipe:
        schema, recipe_prompt = recipes.get_recipe(recipe)
        return schema, prompt or recipe_prompt
    return prompt, None


def _jsonable(value: Any) -> Any:
    if isinstance(value, DaveExtraction):
        return json.loads(DaveEngine.to_json(value))
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


def _render_payload(payload: Any, *, title: str = "DAVE Extraction") -> None:
    payload = _jsonable(payload)
    if isinstance(payload, dict) and "data" in payload and isinstance(payload["data"], dict):
        data = payload["data"]
        meta = {key: value for key, value in payload.items() if key != "data"}
    elif isinstance(payload, dict):
        data = payload
        meta = {}
    else:
        data = {"result": payload}
        meta = {}

    table = Table(title=title, box=box.ROUNDED, show_lines=True)
    table.add_column("Field", style="bold cyan", no_wrap=True)
    table.add_column("Value", style="white")
    for key, value in data.items():
        table.add_row(str(key), json.dumps(value, indent=2, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value))
    console.print(table)

    if meta:
        meta_table = Table(title="Run Metadata", box=box.SIMPLE)
        meta_table.add_column("Metric", style="bold magenta")
        meta_table.add_column("Value")
        for key in ("confidence", "cost_usd", "fetcher", "final_url"):
            if key in meta:
                meta_table.add_row(key, str(meta[key]))
        console.print(meta_table)


def _render_json(payload: Any) -> None:
    console.print(JSON(json.dumps(_jsonable(payload), ensure_ascii=False)))


async def _confirm_estimate(
    engine: DaveEngine,
    url: str,
    schema_or_prompt: type[Any] | str | None,
    prompt: str | None,
    yes: bool,
) -> None:
    with console.status("Estimating token and cost budget...", spinner="dots"):
        estimate = await engine.estimate_cost(url, schema_or_prompt, prompt=prompt)
    console.print(
        Panel.fit(
            f"This extraction will use about [bold]{estimate.total_tokens:,} tokens[/bold] "
            f"for roughly [bold green]${estimate.cost_usd:.6f}[/bold green].",
            title="Cost estimate",
            border_style="green",
        )
    )
    if yes or not sys.stdin.isatty():
        return
    if not Confirm.ask("Proceed?", default=True):
        raise typer.Abort()


@app.command("extract")
def extract(
    url: Annotated[str, typer.Argument(help="URL to extract from")],
    prompt: Annotated[str | None, typer.Option("--prompt", "-p", help="Natural language extraction prompt")] = None,
    recipe: Annotated[str | None, typer.Option("--recipe", "-r", help="Built-in recipe name")] = None,
    provider: Annotated[str, typer.Option("--provider", help="LLM provider: openai, anthropic, gemini, groq, mistral, ollama, mock")] = "mock",
    model: Annotated[str, typer.Option("--model", help="Model name")] = "mock",
    fetcher: Annotated[str, typer.Option("--fetcher", help="Fetcher: auto, http, playwright, or plugin name")] = "auto",
    output: Annotated[str, typer.Option("--output", "-o", help="Output format: rich or json")] = "rich",
    metadata: Annotated[bool, typer.Option("--metadata", help="Include confidence, evidence, and cost metadata")] = True,
    stream: Annotated[bool, typer.Option("--stream/--no-stream", help="Stream fields as they are extracted")] = True,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip interactive cost confirmation")] = False,
) -> None:
    """Extract structured data from a URL.

    Omit prompt and recipe to activate zero-config magic.
    """

    async def run() -> None:
        engine = _make_engine(provider, model, fetcher)
        schema_or_prompt, resolved_prompt = _schema_and_prompt(recipe, prompt)
        await _confirm_estimate(engine, url, schema_or_prompt, resolved_prompt, yes)
        if output == "json":
            result = await engine.extract(url, schema_or_prompt, prompt=resolved_prompt, include_metadata=metadata)
            _render_json(result)
            return

        console.print(Panel.fit("DAVE is extracting structured data", title="Data Acquisition and Validation Engine"))
        if stream:
            final_payload: Any = None
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("Starting", total=None)
                async for event in engine.stream_extract(url, schema_or_prompt, prompt=resolved_prompt):
                    progress.update(task, description=event.message)
                    if event.type == "field":
                        console.print(f"[cyan]field[/cyan] [bold]{event.data['field']}[/bold] = {event.data['value']}")
                    if event.type == "complete":
                        final_payload = DaveExtraction(
                            data=event.data["data"],
                            confidence=float(event.data["confidence"]),
                            field_confidence={},
                            evidence=event.data.get("evidence", {}),
                            cost_usd=float(event.data["cost_usd"]),
                            fetcher=fetcher,
                            final_url=url,
                        )
            _render_payload(final_payload, title=f"DAVE Extraction: {recipe or 'zero_config'}")
        else:
            result = await engine.extract(url, schema_or_prompt, prompt=resolved_prompt, include_metadata=metadata)
            _render_payload(result, title=f"DAVE Extraction: {recipe or 'custom'}")

    asyncio.run(run())


@app.command("batch")
def batch(
    urls_file: Annotated[Path, typer.Argument(help="Text file with one URL per line")],
    recipe: Annotated[str | None, typer.Option("--recipe", "-r", help="Built-in recipe name")] = None,
    prompt: Annotated[str | None, typer.Option("--prompt", "-p", help="Natural language extraction prompt")] = None,
    output: Annotated[Path, typer.Option("--output", "-o", help="JSON output file")] = Path("results.json"),
    provider: Annotated[str, typer.Option("--provider", help="LLM provider: openai, anthropic, gemini, groq, mistral, ollama, mock")] = "mock",
    model: Annotated[str, typer.Option("--model", help="Model name")] = "mock",
    fetcher: Annotated[str, typer.Option("--fetcher", help="Fetcher: auto, http, playwright, or plugin name")] = "auto",
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip interactive cost confirmation")] = False,
) -> None:
    """Process hundreds of URLs with retries, cache, progress, and a cost summary."""

    async def run() -> None:
        urls = [line.strip() for line in urls_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not urls:
            raise typer.BadParameter("urls file is empty")
        engine = _make_engine(provider, model, fetcher)
        schema_or_prompt, resolved_prompt = _schema_and_prompt(recipe, prompt)
        total_estimated_cost = 0.0
        total_estimated_tokens = 0
        for url in urls[: min(5, len(urls))]:
            estimate = await engine.estimate_cost(url, schema_or_prompt, prompt=resolved_prompt)
            total_estimated_cost += estimate.cost_usd
            total_estimated_tokens += estimate.total_tokens
        if len(urls) > 5:
            total_estimated_cost = total_estimated_cost / min(5, len(urls)) * len(urls)
            total_estimated_tokens = int(total_estimated_tokens / min(5, len(urls)) * len(urls))
        console.print(
            Panel.fit(
                f"Batch size: [bold]{len(urls)} URLs[/bold]\n"
                f"Estimated usage: [bold]{total_estimated_tokens:,} tokens[/bold]\n"
                f"Estimated cost: [bold green]${total_estimated_cost:.6f}[/bold green]",
                title="Batch cost estimate",
                border_style="green",
            )
        )
        if not yes and sys.stdin.isatty() and not Confirm.ask("Proceed with batch?", default=True):
            raise typer.Abort()

        results: list[dict[str, Any]] = []
        total_actual_cost = 0.0
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Processing URLs", total=len(urls))
            for url in urls:
                try:
                    result = await engine.extract(url, schema_or_prompt, prompt=resolved_prompt, include_metadata=True)
                    payload = _jsonable(result)
                    total_actual_cost += float(payload.get("cost_usd", 0.0))
                    results.append({"url": url, "ok": True, "result": payload})
                except Exception as exc:
                    results.append({"url": url, "ok": False, "error": str(exc)})
                progress.advance(task)
        output.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        console.print(
            Panel.fit(
                f"Wrote [bold]{len(results)} results[/bold] to [bold]{output}[/bold]\n"
                f"Actual tracked model cost: [bold green]${total_actual_cost:.6f}[/bold green]",
                title="Batch complete",
                border_style="cyan",
            )
        )

    asyncio.run(run())


@app.command("search")
def search(
    query: Annotated[str, typer.Argument(help="Search query to run before extraction")],
    recipe: Annotated[str | None, typer.Option("--recipe", "-r", help="Built-in recipe name")] = None,
    prompt: Annotated[str | None, typer.Option("--prompt", "-p", help="Natural language extraction prompt")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Number of search results to extract")] = 5,
    search_provider: Annotated[str, typer.Option("--search-provider", help="Search provider: duckduckgo, mock, or plugin name")] = "duckduckgo",
    provider: Annotated[str, typer.Option("--provider", help="LLM provider: openai, anthropic, gemini, groq, mistral, ollama, mock")] = "mock",
    model: Annotated[str, typer.Option("--model", help="Model name")] = "mock",
    fetcher: Annotated[str, typer.Option("--fetcher", help="Fetcher: auto, http, playwright, or plugin name")] = "auto",
    output: Annotated[str, typer.Option("--output", "-o", help="Output format: rich or json")] = "rich",
) -> None:
    """Search the web, then extract structured data from each result.

    Combine with --recipe or --prompt to shape what is extracted from every hit.
    """

    async def run() -> None:
        engine = _make_engine(provider, model, fetcher)
        schema_or_prompt, resolved_prompt = _schema_and_prompt(recipe, prompt)
        with console.status(f"Searching '{query}' via {search_provider}...", spinner="dots"):
            report = await engine.search(
                query,
                schema_or_prompt,
                prompt=resolved_prompt,
                provider=search_provider,
                limit=limit,
                include_metadata=True,
            )

        if output == "json":
            console.print(JSON(json.dumps(report.to_dict(), ensure_ascii=False)))
            return

        console.print(
            Panel.fit(
                f"Query: [bold]{report.query}[/bold]\n"
                f"Provider: [bold]{report.provider}[/bold]\n"
                f"Results: [bold]{len(report.items)}[/bold]  Extracted: [bold green]{len(report.ok_items)}[/bold green]",
                title="DAVE Search",
                border_style="green",
            )
        )
        overview = Table(title="Search results", box=box.ROUNDED)
        overview.add_column("#", style="bold magenta", no_wrap=True)
        overview.add_column("Title", style="bold cyan")
        overview.add_column("URL", style="white")
        overview.add_column("Status", no_wrap=True)
        for item in report.items:
            status = "[green]ok[/green]" if item.ok else "[red]failed[/red]"
            overview.add_row(str(item.hit.rank), item.hit.title or "—", item.hit.url, status)
        console.print(overview)

        for item in report.ok_items:
            _render_payload(item.data, title=f"#{item.hit.rank} {item.hit.title or item.hit.url}")

    asyncio.run(run())


@app.command("crawl")
def crawl(
    start_url: Annotated[str, typer.Argument(help="URL to start crawling from")],
    recipe: Annotated[str | None, typer.Option("--recipe", "-r", help="Built-in recipe name")] = None,
    prompt: Annotated[str | None, typer.Option("--prompt", "-p", help="Natural language extraction prompt")] = None,
    max_pages: Annotated[int, typer.Option("--max-pages", help="Maximum pages to crawl")] = 10,
    max_depth: Annotated[int, typer.Option("--max-depth", help="Maximum link depth from the start URL")] = 2,
    same_domain: Annotated[bool, typer.Option("--same-domain/--any-domain", help="Restrict to the start URL's domain")] = True,
    provider: Annotated[str, typer.Option("--provider", help="LLM provider: openai, anthropic, gemini, groq, mistral, ollama, mock")] = "mock",
    model: Annotated[str, typer.Option("--model", help="Model name")] = "mock",
    fetcher: Annotated[str, typer.Option("--fetcher", help="Fetcher: auto, http, playwright, stealth, or plugin name")] = "auto",
    output: Annotated[str, typer.Option("--output", "-o", help="Output format: rich or json")] = "rich",
) -> None:
    """Crawl a site and extract structured data from every page."""

    async def run() -> None:
        engine = _make_engine(provider, model, fetcher)
        schema_or_prompt, resolved_prompt = _schema_and_prompt(recipe, prompt)
        with console.status(f"Crawling {start_url} (max {max_pages} pages, depth {max_depth})...", spinner="dots"):
            report = await engine.crawl(
                start_url, schema_or_prompt, prompt=resolved_prompt,
                max_pages=max_pages, max_depth=max_depth, same_domain=same_domain,
            )

        if output == "json":
            console.print(JSON(json.dumps(report.to_dict(), ensure_ascii=False)))
            return

        console.print(
            Panel.fit(
                f"Start: [bold]{report.start_url}[/bold]\n"
                f"Pages: [bold]{len(report.items)}[/bold]  Extracted: [bold green]{len(report.ok_items)}[/bold green]",
                title="DAVE Crawl", border_style="green",
            )
        )
        table = Table(title="Crawled pages", box=box.ROUNDED)
        table.add_column("Depth", style="bold magenta", no_wrap=True)
        table.add_column("URL", style="white")
        table.add_column("Status", no_wrap=True)
        for item in report.items:
            status = "[green]ok[/green]" if item.ok else "[red]failed[/red]"
            table.add_row(str(item.depth), item.url, status)
        console.print(table)

    asyncio.run(run())


@app.command("leads")
def leads(
    industry: Annotated[str, typer.Argument(help="Industry or business type, e.g. 'roofing companies'")],
    city: Annotated[str, typer.Argument(help="City, e.g. 'Dallas, TX'")],
    max_results: Annotated[int, typer.Option("--max", "-n", help="Max businesses to pull")] = 20,
    output: Annotated[str, typer.Option("--output", "-o", help="Output format: rich, csv, or json")] = "rich",
) -> None:
    """Find local businesses with phone numbers (a ready-to-dial list). Needs APIFY_API_KEY."""

    async def run() -> None:
        from dave.leads import find_leads

        with console.status(f"Pulling {industry} in {city} from Google Maps...", spinner="dots"):
            report = await find_leads(industry, city, max_results=max_results)

        if output == "json":
            console.print(JSON(json.dumps(report.to_dict(), ensure_ascii=False)))
            return
        if output == "csv":
            print(report.to_csv())
            return

        console.print(
            Panel.fit(
                f"[bold]{report.industry}[/bold] in [bold]{report.city}[/bold] — "
                f"[bold green]{len(report.leads)} businesses with phones[/bold green]",
                title="DAVE Leads", border_style="green",
            )
        )
        table = Table(title="Ready-to-dial list", box=box.ROUNDED, show_lines=False)
        table.add_column("Business", style="bold cyan")
        table.add_column("Phone", style="bold white", no_wrap=True)
        table.add_column("Rating", no_wrap=True)
        table.add_column("Website")
        for lead in report.leads:
            rating = f"{lead.rating}★ ({lead.reviews_count})" if lead.rating else "—"
            table.add_row(lead.business_name, lead.phone, rating, lead.website or "—")
        console.print(table)

    asyncio.run(run())


@app.command("enrich")
def enrich(
    input_file: Annotated[Path, typer.Option("--input", "-i", help="JSON file containing list of company domains")] = Path("data/input.json"),
    output_file: Annotated[Path, typer.Option("--output", "-o", help="Output JSON file destination")] = Path("data/output.json"),
    provider: Annotated[str, typer.Option("--provider", help="LLM provider: openai, anthropic, gemini, groq, mistral, ollama, mock")] = "mock",
    model: Annotated[str, typer.Option("--model", help="Model name")] = "mock",
    fetcher: Annotated[str, typer.Option("--fetcher", help="Fetcher: auto, http, playwright, stealth, or plugin name")] = "auto",
    max_pages: Annotated[int, typer.Option("--max-pages", help="Max internal pages to discover per domain")] = 4,
    force_refresh: Annotated[bool, typer.Option("--refresh", help="Bypass cache and force fresh fetch")] = False,
) -> None:
    """Autonomously enrich company domains for the SoftwareBrio assignment."""

    async def run() -> None:
        from dave.enrichment import LeadEnrichmentAgent

        if not input_file.exists():
            console.print(f"[red]Input file not found:[/red] {input_file}")
            raise typer.BadParameter(f"Input file {input_file} does not exist.")

        raw_data = json.loads(input_file.read_text(encoding="utf-8"))
        domains: list[str] = []
        if isinstance(raw_data, list):
            for item in raw_data:
                if isinstance(item, str):
                    domains.append(item.strip())
                elif isinstance(item, dict) and "domain" in item:
                    domains.append(str(item["domain"]).strip())
        else:
            raise typer.BadParameter("Input JSON must be an array of domain strings or objects with 'domain'.")

        if not domains:
            console.print("[yellow]No domains found in input file.[/yellow]")
            return

        engine = _make_engine(provider, model, fetcher)
        agent = LeadEnrichmentAgent(engine=engine)

        console.print(
            Panel.fit(
                f"[bold cyan]SoftwareBrio Lead Enrichment Agent[/bold cyan]\n"
                f"Targets: [bold]{len(domains)} domains[/bold] ({', '.join(domains[:3])}{'...' if len(domains) > 3 else ''})\n"
                f"Provider: [bold]{provider}[/bold] | Model: [bold]{model}[/bold] | Fetcher: [bold]{fetcher}[/bold]",
                title="DAVE Autonomous Agent",
                border_style="cyan",
            )
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Enriching companies...", total=len(domains))
            results, metrics = await agent.enrich_domains(
                domains, max_subpages=max_pages, force_refresh=force_refresh
            )
            progress.update(task, completed=len(domains))

        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)
        serialized_results = [r.model_dump() for r in results]
        output_file.write_text(json.dumps(serialized_results, indent=2, ensure_ascii=False), encoding="utf-8")

        # Render summary tables
        table = Table(title="Company Enrichment Results", box=box.ROUNDED)
        table.add_column("Domain", style="bold cyan")
        table.add_column("Status", no_wrap=True)
        table.add_column("Confidence", justify="right")
        table.add_column("Pages", justify="right")
        table.add_column("Contacts", justify="right")
        table.add_column("Leaders", justify="right")

        for r in results:
            status_style = "green" if r.status.value == "success" else "yellow" if r.status.value == "partial" else "red"
            status_text = f"[{status_style}]{r.status.value}[/{status_style}]"
            conf_text = f"{r.confidence_score:.2f}"
            table.add_row(
                r.domain,
                status_text,
                conf_text,
                str(len(r.source_pages)),
                str(len(r.contact_points)),
                str(len(r.leadership)),
            )

        console.print(table)

        summary_panel = Panel.fit(
            f"Companies Processed: [bold]{metrics.companies_processed}[/bold]\n"
            f"  • Successful: [green]{metrics.successful_count}[/green]\n"
            f"  • Partial: [yellow]{metrics.partial_count}[/yellow]\n"
            f"  • Failed: [red]{metrics.failed_count}[/red]\n"
            f"Pages Analyzed: [bold]{metrics.pages_processed}[/bold]\n"
            f"Tokens Used: [bold]{metrics.total_tokens:,}[/bold]\n"
            f"Estimated Cost: [bold green]${metrics.total_cost_usd:.6f}[/bold green]\n"
            f"Output saved to: [bold underline]{output_file}[/bold underline]",
            title="Batch Run Summary",
            border_style="green",
        )
        console.print(summary_panel)

    asyncio.run(run())


@app.command("recipes")
def list_recipes() -> None:
    """List built-in extraction recipes."""
    table = Table(title="DAVE Recipes", box=box.ROUNDED)
    table.add_column("Recipe", style="bold cyan")
    table.add_column("Returns")
    for name, (schema, _) in recipes.RECIPES.items():
        table.add_row(name, schema.__name__)
    console.print(table)


def main() -> None:
    """Run the Typer app."""
    app()


if __name__ == "__main__":
    main()
