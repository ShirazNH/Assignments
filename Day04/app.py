"""Web interface for the mating efficiency index calculation.

Run with:   python app.py
Then open:  http://127.0.0.1:5000

All the calculations come from mating_efficiency_index.py (the "business logic");
this file only handles web pages, file uploads and downloads.
"""

import base64
import re
import uuid
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from flask import Flask, abort, redirect, render_template, request, send_file, url_for

import mating_efficiency_index as mei

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
EXAMPLE_TOKEN = "example"
TOKEN_PATTERN = re.compile(r"^[0-9a-f]{32}$")
EXCEL_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # reject uploads larger than 10 MB


def file_for_token(token):
    """Map a token from the URL to an Excel file on disk (the example file or an upload)."""
    if token == EXAMPLE_TOKEN:
        return mei.INPUT_FILE
    if not TOKEN_PATTERN.match(token):
        abort(404)
    path = UPLOAD_DIR / f"{token}.xlsx"
    if not path.exists():
        abort(404)
    return path


def sheet_has_required_columns(excel_file, sheet):
    header = pd.read_excel(excel_file, sheet_name=sheet, nrows=0)
    return all(col in header.columns for col in mei.REQUIRED_COLUMNS)


def analyze(token, sheet):
    """Read one sheet and run the business logic on it."""
    path = file_for_token(token)
    try:
        data = pd.read_excel(path, sheet_name=sheet)
    except ValueError:
        abort(404)  # sheet does not exist
    return mei.calculate_indices(data)


def figure_to_base64(fig):
    buffer = BytesIO()
    fig.savefig(buffer, format="png")
    plt.close(fig)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


@app.route("/")
def index():
    return render_template(
        "index.html",
        required_columns=mei.REQUIRED_COLUMNS,
        herm_columns=mei.HERM_COLUMNS,
        error=request.args.get("error"),
    )


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("data_file")
    if file is None or file.filename == "":
        return redirect(url_for("index", error="Please choose a file to upload."))
    if not file.filename.lower().endswith(".xlsx"):
        return redirect(url_for("index", error="Only Excel .xlsx files are supported."))

    token = uuid.uuid4().hex
    path = UPLOAD_DIR / f"{token}.xlsx"
    file.save(path)
    try:
        pd.ExcelFile(path).close()  # make sure it really is a readable Excel file
    except Exception:
        path.unlink(missing_ok=True)
        return redirect(url_for("index", error="The file could not be read as an Excel workbook."))
    return redirect(url_for("choose_sheet", token=token))


@app.route("/sheets/<token>")
def choose_sheet(token):
    path = file_for_token(token)
    with pd.ExcelFile(path) as excel_file:
        sheets = [(name, sheet_has_required_columns(excel_file, name)) for name in excel_file.sheet_names]

    # If there is exactly one sheet in the right format, go straight to the results
    good = [name for name, ok in sheets if ok]
    if len(sheets) == 1 and good:
        return redirect(url_for("results", token=token, sheet=good[0]))

    default = mei.SHEET_NAME if token == EXAMPLE_TOKEN else (good[0] if good else None)
    return render_template("sheets.html", token=token, sheets=sheets, default=default,
                           required_columns=mei.REQUIRED_COLUMNS)


@app.route("/results/<token>")
def results(token):
    sheet = request.args.get("sheet", "")
    try:
        per_male, per_genotype = analyze(token, sheet)
    except mei.DataFormatError as error:
        return render_template("format_error.html", token=token, sheet=sheet, message=str(error),
                               required_columns=mei.REQUIRED_COLUMNS), 400

    plot_png = figure_to_base64(mei.make_bar_plot(per_male, per_genotype, title=sheet))
    return render_template(
        "results.html",
        token=token,
        sheet=sheet,
        plot_png=plot_png,
        per_genotype=per_genotype.round(3).to_html(index=False, classes="table", na_rep="–"),
        per_male=per_male.round(3).to_html(index=False, classes="table"),
    )


@app.route("/download/<token>")
def download(token):
    sheet = request.args.get("sheet", "")
    try:
        per_male, per_genotype = analyze(token, sheet)
    except mei.DataFormatError:
        abort(400)
    content = mei.results_to_excel_bytes(per_male, per_genotype)
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", sheet).strip("_") or "results"
    return send_file(BytesIO(content), mimetype=EXCEL_MIME, as_attachment=True,
                     download_name=f"mating_efficiency_index_{safe_name}.xlsx")


@app.route("/plot/<token>")
def download_plot(token):
    sheet = request.args.get("sheet", "")
    try:
        per_male, per_genotype = analyze(token, sheet)
    except mei.DataFormatError:
        abort(400)
    buffer = BytesIO()
    fig = mei.make_bar_plot(per_male, per_genotype, title=sheet)
    fig.savefig(buffer, format="png", dpi=200)
    plt.close(fig)
    buffer.seek(0)
    return send_file(buffer, mimetype="image/png", as_attachment=True,
                     download_name="mating_efficiency_index.png")


@app.route("/template")
def download_template():
    """An example Excel file showing the required data layout."""
    example = pd.DataFrame({
        "Genotype":    ["wild-type", "wild-type", "wild-type", "mutant", "mutant", "mutant"],
        "male_number": [1, 2, 3, 1, 2, 3],
        "herm_1":      [1, 0, 1, 0, 0, 1],
        "herm_2":      [1, 1, 0, 0, 0, 0],
        "herm_3":      [0, 1, 1, 1, 0, 0],
        "herm_4":      [1, 0, 1, 0, 0, 0],
    })
    buffer = BytesIO()
    example.to_excel(buffer, sheet_name="my_experiment", index=False)
    buffer.seek(0)
    return send_file(buffer, mimetype=EXCEL_MIME, as_attachment=True,
                     download_name="mating_efficiency_template.xlsx")


@app.errorhandler(413)
def file_too_large(_error):
    return redirect(url_for("index", error="The file is too large (maximum 10 MB)."))


if __name__ == "__main__":
    app.run(debug=True)
