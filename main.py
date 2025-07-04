

import typer
import pathlib

from company_finder import Orchestrator
from company_finder.output_writer import OutputWriter

app = typer.Typer(help="Find companies by industry & location.")

@app.command()
def find(
    # industry: str = typer.Argument(..., help="Industry keyword, e.g. 'machine learning'"),
    # location: str = typer.Argument(..., help="City / region"),
    # output: pathlib.Path = typer.Option("results.csv", help="Output file (csv/xlsx/json)"),
):
    """Search and save matching companies."""
    industry="software"
    location="Bengaluru"
    output = pathlib.Path("results.csv")

    ora = Orchestrator()
    writer = OutputWriter()
    results = ora.run(industry, location)

    suffix = output.suffix.lower()
    if suffix == ".csv":
        writer.save_csv(results, output)
    elif suffix in [".xls", ".xlsx"]:
        writer.save_excel(results, output)
    elif suffix == ".json":
        writer.save_json(results, output)
    else:
        raise typer.BadParameter("Unsupported file type. Use .csv, .xlsx, or .json")

    writer.print_pretty(results)
    typer.echo(f"Saved {len(results)} records to {output}")

if __name__ == "__main__":
    app()
