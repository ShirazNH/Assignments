"""Calculate a mating efficiency index for each male and the average index per genotype.

Mating efficiency index = (number of hermaphrodites with progeny) / (number of hermaphrodites tested).
Each male was tested with 4 hermaphrodites (herm_1 - herm_4); a score of 1 means the herm had progeny.

This module holds the "business logic" and is used in two ways:
  * as a command-line script:  python mating_efficiency_index.py
  * imported by the web application (app.py)

The original data file is only read; results are written to a new Excel file.
"""

from io import BytesIO
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # draw plots to files/memory, no window needed (required for the web server)
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).parent / "Data"
INPUT_FILE = DATA_DIR / "mating_efficiency_data.xlsx"
OUTPUT_FILE = DATA_DIR / "mating_efficiency_index.xlsx"
PLOT_FILE = DATA_DIR / "mating_efficiency_index.png"
SHEET_NAME = "19.10.25 ces-2 normal dev time"

GENOTYPE_COLUMN = "Genotype"
HERM_COLUMNS = ["herm_1", "herm_2", "herm_3", "herm_4"]
REQUIRED_COLUMNS = [GENOTYPE_COLUMN] + HERM_COLUMNS
ALLOWED_SCORES = {0, 1}

# Bar colors, assigned to genotypes in the order they appear in the data
BAR_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]


class DataFormatError(ValueError):
    """Raised when the data does not have the expected structure."""


def validate_data(data):
    """Check that the table has the required columns and that scores are 0 or 1.

    Raises DataFormatError with a human-readable message if something is wrong.
    """
    missing = [col for col in REQUIRED_COLUMNS if col not in data.columns]
    if missing:
        found = ", ".join(str(c) for c in data.columns) or "(none)"
        raise DataFormatError(
            f"Missing required column(s): {', '.join(missing)}. Columns found: {found}"
        )

    if data[GENOTYPE_COLUMN].isna().any():
        rows = (data.index[data[GENOTYPE_COLUMN].isna()] + 2).tolist()  # +2: header row + 1-based
        raise DataFormatError(f"Empty 'Genotype' value in Excel row(s): {rows}")

    for col in HERM_COLUMNS:
        bad = ~data[col].isin(ALLOWED_SCORES)
        if bad.any():
            rows = (data.index[bad] + 2).tolist()
            values = data.loc[bad, col].tolist()
            raise DataFormatError(
                f"Column '{col}' must contain only 0 or 1. "
                f"Problem in Excel row(s) {rows} (values: {values})"
            )


def calculate_indices(data):
    """Return (per_male, per_genotype) tables.

    per_male:     the input table with an added 'mating_efficiency_index' column
    per_genotype: number of males, mean and standard deviation of the index per genotype
    """
    validate_data(data)
    per_male = data.copy()

    # Index per male: fraction of the 4 hermaphrodites that had progeny (score == 1)
    per_male["mating_efficiency_index"] = (per_male[HERM_COLUMNS] == 1).sum(axis=1) / len(HERM_COLUMNS)

    # Average index per genotype (keep the order in which genotypes appear in the data)
    per_genotype = (
        per_male.groupby(GENOTYPE_COLUMN, sort=False)["mating_efficiency_index"]
        .agg(n_males="count", mean_index="mean", sd_index="std")
        .reset_index()
    )
    return per_male, per_genotype


def make_bar_plot(per_male, per_genotype, title="Mating efficiency index"):
    """Bar plot of the mean index per genotype (error bars = SD), with each male as a dot."""
    n = len(per_genotype)
    fig, ax = plt.subplots(figsize=(max(4, 1.6 * n + 1.5), 4.5), dpi=120)
    x = np.arange(n)
    colors = [BAR_COLORS[i % len(BAR_COLORS)] for i in range(n)]

    ax.bar(x, per_genotype["mean_index"], width=0.6, color=colors, zorder=2)
    ax.errorbar(x, per_genotype["mean_index"], yerr=per_genotype["sd_index"].fillna(0),
                fmt="none", ecolor="#333333", elinewidth=1.5, capsize=6, zorder=3)

    # Individual males as dots, with a small horizontal jitter so they don't overlap
    rng = np.random.default_rng(0)
    for i, genotype in enumerate(per_genotype[GENOTYPE_COLUMN]):
        values = per_male.loc[per_male[GENOTYPE_COLUMN] == genotype, "mating_efficiency_index"]
        jitter = rng.uniform(-0.15, 0.15, size=len(values))
        ax.scatter(x[i] + jitter, values, s=22, color="#222222", alpha=0.6, zorder=4, linewidths=0)

    labels = [f"{g}\n(n={k})" for g, k in zip(per_genotype[GENOTYPE_COLUMN], per_genotype["n_males"])]
    ax.set_xticks(x, labels)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Mating efficiency index\n(fraction of herms with progeny)")
    ax.set_title(title)
    ax.yaxis.grid(True, color="#e5e5e5", zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.99, 0.01, "Bars: mean ± SD; dots: individual males", ha="right", fontsize=8, color="#555555")
    fig.tight_layout()
    return fig


def results_to_excel(per_male, per_genotype, destination):
    """Write both tables to an Excel file (a path or a file-like object)."""
    with pd.ExcelWriter(destination) as writer:
        per_male.to_excel(writer, sheet_name="per_male", index=False)
        per_genotype.to_excel(writer, sheet_name="per_genotype", index=False)


def results_to_excel_bytes(per_male, per_genotype):
    """Same as results_to_excel, but returns the file content in memory (for downloads)."""
    buffer = BytesIO()
    results_to_excel(per_male, per_genotype, buffer)
    return buffer.getvalue()


def main():
    data = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME)
    per_male, per_genotype = calculate_indices(data)

    results_to_excel(per_male, per_genotype, OUTPUT_FILE)
    fig = make_bar_plot(per_male, per_genotype, title=SHEET_NAME)
    fig.savefig(PLOT_FILE)
    plt.close(fig)

    print(per_male.to_string(index=False))
    print()
    print(per_genotype.to_string(index=False))
    print(f"\nResults saved to: {OUTPUT_FILE}")
    print(f"Bar plot saved to: {PLOT_FILE}")


if __name__ == "__main__":
    main()
