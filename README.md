# Interactive Tool for Initial Event Log Analysis

This repository contains an interactive tool that integrates a catalog of
**patterns for the initial analysis of case-centric event logs** into a single
environment. The tool lets you
load an event log and apply the patterns to it (e.g., inspecting attributes and
schemas, enriching and transforming the log, and detecting super events,
batches, and transaction candidates) while exploring the results interactively.

The tool is a [marimo](https://marimo.io) notebook (`exploratory-tool.py`).
**No prior knowledge of marimo is required**; this README explains everything
needed to run it. The [Marimo guide](https://github.com/initial-analysis-patterns/initial-analysis-tool/blob/main/Marimo_guide.pdf)
provides an overview of the usage, with explicit indication of the patterns for
initial analysis that are realized at each part of the notebook.

---

## What is marimo?

marimo is a notebook for Python that runs in your web browser. Unlike a
traditional notebook, its cells are connected by their data dependencies: when
you change an input (for example, select a different event log or move a
slider), every dependent result is recomputed automatically, so what you see is
always consistent. You do not need to read or write code to use this tool. Instead, you
interact with it through the widgets shown in the browser (a few widgets accept
small Python snippets, but come pre-filled with working examples you can just
apply to specific event logs).

---

## Quick start

```bash
# 1. from the repository root, create and activate an isolated environment
python -m venv .venv
source .venv/bin/activate            # on Windows: .venv\Scripts\activate

# 2. install dependencies
pip install -r requirements.txt

# 3. launch the tool (run from the repository root)
marimo run exploratory-tool.py
```

A browser tab opens with the tool. On first launch it shows *"Select an event
log to start the analysis."* — pick an `.xes` or `.csv` event log in the file
browser and the analysis begins. To stop the tool, return to the terminal and
press `Ctrl+C`.

> Run the command **from the repository root**, so the notebook can import its
> helper modules (`*_util.py`) and reach the example logs.

---

## Requirements

- **Python 3.10 or newer** ([download](https://www.python.org/downloads/));
  check with `python --version`.
- A modern web browser (Chrome, Firefox, Edge, or Safari).
- The Python packages in `requirements.txt` (installed in the Quick start).

If `requirements.txt` is missing, the notebook's direct dependencies can be
installed with pip:

```bash
pip install marimo pandas numpy networkx pm4py altair vegafusion vl-convert-python plotly pytz eclear
```

A few dependencies are easy to overlook: **`vegafusion`** and **`vl-convert-python`** (used
for the charts) and **`eclear`** (provides the enrichment widget). If pm4py
cannot read XES with `variant="rustxes"` on a clean install, also add
**`rustxes`**. The helper modules
(`temporal_characteristics_util.py`, `attribute_util.py`, `data_quality_util.py`,
`structure_util.py`, `display_util.py`) are included in this repository, so no
separate installation is needed for them.

---

## Running the tool

There are two ways to open it.

### Option A: App mode

```bash
marimo run exploratory-tool.py
```

Opens the tool as a web app, by default at
`http://localhost:2718`. If the tab does not open automatically, copy the URL
printed in the terminal.

### Option B: Editable mode

```bash
marimo edit exploratory-tool.py
```

Opens the same tool with the underlying code accessible for inspection.

---

## Providing an event log

The tool analyzes **case-centric event logs** with the three mandatory process
mining attributes: a case identifier, an activity label, and a timestamp.

- **Supported formats:** `.xes` and `.csv`. For XES the standard attributes
  (`case:concept:name`, `concept:name`, `time:timestamp`), if present, are used by default;
  the tool then lets you confirm or change which columns are the case id,
  activity, and timestamp.
- **Selecting a log:** use the file browser shown at the top of the tool. It
  opens in the current working directory and lets you navigate your file system,
  so keep your logs somewhere reachable (for example inside this repository).

---

## Using the tool

After you select a log, the analysis is organized into sections;
results recompute automatically as you adjust the controls.

- **Log Initialization**: set a timezone and (optionally) normalize timestamp
  granularity, choose a time frame that keeps only cases fully contained within
  it, and confirm the mandatory attributes. A summary reports what
  initialization did, alongside timestamp-format and granularity analysis results.
- **Log Enrichment, Activity Folding & Unfolding**: add event- or case-level
  attributes (e.g., forward-fill a measurement, count an activity per case), and
  fold or unfold activities. The folding/unfolding/manual-enrichment widgets take
  small Python snippets and are **pre-filled with working examples** (Sepsis
  "Release" folding, RTFM "Payment" unfolding, a weekday enrichment) that you can
  apply directly.
- **Events View**: browse global vs. local attributes, inspect by case, view
  the log as a case log or as raw events, filter, and run univariate/bivariate
  analyses including histograms.
- **Activity Schemas View**: the attributes of each activity type, overlaps
  between schemas, and per-attribute information.
- **Attribute Dependencies and Functional Relationships**: pairwise correlation
  and normalized mutual information between attributes, and the functional
  relationships (one-to-one, one-to-many, etc.) with their value mappings.
- **Super event candidates / Batch event candidates**: activities coinciding in
  time within a case (super events) or the same activity coinciding across cases
  (batch candidates).
- **Transaction detection**: groups of activities with similar case-level
  occurrence, as candidate units of work.
- **Consistency check**: check a user-specified rule against the log; a Sepsis
  SIRSCriteria example is pre-filled and can be run as is, provided that the Sepsis log is loaded.

> Note: changing anything in **Log Initialization** (timezone, granularity, time
> frame, ordering, or the mandatory-attribute selection) rebuilds the enrichment
> widget and clears enrichments applied there. Changes made further down do not
> have that effect.

---

## Troubleshooting

- **`marimo: command not found`**: the environment is not active or
  dependencies were not installed; re-run the Quick start steps (ensure the
  virtual environment is activated).
- **`ModuleNotFoundError` for a `*_util` module or `eclear`**: launch the tool
  from the repository root, and make sure `eclear` was installed.
- **XES loading fails**: ensure `rustxes` is installed (the reader uses it);
  then retry.
- **Charts do not render**: ensure `vegafusion` and `vl-convert-python` are
  installed.
- **The browser tab did not open**: open the URL printed in the terminal
  (usually `http://localhost:2718`).
- **Port already in use**: start on another port, e.g.
  `marimo run exploratory-tool.py --port 2900`.
- **A large event log is slow**: loading and analyzing very large logs takes
  time; select a smaller time frame in Log Initialization, or try a smaller log
  first.

---

## Further notes

- The tool integrates all patterns in one environment; the individual patterns
  are also available as standalone Jupyter notebooks in a companion repository
  ([found here](https://github.com/initial-analysis-patterns/initial-analysis-patterns)).
- marimo notebooks are stored as plain Python files, which makes them easy to
  version and inspect; app mode hides the code so the tool can be used without
  reading it.
