"""Typer CLI entry point for AI SEO Platform."""

import asyncio
import sys

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from aiseo.config import get_settings
from aiseo.models import create_db_and_tables
from aiseo.utils.text import normalize_url

app = typer.Typer(
    name="aiseo",
    help="AI Visibility Intelligence for SaaS Founders",
    no_args_is_help=True,
)
console = Console()


@app.command()
def scan(
    url: str = typer.Argument(..., help="Website URL to scan"),
    queries: int = typer.Option(10, "--queries", "-q", help="Number of queries to generate"),
):
    """Quick scan: paste a URL and get AI visibility results."""
    settings = get_settings()
    _check_api_keys(settings)

    create_db_and_tables()

    console.print(Panel(f"[bold]AI SEO Platform Scan[/bold]\n{normalize_url(url)}", style="blue"))

    with console.status("[bold green]Extracting brand profile..."):
        brand_profile = asyncio.run(_run_extraction(url))

    _display_brand_profile(brand_profile)

    with console.status(f"[bold green]Generating {queries} queries..."):
        query_list = asyncio.run(_run_query_generation(brand_profile, queries))

    _display_queries(query_list)

    console.print(
        "\n[bold yellow]Phase 2 (LLM scanning) coming soon![/bold yellow]\n"
        "Run [bold]aiseo serve[/bold] to start the API server."
    )


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Host to bind"),
    port: int = typer.Option(8000, help="Port to bind"),
):
    """Start the AI SEO Platform API server."""
    import uvicorn

    console.print(Panel(f"[bold]AI SEO Platform API Server[/bold]\nhttp://{host}:{port}", style="green"))
    uvicorn.run("aiseo.main:app", host=host, port=port, reload=True)


@app.command()
def info():
    """Show current configuration and available providers."""
    settings = get_settings()
    table = Table(title="AI SEO Platform Configuration")
    table.add_column("Provider", style="bold")
    table.add_column("Status")

    providers = [
        ("OpenAI (ChatGPT)", settings.openai_api_key),
        ("Anthropic (Claude)", settings.anthropic_api_key),
        ("Google (Gemini)", settings.google_api_key),
        ("Perplexity", settings.perplexity_api_key),
    ]
    for name, key in providers:
        status = "[green]Configured[/green]" if key else "[dim]Not set[/dim]"
        table.add_row(name, status)

    console.print(table)
    console.print(f"\nDatabase: {settings.database_url}")
    console.print(f"Redis: {settings.redis_url}")


def _check_api_keys(settings):
    """Ensure at least one LLM API key is configured."""
    has_key = any([
        settings.openai_api_key,
        settings.anthropic_api_key,
        settings.google_api_key,
    ])
    if not has_key:
        console.print(
            "[bold red]Error:[/bold red] No LLM API key configured.\n"
            "Set at least one of: AISEO_OPENAI_API_KEY, AISEO_ANTHROPIC_API_KEY, "
            "AISEO_GOOGLE_API_KEY\n\n"
            "See .env.example for all options.",
            style="red",
        )
        sys.exit(1)


async def _run_extraction(url: str) -> dict:
    """Run brand extraction."""
    from aiseo.services.brand_extractor import extract_brand_profile

    return await extract_brand_profile(url)


async def _run_query_generation(brand_profile: dict, max_queries: int) -> list[dict]:
    """Run query generation."""
    from aiseo.services.query_generator import generate_all_queries

    return await generate_all_queries(brand_profile, max_queries=max_queries)


def _display_brand_profile(profile: dict):
    """Display extracted brand profile."""
    table = Table(title="Brand Profile", show_lines=True)
    table.add_column("Field", style="bold")
    table.add_column("Value")

    table.add_row("Brand Name", profile.get("brand_name", ""))
    table.add_row("Aliases", ", ".join(profile.get("brand_aliases", [])))
    table.add_row("Category", profile.get("category", ""))
    table.add_row("Description", profile.get("description", "")[:200])
    table.add_row("Competitors", ", ".join(profile.get("competitors", [])))
    table.add_row("Features", ", ".join(profile.get("features", [])))
    table.add_row("Target Audience", profile.get("target_audience", ""))

    console.print(table)


def _display_queries(queries: list[dict]):
    """Display generated queries."""
    table = Table(title=f"Generated Queries ({len(queries)})")
    table.add_column("#", style="dim", width=4)
    table.add_column("Query")
    table.add_column("Intent", style="cyan")

    for i, q in enumerate(queries, 1):
        table.add_row(str(i), q["text"], q["intent_category"])

    console.print(table)


if __name__ == "__main__":
    app()
