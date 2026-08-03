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
def _(browser, pd, pm4py):
    # load event log from disk

    if len(browser.value) > 0:
        path = browser.value[0].id
        if path.lower().endswith(".csv"):
            event_log_from_disk = pd.read_csv(path)
        elif path.lower().endswith(".xes"):
            event_log_from_disk = pm4py.read_xes(path, variant="rustxes")
    else:
        event_log_from_disk = pd.DataFrame()

    print(len(event_log_from_disk), 'events loaded from disk.')
    return (event_log_from_disk,)


@app.cell(hide_code=True)
def _(code_editor, event_log_from_disk, pd, submit_button):
    # initialize the event log
    event_log = event_log_from_disk

    # columns that are filled for every row vs. columns that are not consistently filled
    fully_filled_columns = [ col for col in event_log.columns if event_log[col].notna().all() ]
    _inconsistent_columns = [ col for col in event_log.columns if col not in fully_filled_columns ]

    # from the fully filled columns, drop those that only ever take a single value
    _constant_columns = [ col for col in fully_filled_columns if event_log[col].nunique() <= 1 ]
    for _col in _constant_columns:
        _values = event_log[_col].unique()
        _value = _values[0] if len(_values) > 0 else None
        print(f"Dropping constant column '{_col}' with value: {_value}")
    event_log = event_log.drop(columns=_constant_columns)
    fully_filled_columns = [ col for col in fully_filled_columns if col not in _constant_columns ]

    # from the inconsistently filled columns, drop those that are completely empty
    _empty_columns = [ col for col in _inconsistent_columns if event_log[col].notna().sum() == 0 ]
    for _col in _empty_columns:
        print(f"Dropping empty column '{_col}'")
    event_log = event_log.drop(columns=_empty_columns)
    _inconsistent_columns = [ col for col in _inconsistent_columns if col not in _empty_columns ]

    # add manual enrichments here
    if submit_button.value:
        exec(code_editor.value)
        print('done')

    # add folding of inconsistent columns
    def fold_data(event):
        # activity = event[ACTIVITY]
        # non_standard_schema_columns = activity_schema[activity]
        dict = {k: v for k, v in event[_inconsistent_columns].items() if pd.notna(v)}
        return dict

    event_log['folded_data'] = event_log.apply(fold_data, axis=1)
    return event_log, fully_filled_columns


@app.cell(hide_code=True)
def _(fully_filled_columns, mo):
    # define mandatory columns to be user selected from all consistent columns

    DEFAULT_CASE_ID = "case:concept:name"
    DEFAULT_ACTIVITY = "concept:name"
    DEFAULT_COMPLETION_TIME = "time:timestamp"

    CASE_ID_dropdown = mo.ui.dropdown(
        options=fully_filled_columns,
        value=DEFAULT_CASE_ID if DEFAULT_CASE_ID in fully_filled_columns else fully_filled_columns[0],
        label="CASE ID column",
        allow_select_none=False,
        searchable=True,
    )

    COMPLETION_TIME_dropdown = mo.ui.dropdown(
        options=fully_filled_columns,
        value=DEFAULT_COMPLETION_TIME if DEFAULT_COMPLETION_TIME in fully_filled_columns else fully_filled_columns[1],
        label="COMPLETION TIME column",
        allow_select_none=False,
        searchable=True,
    )

    ACTIVITY_dropdown = mo.ui.dropdown(
        options=fully_filled_columns,
        value=DEFAULT_ACTIVITY if DEFAULT_ACTIVITY in fully_filled_columns else fully_filled_columns[2],
        label="ACTIVITY column",
        allow_select_none=False,
        searchable=True,
    )

    mo.vstack([
        mo.md("Select mandatory attributes from attributes that are fully filled:"),
        mo.hstack([CASE_ID_dropdown, COMPLETION_TIME_dropdown, ACTIVITY_dropdown])
    ])
    return ACTIVITY_dropdown, CASE_ID_dropdown, COMPLETION_TIME_dropdown


@app.cell(hide_code=True)
def _(
    ACTIVITY_dropdown,
    CASE_ID_dropdown,
    COMPLETION_TIME_dropdown,
    event_log,
    fully_filled_columns,
    pd,
):
    # Based on selected mandatory attributes, classify each attribute as mandatory, standard, or else

    CASE_ID = CASE_ID_dropdown.value
    ACTIVITY = ACTIVITY_dropdown.value
    COMPLETION_TIME = COMPLETION_TIME_dropdown.value

    MANDATORY_COLUMNS = [CASE_ID, ACTIVITY, COMPLETION_TIME]

    activity_stats = event_log[ACTIVITY].value_counts()
    activity_list = list(activity_stats.index)

    data = []
    for activity in list(activity_stats.index):
        filtered_log = event_log[event_log[ACTIVITY] == activity]
        _counts = { col: filtered_log[col].count() for col in event_log.columns}
        data.append(_counts)
    columns_per_activity = pd.DataFrame.from_records(data, index=activity_stats.index)

    # everywhere_non_empty_columns = [col for col in columns_per_activity.columns if (columns_per_activity[col] != 0).all()]

    STANDARD_COLUMNS = [col for col in fully_filled_columns if col not in MANDATORY_COLUMNS]

    activity_schema = {}
    activity_schema_population = {}
    for activity in list(activity_stats.index):
        non_empty_cols = [col for col in columns_per_activity.columns if (columns_per_activity[col][activity] != 0)]
        non_standard_schema_cols = [col for col in non_empty_cols if col not in MANDATORY_COLUMNS+STANDARD_COLUMNS]
        activity_schema[activity] = non_standard_schema_cols
        activity_schema_population[activity] = columns_per_activity[[CASE_ID]+STANDARD_COLUMNS+non_standard_schema_cols].loc[activity]

    # no_rows = len(columns_per_activity)
    # SHARED_COLUMNS = [col for col in columns_per_activity.columns if 2 <= (columns_per_activity[col] != 0).sum() < no_rows]

    # all remaining columns are not shared
    # anyway, we need to compute the schema for each activity separately and store it and then compute the enrichment from there
    return (
        ACTIVITY,
        CASE_ID,
        MANDATORY_COLUMNS,
        STANDARD_COLUMNS,
        activity_list,
        activity_stats,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## LOG VIEW

    3. schema population, with filter
    4. on top we have filters: case, activity (to show the schema)
    5. check whether we can do completeness inspection on top, or whether we need a new widget
    6. check how to add more case vis. on top, such as dotted chart
    """)
    return


@app.cell
def _(MANDATORY_COLUMNS, STANDARD_COLUMNS, event_log):
    event_log[MANDATORY_COLUMNS+STANDARD_COLUMNS+['folded_data']]
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Activity schema

    Select an activity of the log to see its schema, i.e., the set of attributes defined for the activity. You can also see how consistently the attribute is populated, i.e., how many events have a missing value.
    """)
    return


@app.cell(hide_code=True)
def _(activity_list, mo):
    activity_dropdown = mo.ui.dropdown(
        options=activity_list,
        label="Select Activity",
        value=activity_list[0]
    )
    return (activity_dropdown,)


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


    mo.hstack([activity_dropdown, attribute_dropdown], justify="start") # attribute_bin_selector, attribute_log_scale
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
def _(
    MANDATORY_COLUMNS,
    STANDARD_COLUMNS,
    attribute_bin_selector,
    attribute_histogram,
    events_of_selected_activity,
    mo,
):
    mo.ui.tabs({
        "Events": events_of_selected_activity[MANDATORY_COLUMNS+STANDARD_COLUMNS],
        "Histogram": mo.hstack([attribute_bin_selector, attribute_histogram]),
    })
    return


@app.cell(hide_code=True)
def _(
    ACTIVITY,
    CASE_ID,
    MANDATORY_COLUMNS,
    STANDARD_COLUMNS,
    activity_stats,
    event_log,
    pd,
):
    _data = []
    for _activity in list(activity_stats.index):
      _filtered_log = event_log[event_log[ACTIVITY] == _activity]
      counts = { col: _filtered_log[col].count() for col in event_log.columns if col != ACTIVITY}
      _data.append(counts)
    schema_usages = pd.DataFrame.from_records(_data, index=activity_stats.index)

    schema_usages['incidence'] = schema_usages[CASE_ID]

    _non_schema_columns = MANDATORY_COLUMNS + STANDARD_COLUMNS + ['folded_data', 'incidence']
    _extra_columns = [col for col in schema_usages.columns if col not in _non_schema_columns]

    schema_usages['extra_schema'] = schema_usages[_extra_columns].apply(
        lambda row: {col: value for col, value in row.items() if value != 0},
        axis=1
    )

    schema_usages['extra_schema_keys'] = schema_usages['extra_schema'].apply(
        lambda extra_schema: sorted(extra_schema.keys())
    )

    schema_usages['extra_schema_missing'] = schema_usages.apply(
        lambda row: {
            col: value - row['incidence']
            for col, value in row['extra_schema'].items()
            if value - row['incidence'] != 0
        },
        axis=1
    )

    _no_rows = len(schema_usages)
    partial_rows = [col for col in schema_usages.columns if 2 <= (schema_usages[col] != 0).sum() < _no_rows]

    partial_schema_usages = schema_usages[partial_rows]
    # schema_usages[['incidence', 'extra_schema_keys', 'extra_schema_missing']]
    return partial_schema_usages, schema_usages


@app.cell(hide_code=True)
def _(mo, partial_schema_usages, schema_usages):
    mo.ui.tabs({
        "Activity Schemas": schema_usages[['incidence', 'extra_schema_keys', 'extra_schema_missing']],
        "Schema Overlaps": partial_schema_usages[(partial_schema_usages != 0).any(axis=1)],
    })
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Event Enrichment
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    sample_enrichment = "event_log['weekday'] = event_log[COMPLETION_TIME].apply(lambda x: x.weekday())"

    code_editor = mo.ui.code_editor(
        value=sample_enrichment,
        language="python",
        label="Write your code here")

    submit_button = mo.ui.run_button(label="Submit")
    mo.vstack([code_editor, submit_button])
    return code_editor, submit_button


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
