"""Command Line Interface for docconv using Typer and Rich."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from docconv.config import load_config
from docconv.logging_setup import setup_logging
from docconv.pipeline import ConversionPipeline
from docconv.quality import evaluate_quality
from docconv.registry import list_supported_extensions

app = typer.Typer(
    name="docconv",
    help="Fast, offline-first document to Markdown converter.",
    add_completion=False,
)
console = Console()


@app.command(name="convert")
def convert_command(
    input_path: Path = typer.Argument(
        ...,
        help="Input document file or directory to convert.",
        exists=True,
        readable=True,
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "-o",
        "--output-dir",
        help="Output directory where .md and assets will be saved.",
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "-c",
        "--config",
        help="Path to YAML configuration file.",
    ),
    ocr: Optional[bool] = typer.Option(
        None,
        "--ocr/--no-ocr",
        help="Enable or disable OCR for scanned documents.",
    ),
    lang: str = typer.Option(
        "ind+eng",
        "--lang",
        help="OCR language codes separated by '+' (e.g., 'ind+eng', 'eng').",
    ),
    images: Optional[bool] = typer.Option(
        None,
        "--images/--no-images",
        help="Extract embedded images to assets directory.",
    ),
    pdf_engine: Optional[str] = typer.Option(
        None,
        "--pdf-engine",
        help="PDF conversion engine: 'pymupdf4llm' (default) or 'docling'.",
    ),
    recursive: bool = typer.Option(
        True,
        "--recursive/--no-recursive",
        help="Recursively convert all files in input folder.",
    ),
    log_file: Path = typer.Option(
        Path("conversion.log"),
        "--log-file",
        help="Path to save log file.",
    ),
    verbose: bool = typer.Option(
        False,
        "-v",
        "--verbose",
        help="Enable verbose / debug logs in console.",
    ),
) -> None:
    """Convert a document or a directory of documents into clean Markdown."""
    setup_logging(log_file=log_file, verbose=verbose)
    cfg = load_config(config_file)

    # Overwrite config values with CLI options if explicitly supplied
    if output_dir is not None:
        cfg.output_dir = output_dir
    if ocr is not None:
        cfg.ocr.enabled = ocr
    if lang:
        cfg.ocr.lang = lang
    if images is not None:
        cfg.images.extract = images
    if pdf_engine is not None:
        cfg.pdf.engine = pdf_engine
    cfg.batch.recursive = recursive

    console.print(
        f"[bold blue]docconv[/bold blue] starting conversion of [bold]{input_path}[/bold] "
        f"-> [bold]{cfg.output_dir}[/bold]"
    )

    pipeline = ConversionPipeline(cfg)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Processing documents...", total=None)
        summary = pipeline.convert_path(input_path, output_dir=cfg.output_dir)

    # Output summary table
    table = Table(title="Conversion Summary", show_header=True, header_style="bold magenta")
    table.add_column("Status", style="bold", width=12)
    table.add_column("Source Document")
    table.add_column("Output File")
    table.add_column("Assets", justify="right")
    table.add_column("Time (s)", justify="right")

    for res in summary.results:
        status = "[green]SUCCESS[/green]" if res.success else "[red]FAILED[/red]"
        out = str(res.output_path.name) if res.output_path else "-"
        assets_str = str(res.assets_count) if res.assets_count else "0"
        time_str = f"{res.duration_seconds:.2f}"
        table.add_row(status, res.source_path.name, out, assets_str, time_str)

    console.print(table)
    console.print(
        f"[bold]Total:[/] {summary.total} | "
        f"[green]Succeeded:[/] {summary.succeeded} | "
        f"[red]Failed:[/] {summary.failed} | "
        f"[dim]Time: {summary.duration_seconds:.2f}s[/dim]"
    )

    if summary.failed > 0:
        console.print(f"[yellow]Review [bold]{log_file}[/bold] for failure details.[/yellow]")
        raise typer.Exit(code=1)


@app.command(name="eval")
def eval_command(
    source: Path = typer.Argument(..., help="Path to source document.", exists=True),
    markdown: Path = typer.Argument(..., help="Path to converted Markdown file.", exists=True),
) -> None:
    """Evaluate conversion quality by comparing structural metrics between source and Markdown."""
    console.print(f"Comparing [bold]{source.name}[/bold] vs [bold]{markdown.name}[/bold]...")
    report = evaluate_quality(source, markdown)

    table = Table(title="Quality Evaluation Report", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Source Document", justify="right")
    table.add_column("Markdown", justify="right")
    table.add_column("Difference", justify="right")
    table.add_column("Retention %", justify="right")

    src = report.source_metrics
    md = report.md_metrics
    diffs = report.differences
    retention = report.retention_rates

    metrics = [
        ("Headings", src.headings, md.headings, diffs["headings"], retention["headings"]),
        ("Tables", src.tables, md.tables, diffs["tables"], retention["tables"]),
        ("Images", src.images, md.images, diffs["images"], retention["images"]),
        ("Links", src.links, md.links, diffs["links"], retention["links"]),
        ("Words", src.words, md.words, diffs["words"], retention["words"]),
    ]

    for name, s_val, m_val, diff, ret in metrics:
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        ret_color = "green" if ret >= 90 else ("yellow" if ret >= 70 else "red")
        ret_str = f"[{ret_color}]{ret:.1f}%[/{ret_color}]"
        table.add_row(name, str(s_val), str(m_val), diff_str, ret_str)

    console.print(table)


@app.command(name="formats")
def formats_command() -> None:
    """List all supported document formats."""
    exts = list_supported_extensions()
    console.print("[bold green]Supported extensions:[/bold green] " + ", ".join(exts))


@app.callback()
def main_callback() -> None:
    """docconv — Fast, offline-first document to Markdown converter."""
    pass


def main() -> None:
    """Entry point with automatic 'convert' routing when first argument is a file/path."""
    import sys

    known_cmds = {"eval", "formats", "convert", "--help", "-h", "--install-completion", "--show-completion"}
    if len(sys.argv) > 1 and sys.argv[1] not in known_cmds and not sys.argv[1].startswith("-"):
        sys.argv.insert(1, "convert")

    app()


if __name__ == "__main__":
    main()

