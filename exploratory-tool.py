import marimo

__generated_with = "0.24.0"
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
    import importlib
    import temporal_characteristics_util as tcu
    importlib.reload(tcu)
    import attribute_util as au
    importlib.reload(au)
    import data_quality_util as dqu
    importlib.reload(dqu)
    return au, dqu, mo, pd, pm4py, px, tcu


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
    # Load event log from disk

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
def _(mo):
    mo.md(r"""
    ## Temporal Characteristics of the Log
    """)
    return


@app.cell(hide_code=True)
def _(event_log, event_log_from_disk, pd, tcu):
    # Show the format used by all timestamp columns

    _timestamp_columns = [
        col
        for col in event_log.columns
        if (
            isinstance(event_log[col].dtype, pd.DatetimeTZDtype)
            or pd.api.types.is_datetime64_dtype(event_log_from_disk[col])
        )
    ]

    _format_results = []

    for _col in _timestamp_columns:
        _result = tcu.infer_timestamp_format_from_column(event_log_from_disk[_col])

        _format_results.append({
            "Timestamp column": _col,
            "Status": _result["status"],
            "Format": _result["format"],
        })

    timestamp_format_summary = pd.DataFrame(_format_results)

    timestamp_format_summary
    return


@app.cell(hide_code=True)
def _(event_log_from_disk, mo, tcu):
    # Show the granularity level of the encoded timestamps in the log, including whether timestamp components and timezone are constant
    timestamp_component_summary, timestamp_constant_prefixes = tcu.analyze_timestamp_components(event_log_from_disk)
    mo.ui.tabs({
        "Component analysis": timestamp_component_summary,
        "Constant prefixes": timestamp_constant_prefixes,
    })
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Initialize the Event Log

    In this stage, a common time zone and granularity are applied to all timestamp columns in the log; uninformative columns and duplicated events are dropped; and enrichments are applied.
    """)
    return


@app.cell(hide_code=True)
def _(event_log_from_disk, mo):
    # identify columns that are filled for every row
    fully_filled_columns = [ col for col in event_log_from_disk.columns if event_log_from_disk[col].notna().all() ]

    _constant_columns = [ col for col in fully_filled_columns if event_log_from_disk[col].nunique() <= 1]
    fully_filled_columns = [ col for col in fully_filled_columns if col not in _constant_columns ]

    checkbox = mo.ui.checkbox(label="Enforce global ordering of the event log by completion time")
    return checkbox, fully_filled_columns


@app.cell(hide_code=True)
def _(checkbox, mo):
    import pytz
    from datetime import datetime

    _common_timezones = pytz.common_timezones

    _default_timezone = "UTC" if "UTC" in _common_timezones else _common_timezones[0]

    GRANULARITY_LEVELS = ['year', 'month', 'day', 'hour', 'minute', 'second', 'millisecond', 'sub-millisecond']

    timezone_dropdown = mo.ui.dropdown(
        options=_common_timezones,
        value=_default_timezone,
        label="Select Time Zone",
        allow_select_none=False,
        searchable=True,
    )

    granularity_normalization_dropdown = mo.ui.dropdown(
        options=GRANULARITY_LEVELS,
        value=None,
        label="Select granularity level",
        allow_select_none=True,
    )

    mo.vstack([
        mo.md("## Time-related Log Initialization Options"),
        mo.md("Select a time zone to apply to all timestamp columns in the event log and case log:"),
        mo.hstack([timezone_dropdown], justify="start"),
        mo.md("(Optional) Select a granularity level to apply to all timestamp columns in the event log and case log:"),
        mo.hstack([granularity_normalization_dropdown], justify="start"),
        checkbox
    ])
    return granularity_normalization_dropdown, timezone_dropdown


@app.cell(hide_code=True)
def _(fully_filled_columns, mo):
    # Define mandatory columns to be user selected from all consistent columns

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
        mo.md("## Mandatory Attribute Specification"),
        mo.md("Select mandatory attributes from attributes that are fully filled:"),
        mo.hstack([CASE_ID_dropdown, COMPLETION_TIME_dropdown, ACTIVITY_dropdown])
    ])
    return ACTIVITY_dropdown, CASE_ID_dropdown, COMPLETION_TIME_dropdown


@app.cell(hide_code=True)
def _(
    CASE_ID_dropdown,
    COMPLETION_TIME_dropdown,
    au,
    checkbox,
    dqu,
    event_enrichment_code_editor,
    event_enrichment_submit_button,
    event_log_from_disk,
    granularity_normalization_dropdown,
    mo,
    pd,
    tcu,
    timezone_dropdown,
):
    # Initialize the event log
    event_log = event_log_from_disk

    # apply the selected timezone to all timestamp columns
    _selected_timezone = timezone_dropdown.value

    for _col in event_log.columns:
        if isinstance(event_log[_col].dtype, pd.DatetimeTZDtype):
            event_log[_col] = event_log[_col].dt.tz_convert(_selected_timezone)
            print('Converting column', _col, 'to timezone', _selected_timezone)

    # apply the selected timestamp granularity to all timestamp columns
    _target_granularity = granularity_normalization_dropdown.value

    if _target_granularity is not None:
        if _target_granularity not in tcu._FREQ_ALIASES:
            print(
                f"Granularity normalization to '{_target_granularity}' "
                "is currently not supported."
            )
        else:
            _freq = tcu._FREQ_ALIASES[_target_granularity]

            # apply to all timestamp columns
            for _col in event_log.columns:
                if isinstance(event_log[_col].dtype, pd.DatetimeTZDtype) or pd.api.types.is_datetime64_dtype(event_log[_col]):
                    _original = event_log[_col]
                    _rounded = _original.dt.round(_freq)

                    _changed = (_rounded != _original).sum()

                    event_log[_col] = _rounded

                    print(
                        f"Rounded {_changed}/{len(_original)} values in "
                        f"'{_col}' to the nearest {_target_granularity}"
                    )

    # columns that are filled for every row vs. columns that are not consistently filled
    _fully_filled_columns = [ col for col in event_log.columns if event_log[col].notna().all() ]
    _inconsistent_columns = [ col for col in event_log.columns if col not in _fully_filled_columns ]

    # from the fully filled columns, drop those that only ever take a single value
    _constant_columns = [ col for col in _fully_filled_columns if event_log[col].nunique() <= 1 ]
    for _col in _constant_columns:
        _values = event_log[_col].unique()
        _value = _values[0] if len(_values) > 0 else None
        print(f"Dropping constant column '{_col}' with value: {_value}")
    event_log = event_log.drop(columns=_constant_columns)
    #fully_filled_columns = [ col for col in fully_filled_columns if col not in _constant_columns ]

    # from the inconsistently filled columns, drop those that are completely empty
    _empty_columns = [ col for col in _inconsistent_columns if event_log[col].notna().sum() == 0 ]
    for _col in _empty_columns:
        print(f"Dropping empty column '{_col}'")
    event_log = event_log.drop(columns=_empty_columns)
    _inconsistent_columns = [ col for col in _inconsistent_columns if col not in _empty_columns ]

    # add manual enrichments here
    if event_enrichment_submit_button.value:
        exec(event_enrichment_code_editor.value)
        print('done')

    # find attribute pairs that encode the same information
    redundant_attribute_candidates = au.find_redundant_attribute_pairs(event_log)

    # check for and remove events that are exact duplicates of another event
    duplicate_event_instances = dqu.summarize_duplicate_events(event_log)

    if not duplicate_event_instances.empty:
        _events_before = len(event_log)
        event_log = dqu.remove_duplicate_events(event_log)
        print(
            f"Removed {_events_before - len(event_log)} duplicate events "
            f"in {len(duplicate_event_instances)} groups of identical events"
        )

    # Based on the selected COMPLETION TIME column, check whether events are ordered by completion time within each case and across the log
    case_ordering_summary, log_ordering_summary = tcu.analyze_event_ordering(
        event_log, CASE_ID_dropdown.value, COMPLETION_TIME_dropdown.value
    )

    # Based on whether the checkbox was checked, order the event log
    if checkbox.value:
        event_log['original_order'] = range(len(event_log))

        event_log = event_log.sort_values(
            by=[
                COMPLETION_TIME_dropdown.value,
                'original_order'
            ]
        ).reset_index(drop=True)

        assert event_log[
            COMPLETION_TIME_dropdown.value
        ].is_monotonic_increasing
        print("All events in the log are now globally ordered.")

    # add folding of inconsistent columns
    def fold_data(event):
        # activity = event[ACTIVITY]
        # non_standard_schema_columns = activity_schema[activity]
        dict = {k: v for k, v in event[_inconsistent_columns].items() if pd.notna(v)}
        return dict if dict else None

    event_log['folded_data'] = event_log.apply(fold_data, axis=1)

    # Show one kept instance per group of duplicate events
    mo.vstack([
        mo.md("The following events had duplicates that have been removed, retaining only one:"),
        duplicate_event_instances,  
        #mo.md("Assessment of the log ordering before reordering was applied:"),
        #mo.ui.tabs({
        #    "Case-wise ordering": case_ordering_summary,
        #    "Global ordering": log_ordering_summary,
        #})
    ])
    return event_log, redundant_attribute_candidates


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

    # create a preliminary case log from the case features in the event log

    # compute case features: columns that take at most one unique (non-null) value per case,
    # i.e. 0 (all NaN) or 1 unique value within each case group
    _case_groups = event_log.groupby(CASE_ID)

    CASE_FEATURE_COLUMNS = [
        col for col in event_log.columns
        if col != CASE_ID
        and col != 'folded_data'
        and _case_groups[col].apply(lambda s: s.dropna().nunique()).max() <= 1
    ]

    print("Case feature columns (unique value per case, possibly NaN):", CASE_FEATURE_COLUMNS)
    return (
        ACTIVITY,
        CASE_FEATURE_COLUMNS,
        CASE_ID,
        MANDATORY_COLUMNS,
        STANDARD_COLUMNS,
        activity_list,
        activity_stats,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## EVENT LOG VIEW

    - use for overview or filter for a specific case, activity, or time period
    """)
    return


@app.cell(hide_code=True)
def _(
    CASE_FEATURE_COLUMNS,
    MANDATORY_COLUMNS,
    STANDARD_COLUMNS,
    case_log,
    initialized_event_log,
    mo,
):
    mo.ui.tabs({
        "Event Log": initialized_event_log[[col for col in MANDATORY_COLUMNS+STANDARD_COLUMNS+['folded_data'] if col not in CASE_FEATURE_COLUMNS]],
        "Case Log": case_log
    })
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## ACTIVITY SCHEMA VIEW
    """)
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

    if _extra_columns:
        schema_usages['extra_schema'] = schema_usages[_extra_columns].apply(
            lambda row: {col: value for col, value in row.items() if value != 0},
            axis=1
        )
    else:
        schema_usages['extra_schema'] = [{} for _ in range(len(schema_usages))]

    schema_usages['extra_schema_keys'] = schema_usages['extra_schema'].apply(
        lambda extra_schema: sorted(extra_schema.keys())
    )

    schema_usages['missing_values'] = schema_usages.apply(
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
    # schema_usages[['incidence', 'extra_schema_keys', 'missing_values']]
    return partial_schema_usages, schema_usages


@app.cell(hide_code=True)
def _(mo, partial_schema_usages, schema_usages):
    mo.ui.tabs({
        "Activity Schemas": schema_usages[['incidence', 'extra_schema_keys', 'missing_values']],
        "Schema Overlaps": partial_schema_usages[(partial_schema_usages != 0).any(axis=1)],
    })
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

    selectable_attributes = [ a for a in events_of_selected_activity.columns.tolist() if a != 'folded_data' ]

    # UI: dropdown to choose column
    attribute_dropdown = mo.ui.dropdown(
        options=selectable_attributes,
        value=selectable_attributes[0] if selectable_attributes else None,
        label="Select attribute"
    )
    return attribute_dropdown, events_of_selected_activity


@app.cell(hide_code=True)
def _(activity_dropdown, attribute_dropdown, mo):
    attribute_bin_selector = mo.ui.number(label="Enter number of bins", value=None)
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
def _(
    MANDATORY_COLUMNS,
    STANDARD_COLUMNS,
    activity_dropdown,
    attribute_bin_selector,
    attribute_histogram,
    events_of_selected_activity,
    mo,
    schema_usages,
):
    _events_extra_columns = schema_usages.loc[activity_dropdown.value, 'extra_schema_keys']

    mo.ui.tabs({
        "Histogram": mo.vstack([attribute_bin_selector, attribute_histogram]),
        "Events": events_of_selected_activity[MANDATORY_COLUMNS+STANDARD_COLUMNS+_events_extra_columns]
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
    _sample_enrichment = "event_log['weekday'] = event_log['time:timestamp'].apply(lambda x: x.weekday())"

    event_enrichment_code_editor = mo.ui.code_editor(
        value=_sample_enrichment,
        language="python",
        label="Write your code here")

    event_enrichment_submit_button = mo.ui.run_button(label="Submit")
    mo.vstack([event_enrichment_code_editor, event_enrichment_submit_button])
    return event_enrichment_code_editor, event_enrichment_submit_button


@app.cell
def _(mo):
    _sample_enrichment = "case_log['duration'] = case_log['end_time'] - case_log['start_time']"

    case_enrichment_code_editor = mo.ui.code_editor(
        value=_sample_enrichment,
        language="python",
        label="Write your code here")

    case_enrichment_submit_button = mo.ui.run_button(label="Submit")
    mo.vstack([case_enrichment_code_editor, case_enrichment_submit_button])
    return case_enrichment_code_editor, case_enrichment_submit_button


@app.cell(hide_code=True)
def _(
    CASE_FEATURE_COLUMNS,
    CASE_ID,
    case_enrichment_code_editor,
    case_enrichment_submit_button,
    initialized_event_log,
):
    cases = initialized_event_log.groupby(CASE_ID)
    case_log = cases.agg(
        start_time=('time:timestamp','first'),
        end_time=('time:timestamp', 'last'),
        no_of_events=('concept:name', 'count'),
        **{col: (col, 'first') for col in CASE_FEATURE_COLUMNS}
    )

    # add manual enrichments here
    if case_enrichment_submit_button.value:
        exec(case_enrichment_code_editor.value)
        print('done')
    return (case_log,)


@app.cell(hide_code=True)
def _(case_log, mo):
    _categorical_case_columns = case_log.reset_index().select_dtypes(include=["number", "object", "category", "bool", "datetime", "datetimetz"]).columns.tolist()

    x_axis_dropdown = mo.ui.dropdown(
        options=_categorical_case_columns,
        value=_categorical_case_columns[0] if _categorical_case_columns else None,
        label="X-axis",
        allow_select_none=False,
        searchable=True,
    )

    y_axis_dropdown = mo.ui.dropdown(
        options=_categorical_case_columns,
        value=_categorical_case_columns[1] if len(_categorical_case_columns) > 1 else (_categorical_case_columns[0] if _categorical_case_columns else None),
        label="Y-axis",
        allow_select_none=False,
        searchable=True,
    )

    mo.hstack([x_axis_dropdown, y_axis_dropdown], justify="start")
    return x_axis_dropdown, y_axis_dropdown


@app.cell(hide_code=True)
def _(case_log, px, x_axis_dropdown, y_axis_dropdown):
    case_log_reset = case_log.reset_index()

    case_scatter_fig = px.scatter(
        case_log_reset,
        x=x_axis_dropdown.value,
        y=y_axis_dropdown.value,
        hover_data=case_log_reset.columns.tolist(),
        title=f"{y_axis_dropdown.value} vs {x_axis_dropdown.value}",
        labels={
            x_axis_dropdown.value: x_axis_dropdown.value,
            y_axis_dropdown.value: y_axis_dropdown.value,
        },
    )
    case_scatter_fig.update_traces(marker=dict(size=8, opacity=0.7))
    case_scatter_fig
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Attributes
    """)
    return


@app.cell(hide_code=True)
def _(mo, redundant_attribute_candidates):
    # Select a pair of redundant attribute candidates to inspect
    _pair_labels = {
        f"{_row.attribute_a} <-> {_row.attribute_b} ({_row.n_values} values)": _row.Index
        for _row in redundant_attribute_candidates.itertuples()
    }

    redundant_pair_dropdown = mo.ui.dropdown(
        options=_pair_labels,
        value=next(iter(_pair_labels), None),
        label="Select attribute pair",
        searchable=True,
    )

    mo.vstack([
        mo.md("Select a pair of redundant attribute candidates, i.e., attributes that show information in a one-to-one relation, to inspect:"),
        redundant_pair_dropdown
    ])
    return (redundant_pair_dropdown,)


@app.cell(hide_code=True)
def _(mo, pd, redundant_attribute_candidates, redundant_pair_dropdown):
    # Show attribute pairs that encode the same information through a one-to-one value mapping
    if redundant_attribute_candidates.empty:
        redundant_pair_overview = pd.DataFrame(
            columns=['attribute_a', 'attribute_b', 'n_values']
        )
        redundant_pair_mapping = pd.DataFrame()
    else:
        redundant_pair_overview = redundant_attribute_candidates[
            ['attribute_a', 'attribute_b', 'n_values']
        ]
        _row = redundant_attribute_candidates.loc[redundant_pair_dropdown.value]
        redundant_pair_mapping = pd.DataFrame({
            _row['attribute_a']: list(_row['mapping'].keys()),
            _row['attribute_b']: list(_row['mapping'].values()),
        })

    mo.ui.tabs({
        "Redundant attribute candidate pairs": redundant_pair_overview,
        "Selected mapping": redundant_pair_mapping,
    })
    return


if __name__ == "__main__":
    app.run()
