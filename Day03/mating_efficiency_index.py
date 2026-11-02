"""Calculate a mating efficiency index for each male and the average index per genotype.

Mating efficiency index = (number of hermaphrodites with progeny) / (number of hermaphrodites tested).
Each male was tested with 4 hermaphrodites (herm_1 - herm_4); a score of 1 means the herm had progeny.

The original data file is only read; results are written to a new Excel file.
"""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "Data"
INPUT_FILE = DATA_DIR / "mating_efficiency_data.xlsx"
OUTPUT_FILE = DATA_DIR / "mating_efficiency_index.xlsx"
SHEET_NAME = "19.10.25 ces-2 normal dev time"
HERM_COLUMNS = ["herm_1", "herm_2", "herm_3", "herm_4"]


def main():
    data = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME)

    # Index per male: fraction of the 4 hermaphrodites that had progeny (score == 1)
    data["mating_efficiency_index"] = (data[HERM_COLUMNS] == 1).sum(axis=1) / len(HERM_COLUMNS)

    # Average index per genotype (keep the order in which genotypes appear in the data)
    group_summary = (
        data.groupby("Genotype", sort=False)["mating_efficiency_index"]
        .agg(n_males="count", mean_index="mean", sd_index="std")
        .reset_index()
    )

    with pd.ExcelWriter(OUTPUT_FILE) as writer:
        data.to_excel(writer, sheet_name="per_male", index=False)
        group_summary.to_excel(writer, sheet_name="per_genotype", index=False)

    print(data.to_string(index=False))
    print()
    print(group_summary.to_string(index=False))
    print(f"\nResults saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
