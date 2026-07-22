import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Exploratory Process Mining
    """)
    return


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import pandas as pd 
    import pm4py
    import altair as alt
    alt.data_transformers.enable("vegafusion")
    import plotly.express as px


    return mo, pd, pm4py, px


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Select a data set
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    #| slide: continue
    browser = mo.ui.file_browser(filetypes=['.csv', '.xes'], multiple=False)
    browser
    return (browser,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    This is the loaded event log:
    """)
    return


@app.cell(hide_code=True)
def _(browser, pd, pm4py):
    if len(browser.value) > 0:
        path = browser.value[0].id
        if path.lower().endswith(".csv"):
            event_log = pd.read_csv(path)
        elif path.lower().endswith(".xes"):
            event_log = pm4py.read_xes(path, variant="rustxes")
    else:
        event_log = pd.DataFrame()

    event_log
    return (event_log,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Select mandatory event log attributes

    Define which attributes of the event log define the Case Identifier, the Completion Time and the Activity Name of each event.
    """)
    return


@app.cell(hide_code=True)
def _(event_log, mo):
    all_cols = event_log.columns.tolist()

    DEFAULT_CASE_ID = "case:concept:name"
    DEFAULT_ACTIVITY = "concept:name"
    DEFAULT_COMPLETION_TIME = "time:timestamp"

    CASE_ID_dropdown = mo.ui.dropdown(
        options=all_cols,
        value=DEFAULT_CASE_ID if DEFAULT_CASE_ID in all_cols else all_cols[0],
        label="CASE ID column",
        allow_select_none=False,
        searchable=True,
    )

    COMPLETION_TIME_dropdown = mo.ui.dropdown(
        options=all_cols,
        value=DEFAULT_COMPLETION_TIME if DEFAULT_COMPLETION_TIME in all_cols else all_cols[1],
        label="COMPLETION TIME column",
        allow_select_none=False,
        searchable=True,
    )

    ACTIVITY_dropdown = mo.ui.dropdown(
        options=all_cols,
        value=DEFAULT_ACTIVITY if DEFAULT_ACTIVITY in all_cols else all_cols[2],
        label="ACTIVITY column",
        allow_select_none=False,
        searchable=True,
    )

    mo.hstack([CASE_ID_dropdown, COMPLETION_TIME_dropdown, ACTIVITY_dropdown])
    return ACTIVITY_dropdown, CASE_ID_dropdown, COMPLETION_TIME_dropdown


@app.cell(hide_code=True)
def _(ACTIVITY_dropdown, CASE_ID_dropdown, COMPLETION_TIME_dropdown):
    CASE_ID = CASE_ID_dropdown.value
    ACTIVITY = ACTIVITY_dropdown.value
    COMPLETION_TIME = COMPLETION_TIME_dropdown.value

    MANDATORY_COLUMNS = [CASE_ID, ACTIVITY, COMPLETION_TIME]
    return ACTIVITY, CASE_ID, COMPLETION_TIME


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Activity schema

    Select an activity of the log to see its schema, i.e., the set of attributes defined for the activity. You can also see how consistently the attribute is populated, i.e., how many events have a missing value.
    """)
    return


@app.cell(hide_code=True)
def _(ACTIVITY, event_log, mo):
    activity_stats = event_log[ACTIVITY].value_counts()
    activity_list = list(activity_stats.index)

    activity_dropdown = mo.ui.dropdown(
        options=activity_list,
        label="Select Activity",
        value=activity_list[0]
    )
    return activity_dropdown, activity_stats


@app.cell(hide_code=True)
def _(ACTIVITY, activity_dropdown, event_log, mo):
    events_of_selected_activity = event_log[event_log[ACTIVITY] == activity_dropdown.value]
    events_of_selected_activity = events_of_selected_activity.dropna(axis=1, how="all")

    selectable_attributes = events_of_selected_activity.columns.tolist() 

    # UI: dropdown to choose column
    attribute_dropdown = mo.ui.dropdown(
        options=selectable_attributes,
        value=selectable_attributes[0] if selectable_attributes else None,
        label="Select attribute"
    )
    return attribute_dropdown, events_of_selected_activity


@app.cell(hide_code=True)
def _(activity_dropdown, attribute_dropdown, mo):
    attribute_bin_selector = mo.ui.number(
        start=1, stop=None, step=1, label="Enter number of bins", value=None
    )

    attribute_log_scale = mo.ui.checkbox(label="Y-axis log scale", value=False)


    mo.hstack([activity_dropdown, attribute_dropdown, attribute_bin_selector, attribute_log_scale], justify="start")
    return attribute_bin_selector, attribute_log_scale


@app.cell(hide_code=True)
def _(
    attribute_bin_selector,
    attribute_dropdown,
    attribute_log_scale,
    events_of_selected_activity,
    px,
):
    if attribute_dropdown.value:
        attribute_histogram = px.histogram(
            events_of_selected_activity,
            x=attribute_dropdown.value,
            nbins=attribute_bin_selector.value,
            log_y=attribute_log_scale.value,
            marginal='rug'
        )
    return (attribute_histogram,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    TODO: Work on events tab: mandatory columns then selected, then all other of the schema
    """)
    return


@app.cell(hide_code=True)
def _(attribute_histogram, events_of_selected_activity, mo):
    mo.ui.tabs({
        "Events": events_of_selected_activity,
        "Histogram": attribute_histogram,
    })
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Case Inspection

    The following table allows you to see all data of a selected case. Use the "Freeze left" feature of the widget to focus on the most relevant attributes.
    """)
    return


@app.cell(hide_code=True)
def _(CASE_ID, event_log, mo):
    all_case_ids = event_log[CASE_ID].unique().tolist()

    case_selector = mo.ui.dropdown(
        options=all_case_ids,
        label="Select case",
        value=all_case_ids[0],
        searchable=True
    )

    case_selector
    return (case_selector,)


@app.cell(hide_code=True)
def _(ACTIVITY, CASE_ID, COMPLETION_TIME, case_selector, event_log):
    case_data = event_log[event_log[CASE_ID] == case_selector.value]
    fixed_columns = [CASE_ID, ACTIVITY, COMPLETION_TIME]
    other_columns = event_log.columns.difference(fixed_columns).to_list()

    case_data[fixed_columns+other_columns]
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    TODO: Put the simplified view
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Schema Population and Overlap

    The follwoing table shows, for each activity and each log attribute, the number of events that have a non-NAN value.
    """)
    return


@app.cell(hide_code=True)
def _(ACTIVITY, activity_stats, event_log, pd):
    _data = []
    for _activity in list(activity_stats.index):
      _filtered_log = event_log[event_log[ACTIVITY] == _activity]
      counts = { col: _filtered_log[col].count() for col in event_log.columns if col != ACTIVITY}
      _data.append(counts)
    schema_usages = pd.DataFrame.from_records(_data, index=activity_stats.index)

    schema_usages
    return (schema_usages,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Schema Overlap

    The following table simplifies the previous by only showing attributes of the event log that a part of the schema of multiple but not all activities.
    """)
    return


@app.cell(hide_code=True)
def _(schema_usages):
    _no_rows = len(schema_usages)
    partial_rows = [col for col in schema_usages.columns if 2 <= (schema_usages[col] != 0).sum() < _no_rows]

    schema_usages[partial_rows]
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## TODO: Case log

    - add case log
    - have a histogram on case attributes
    - have a scatter plot on case attributes
    """)
    return


if __name__ == "__main__":
    app.run()
