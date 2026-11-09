## Assignment 4

For this assignment I copied my Day03 project (the *mating efficiency index* of a clock-gene mutant) into a new folder, *Day04*, so the old version stays intact. I then asked Claude to build a web application with **Flask** that uses the same calculation and gives it a web interface.

The prompts I used:
> Take the previous assignment, Copy it to the day04 folder just so we will have the old one intact. Write a web application (e.g. using Flask) that will use the "business logic" from the previous implementation and provide a web interface to it. Check that both the old and the new systems work. Please explain what it means to write a web application and what Flask is before doing anything, and wait for my request before executing.

> Let's add a bar plot. Is there a specific structure the data should be in? If so, let's add it to the website so a user will know how to organize the data.

### What's in this folder

| File | What it does |
|------|--------------|
| `mating_efficiency_index.py` | The logic: checks the data format, calculates the index per male and the mean/SD per genotype, draws the bar plot and writes the Excel output. It can still be run on its own from the command line. |
| `app.py` | The Flask web application. It imports the functions above and only handles pages, uploads and downloads. |
| `templates/`, `static/` | The HTML pages and the stylesheet of the website. |
| `Data/` | The original data (unchanged) and the outputs of the command-line version (Excel + bar plot). |
| `requirements.txt` | The Python packages needed. |

### How to run

Install the packages (once):
```
pip install -r requirements.txt
```

**Command-line version** (same as Day03, now also saves a bar plot):
```
python mating_efficiency_index.py
```

**Web version:**
```
python app.py
```
Then open http://127.0.0.1:5000 in a browser. Stop the server with Ctrl+C in the terminal.

On the website you can:
1. Read how the data must be organized (and download an Excel template).
2. Upload an Excel file, or use the example data.
3. Choose a sheet. Sheets in the right format are marked ✓.
4. See the bar plot (mean ± SD, with each male as a dot) and the tables, and download the results as Excel and the plot as PNG.

### Required data format

- One row per male, first row = column names.
- `Genotype`: the group of the male.
- `herm_1`, `herm_2`, `herm_3`, `herm_4`: 1 = hermaphrodite had progeny, 0 = no progeny.
- Other columns (e.g. `male_number`) are allowed and kept in the output.

### Checking that both versions work

The Day03 script and the Day04 script (command line and web download) were run on the same sheet (`19.10.25 ces-2 normal dev time`) and gave identical results:

| Genotype | n_males | mean_index | sd_index |
|----------|---------|------------|----------|
| him-5    | 12      | 0.458      | 0.257    |
| ces-2    | 15      | 0.117      | 0.208    |
