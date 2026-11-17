"""Tests for the business logic in mating_efficiency_index.py.

Run from the Day04 folder with:   python -m pytest -v

Each test builds a small table where the correct answer is easy to work out by hand,
runs one function on it, and checks the result.
"""

import math
from io import BytesIO

import matplotlib.pyplot as plt
import pandas as pd
import pytest

import mating_efficiency_index as mei


# ---------------------------------------------------------------------------
# Fixtures: small example tables reused by several tests
# ---------------------------------------------------------------------------

@pytest.fixture
def small_data():
    """Two genotypes. Each row's comment shows how many herms had progeny."""
    return pd.DataFrame({
        "Genotype":    ["wt", "wt", "wt", "mut", "mut"],
        "male_number": [1, 2, 3, 1, 2],
        "herm_1":      [1, 1, 0, 0, 1],
        "herm_2":      [1, 1, 0, 0, 0],
        "herm_3":      [1, 0, 0, 0, 0],
        "herm_4":      [1, 0, 0, 0, 0],
        #               4  2  0  0  1   herms with progeny
    })


@pytest.fixture(autouse=True)
def close_figures():
    """Close any plots a test created, so they don't pile up in memory."""
    yield
    plt.close("all")


# ---------------------------------------------------------------------------
# Index per male
# ---------------------------------------------------------------------------

def test_index_per_male_is_fraction_of_herms_with_progeny(small_data):
    per_male, _ = mei.calculate_indices(small_data)
    assert per_male["mating_efficiency_index"].tolist() == [1.0, 0.5, 0.0, 0.0, 0.25]


@pytest.mark.parametrize("scores, expected", [
    ([0, 0, 0, 0], 0.0),
    ([1, 0, 0, 0], 0.25),
    ([0, 1, 0, 1], 0.5),
    ([1, 1, 1, 0], 0.75),
    ([1, 1, 1, 1], 1.0),
])
def test_every_possible_index_value(scores, expected):
    data = pd.DataFrame([["wt", *scores]], columns=["Genotype", *mei.HERM_COLUMNS])
    per_male, _ = mei.calculate_indices(data)
    assert per_male["mating_efficiency_index"].iloc[0] == expected


def test_scores_read_as_decimals_are_accepted():
    """Excel sometimes gives 1.0 instead of 1; that should still count."""
    data = pd.DataFrame([["wt", 1.0, 0.0, 1.0, 0.0]], columns=["Genotype", *mei.HERM_COLUMNS])
    per_male, _ = mei.calculate_indices(data)
    assert per_male["mating_efficiency_index"].iloc[0] == 0.5


def test_original_columns_are_kept_and_input_is_not_changed(small_data):
    original = small_data.copy()
    per_male, _ = mei.calculate_indices(small_data)

    assert list(per_male.columns) == list(original.columns) + ["mating_efficiency_index"]
    pd.testing.assert_frame_equal(small_data, original)  # the input table was not modified


# ---------------------------------------------------------------------------
# Summary per genotype
# ---------------------------------------------------------------------------

def test_genotype_summary_counts_mean_and_sd(small_data):
    _, per_genotype = mei.calculate_indices(small_data)
    wt = per_genotype.set_index("Genotype").loc["wt"]
    mut = per_genotype.set_index("Genotype").loc["mut"]

    # wt indices: 1.0, 0.5, 0.0 -> mean 0.5, sample SD 0.5
    assert wt["n_males"] == 3
    assert wt["mean_index"] == pytest.approx(0.5)
    assert wt["sd_index"] == pytest.approx(0.5)

    # mut indices: 0.0, 0.25 -> mean 0.125, sample SD = 0.25 / sqrt(2)
    assert mut["n_males"] == 2
    assert mut["mean_index"] == pytest.approx(0.125)
    assert mut["sd_index"] == pytest.approx(0.25 / math.sqrt(2))


def test_genotypes_keep_the_order_they_appear_in(small_data):
    _, per_genotype = mei.calculate_indices(small_data)
    assert per_genotype["Genotype"].tolist() == ["wt", "mut"]  # not alphabetical


def test_genotype_with_one_male_has_no_sd():
    data = pd.DataFrame([["solo", 1, 1, 0, 0]], columns=["Genotype", *mei.HERM_COLUMNS])
    _, per_genotype = mei.calculate_indices(data)
    assert per_genotype["n_males"].iloc[0] == 1
    assert per_genotype["mean_index"].iloc[0] == 0.5
    assert math.isnan(per_genotype["sd_index"].iloc[0])  # SD needs at least 2 males


# ---------------------------------------------------------------------------
# Data format checks
# ---------------------------------------------------------------------------

def test_correct_data_passes_validation(small_data):
    mei.validate_data(small_data)  # should not raise an error


def test_missing_column_is_reported(small_data):
    data = small_data.drop(columns=["herm_3"])
    with pytest.raises(mei.DataFormatError, match="Missing required column.*herm_3"):
        mei.calculate_indices(data)


def test_misspelled_genotype_column_is_reported(small_data):
    data = small_data.rename(columns={"Genotype": "genotype"})  # wrong capitalization
    with pytest.raises(mei.DataFormatError, match="Genotype"):
        mei.calculate_indices(data)


def test_empty_genotype_is_reported_with_excel_row(small_data):
    small_data.loc[1, "Genotype"] = None  # 2nd data row = Excel row 3
    with pytest.raises(mei.DataFormatError, match=r"Empty 'Genotype'.*\[3\]"):
        mei.calculate_indices(small_data)


@pytest.mark.parametrize("bad_value", [2, -1, 0.5, "yes", None])
def test_scores_other_than_0_or_1_are_rejected(small_data, bad_value):
    small_data["herm_2"] = small_data["herm_2"].astype(object)
    small_data.loc[3, "herm_2"] = bad_value  # 4th data row = Excel row 5
    with pytest.raises(mei.DataFormatError, match=r"'herm_2' must contain only 0 or 1.*\[5\]"):
        mei.calculate_indices(small_data)


# ---------------------------------------------------------------------------
# Outputs: Excel file and bar plot
# ---------------------------------------------------------------------------

def test_excel_output_contains_both_tables(small_data):
    per_male, per_genotype = mei.calculate_indices(small_data)
    content = mei.results_to_excel_bytes(per_male, per_genotype)

    sheets = pd.read_excel(BytesIO(content), sheet_name=None)  # read all sheets
    assert list(sheets) == ["per_male", "per_genotype"]
    pd.testing.assert_frame_equal(sheets["per_male"], per_male)
    pd.testing.assert_frame_equal(sheets["per_genotype"], per_genotype)


def test_bar_plot_has_one_bar_per_genotype_at_the_mean(small_data):
    per_male, per_genotype = mei.calculate_indices(small_data)
    fig = mei.make_bar_plot(per_male, per_genotype, title="test")
    ax = fig.axes[0]

    bar_heights = [bar.get_height() for bar in ax.patches]
    assert bar_heights == pytest.approx([0.5, 0.125])
    assert ax.get_title() == "test"
    assert [label.get_text() for label in ax.get_xticklabels()] == ["wt\n(n=3)", "mut\n(n=2)"]


# ---------------------------------------------------------------------------
# Real experiment data (checks the results haven't changed since Day03)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not mei.INPUT_FILE.exists(), reason="example data file not found")
def test_real_data_gives_known_results():
    data = pd.read_excel(mei.INPUT_FILE, sheet_name=mei.SHEET_NAME)
    _, per_genotype = mei.calculate_indices(data)
    summary = per_genotype.set_index("Genotype")

    assert summary.loc["him-5", "n_males"] == 12
    assert summary.loc["him-5", "mean_index"] == pytest.approx(0.458333, abs=1e-6)
    assert summary.loc["ces-2", "n_males"] == 15
    assert summary.loc["ces-2", "mean_index"] == pytest.approx(0.116667, abs=1e-6)
