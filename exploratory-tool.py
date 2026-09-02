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
    from pathlib import Path
    import importlib
    import temporal_characteristics_util as tcu
    tcu = importlib.reload(tcu)
    import attribute_util as au
    au = importlib.reload(au)
    import data_quality_util as dqu
    dqu = importlib.reload(dqu)
    import structure_util as su
    su = importlib.reload(su)
    return Path, au, dqu, mo, pd, pm4py, px, tcu


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Select a data set
    """)
    return


@app.cell(hide_code=True)
def _(Path, mo):
    #| slide: continue
    browser = mo.ui.file_browser(initial_path=Path.cwd(), filetypes=['.csv', '.xes'], multiple=False)
    browser
    return (browser,)


@app.cell(hide_code=True)
def _(browser, mo, pd, pm4py):
    # Load event log from disk

    mo.stop(
        len(browser.value) == 0,
        mo.md("**Select an event log to start the analysis.**"),
    )


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
    ## Timestamp Attributes in the Log
    """)
    return


@app.cell(hide_code=True)
def _(event_log_from_disk, mo, pd, tcu):
    # Show the format used by all timestamp columns
    _timestamp_columns = [
        col
        for col in event_log_from_disk.columns
        if (
            isinstance(event_log_from_disk[col].dtype, pd.DatetimeTZDtype)
            or pd.api.types.is_datetime64_dtype(event_log_from_disk[col])
        )
    ]

    _format_results = []

    for _col in _timestamp_columns:
        _result = tcu.infer_timestamp_format_from_column(event_log_from_disk[_col])

        _format_results.append({
            "Timestamp column": _col,
            "Status": _result["status"],
            "Format": tcu.format_to_human(_result["format"]),
            "Example": tcu.get_example_timestamp(event_log_from_disk[_col], _result["format"]),
            "Pattern": _result["format"],
        })

    timestamp_format_summary = pd.DataFrame(_format_results)

    mo.vstack([
        mo.md("Showing the format of each timestamp column, if unambiguously detected from the data recorded therein:"),
        timestamp_format_summary
    ])
    return


@app.cell(hide_code=True)
def _(event_log_from_disk, mo, pd):
    # Select a timestamp attribute to inspect
    _timestamp_attributes = [
        col
        for col in event_log_from_disk.columns
        if (
            isinstance(event_log_from_disk[col].dtype, pd.DatetimeTZDtype)
            or pd.api.types.is_datetime64_dtype(event_log_from_disk[col])
        )
    ]

    timestamp_attribute_dropdown = mo.ui.dropdown(
        options=_timestamp_attributes,
        value=_timestamp_attributes[0] if _timestamp_attributes else None,
        label="Timestamp attribute: ",
        searchable=True,
    )

    mo.vstack([
        mo.md("Select a timestamp attribute to inspect:"),
        timestamp_attribute_dropdown
    ])
    return (timestamp_attribute_dropdown,)


@app.cell(hide_code=True)
def _(event_log_from_disk, mo, tcu, timestamp_attribute_dropdown):
    # Show the granularity level of the encoded timestamps in the log, including whether timestamp components and timezone are constant
    timestamp_component_summary, timestamp_constant_prefixes = tcu.analyze_timestamp_components(event_log_from_disk)

    _selected_timestamp = timestamp_attribute_dropdown.value

    _component_view = timestamp_component_summary[
        timestamp_component_summary['Timestamp column'] == _selected_timestamp
    ].drop(columns='Timestamp column')

    _prefix_view = timestamp_constant_prefixes[
        timestamp_constant_prefixes['Timestamp column'] == _selected_timestamp
    ].drop(columns='Timestamp column')

    mo.vstack([
        mo.md(
            f"Showing the precision of '{_selected_timestamp}' and whether any timestamp "
            "elements are constant, based on the data recorded therein:"
        ),
        mo.ui.tabs({
            "Component analysis": _component_view,
            "Constant prefixes": _prefix_view,
        }),
    ])
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
def _(checkbox, fully_filled_columns, mo):
    import pytz
    from datetime import datetime

    _common_timezones = pytz.common_timezones

    _default_timezone = "UTC" if "UTC" in _common_timezones else _common_timezones[0]

    GRANULARITY_LEVELS = ['year', 'month', 'day', 'hour', 'minute', 'second', 'millisecond', 'sub-millisecond']

    # Define mandatory columns to be user selected from all consistent columns

    DEFAULT_CASE_ID = "case:concept:name"
    DEFAULT_ACTIVITY = "concept:name"
    DEFAULT_COMPLETION_TIME = "time:timestamp"

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
        mo.md("## Log Initialization"),
        mo.md("Select a time zone to apply to all timestamp columns in the event log and case log:"),
        mo.hstack([timezone_dropdown], justify="start"),
        mo.md("(Optional) Select a granularity level to apply to all timestamp columns in the event log and case log:"),
        mo.hstack([granularity_normalization_dropdown], justify="start"),
        checkbox,
        mo.md("Select mandatory attributes from attributes that are fully filled:"),
        mo.hstack([CASE_ID_dropdown, COMPLETION_TIME_dropdown, ACTIVITY_dropdown])
    ])
    return (
        ACTIVITY_dropdown,
        CASE_ID_dropdown,
        COMPLETION_TIME_dropdown,
        granularity_normalization_dropdown,
        timezone_dropdown,
    )


@app.cell(hide_code=True)
def _(
    CASE_ID_dropdown,
    COMPLETION_TIME_dropdown,
    event_log_from_disk,
    mo,
    pd,
    tcu,
):
    # Select a time frame; only cases that start and end within it are included in the event log
    _case_bounds = tcu.get_case_time_bounds(
        event_log_from_disk, CASE_ID_dropdown.value, COMPLETION_TIME_dropdown.value
    )

    CASE_WINDOW_START = _case_bounds['min'].min()
    _last_timestamp = _case_bounds['max'].max()

    # a day-resolution slider unless the log spans less than two days
    CASE_WINDOW_UNIT = 'D' if (_last_timestamp - CASE_WINDOW_START) >= pd.Timedelta(days=2) else 'h'
    _unit_length = pd.Timedelta(1, CASE_WINDOW_UNIT)

    DEFAULT_CASE_COUNT = 100
    _default_end = tcu.get_end_time_of_nth_case(_case_bounds, DEFAULT_CASE_COUNT)

    case_window_slider = mo.ui.range_slider(
        start=0,
        stop=int((_last_timestamp - CASE_WINDOW_START) / _unit_length) + 1,
        step=1,
        value=[0, int((_default_end - CASE_WINDOW_START) / _unit_length) + 1],
        label=f"Time frame in {'days' if CASE_WINDOW_UNIT == 'D' else 'hours'} after {CASE_WINDOW_START}",
        full_width=True,
    )

    mo.vstack([
        mo.md("Select a time frame. Only cases that both start and end within it are "
            f"included for analysis. The initial selection covers the first {DEFAULT_CASE_COUNT} cases."
        ),
        case_window_slider
    ])
    return CASE_WINDOW_START, CASE_WINDOW_UNIT, case_window_slider


@app.cell(hide_code=True)
def _(
    CASE_ID_dropdown,
    CASE_WINDOW_START,
    CASE_WINDOW_UNIT,
    COMPLETION_TIME_dropdown,
    au,
    case_window_slider,
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

    _messages = []

    # apply the selected timezone to all timestamp columns
    _selected_timezone = timezone_dropdown.value

    for _col in event_log.columns:
        if isinstance(event_log[_col].dtype, pd.DatetimeTZDtype):
            event_log[_col] = event_log[_col].dt.tz_convert(_selected_timezone)
            _messages.append(f"Converted column '{_col}' to timezone {_selected_timezone}")

    # apply the selected timestamp granularity to all timestamp columns
    _target_granularity = granularity_normalization_dropdown.value

    if _target_granularity is not None:
        if _target_granularity not in tcu._FREQ_ALIASES:
            _messages.append(
                f"Granularity normalization to '{_target_granularity}' is currently not supported."
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

                    _messages.append(
                        f"Rounded {_changed}/{len(_original)} values in "
                        f"'{_col}' to the nearest {_target_granularity}"
                    )

    # keep only the cases that start and end within the selected time frame
    _window_start = CASE_WINDOW_START + pd.Timedelta(case_window_slider.value[0], CASE_WINDOW_UNIT)
    _window_end = CASE_WINDOW_START + pd.Timedelta(case_window_slider.value[1], CASE_WINDOW_UNIT)

    _cases_before = event_log[CASE_ID_dropdown.value].nunique()

    event_log = tcu.filter_cases_within_window(
        event_log, CASE_ID_dropdown.value, COMPLETION_TIME_dropdown.value,
        _window_start, _window_end
    )

    _messages.append(
        f"Time frame {_window_start} to {_window_end}: kept "
        f"{event_log[CASE_ID_dropdown.value].nunique()} of {_cases_before} cases "
        f"({len(event_log)} events)"
    )

    # columns that are filled for every row vs. columns that are not consistently filled
    _fully_filled_columns = [ col for col in event_log.columns if event_log[col].notna().all() ]
    _inconsistent_columns = [ col for col in event_log.columns if col not in _fully_filled_columns ]

    # from the fully filled columns, drop those that only ever take a single value
    _constant_columns = [ col for col in _fully_filled_columns if event_log[col].nunique() <= 1 ]
    for _col in _constant_columns:
        _values = event_log[_col].unique()
        _value = _values[0] if len(_values) > 0 else None
        _messages.append(f"Dropped constant column '{_col}' with value: {_value}")
    event_log = event_log.drop(columns=_constant_columns)

    # from the inconsistently filled columns, drop those that are completely empty
    _empty_columns = [ col for col in _inconsistent_columns if event_log[col].notna().sum() == 0 ]
    for _col in _empty_columns:
        _messages.append(f"Dropped empty column '{_col}'")
    event_log = event_log.drop(columns=_empty_columns)
    _inconsistent_columns = [ col for col in _inconsistent_columns if col not in _empty_columns ]

    # add manual enrichments here
    if event_enrichment_submit_button.value:
        exec(event_enrichment_code_editor.value)
        _messages.append("Applied the manual event enrichment")

    # find attribute pairs that encode the same information
    redundant_attribute_candidates = au.find_redundant_attribute_pairs(event_log)

    # check for and remove events that are exact duplicates of another event
    duplicate_event_instances = dqu.summarize_duplicate_events(event_log)

    if not duplicate_event_instances.empty:
        _events_before = len(event_log)
        event_log = dqu.remove_duplicate_events(event_log)
        _messages.append(
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
        _messages.append("All events in the log are now globally ordered.")

    # add folding of inconsistent columns
    def fold_data(event):
        # activity = event[ACTIVITY]
        # non_standard_schema_columns = activity_schema[activity]
        dict = {k: v for k, v in event[_inconsistent_columns].items() if pd.notna(v)}
        return dict if dict else None

    event_log['folded_data'] = event_log.apply(fold_data, axis=1)

    # report what the initialization did, and show one kept instance per group of duplicate events
    _output = [mo.md("\n".join(f"- {_message}" for _message in _messages))]

    if not duplicate_event_instances.empty:
        _output.append(mo.md("The following events had duplicates that have been removed, retaining only one:"))
        _output.append(duplicate_event_instances)

    mo.vstack([mo.md("### Summary of the Initialization"),
              *_output
              ])
    return event_log, redundant_attribute_candidates


@app.cell(hide_code=True)
def _(
    ACTIVITY_dropdown,
    CASE_ID_dropdown,
    COMPLETION_TIME_dropdown,
    au,
    checkbox,
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

    # summarize how each attribute is classified and populated
    def _classify_attribute(col, activity_type_count):
        if col in MANDATORY_COLUMNS:
            return 'mandatory'
        if col in STANDARD_COLUMNS:
            return 'standard'
        # non-standard attributes are shared if more than one activity type writes them
        return 'non-standard, shared' if activity_type_count > 1 else 'non-standard, exclusive'

    # check monotonicity over time for the numeric attributes
    _numeric_attributes = [
        col for col in event_log.columns
        if col != 'folded_data' and pd.api.types.is_numeric_dtype(event_log[col])
    ]

    monotonicity_overview = au.get_monotonicity_per_attribute(
        event_log, CASE_ID, COMPLETION_TIME, _numeric_attributes,
        check_log_level=checkbox.value,
    )

    attribute_overview = pd.DataFrame([
        {
            'Attribute': col,
            'Classification': _classify_attribute(
                col, int((columns_per_activity[col] != 0).sum())
            ),
            'Level': 'case' if col in CASE_FEATURE_COLUMNS else 'event',
            'Events populated': int(event_log[col].count()),
            'Events populated %': round(event_log[col].count() / len(event_log) * 100, 2),
            'Distinct values': int(event_log[col].nunique()),
            'Activity types': int((columns_per_activity[col] != 0).sum()),
            'Monotonicity within cases': (
                monotonicity_overview.loc[col, 'Monotonicity within cases']
                if col in monotonicity_overview.index else None
            ),
            'Cases not monotonic': (
                monotonicity_overview.loc[col, 'Cases not monotonic']
                if col in monotonicity_overview.index else None
            ),
            'Monotonicity over log': (
                monotonicity_overview.loc[col, 'Monotonicity over log']
                if col in monotonicity_overview.index else None
            ),
        }
        for col in event_log.columns
        if col != 'folded_data'
    ])
    return (
        ACTIVITY,
        CASE_FEATURE_COLUMNS,
        CASE_ID,
        MANDATORY_COLUMNS,
        STANDARD_COLUMNS,
        activity_list,
        activity_stats,
        attribute_overview,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Events View

    Use for overview or filter for a specific case, activity, or time period. Switch between event log and case table view.
    """)
    return


@app.cell(hide_code=True)
def _(
    CASE_FEATURE_COLUMNS,
    MANDATORY_COLUMNS,
    STANDARD_COLUMNS,
    attribute_overview,
    case_log,
    event_log,
    mo,
):
    mo.ui.tabs({
        "Event Log": event_log[[col for col in MANDATORY_COLUMNS+STANDARD_COLUMNS+['folded_data'] if col not in CASE_FEATURE_COLUMNS]],
        "Case Log": case_log,
        "Attributes": attribute_overview,
    })
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Activity Schemas View

    Showing the activity schemas, i.e. the attributes that take at least one non-null value across the log for each activity type. Mandatory attributes are excluded from the list. Schema overlaps are attributes that belong to more than one activity schema.
    """)
    return


@app.cell(hide_code=True)
def _(activity_list, mo):
    # Select an activity type whose schema is shown below
    schema_activity_dropdown = mo.ui.dropdown(
        options=activity_list,
        value=activity_list[0] if activity_list else None,
        label="Select activity",
        searchable=True,
    )

    mo.vstack([
        mo.md("Select an activity type to inspect the attributes of its schema:"),
        schema_activity_dropdown
    ])
    return (schema_activity_dropdown,)


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
def _(
    ACTIVITY,
    MANDATORY_COLUMNS,
    STANDARD_COLUMNS,
    event_log,
    mo,
    partial_schema_usages,
    schema_activity_dropdown,
    schema_usages,
):
    # Events of the selected activity, with the attributes of its schema
    _selected_activity = schema_activity_dropdown.value
    _selected_events = event_log[event_log[ACTIVITY] == _selected_activity]
    _extra_schema_columns = schema_usages.loc[_selected_activity, 'extra_schema_keys']

    activity_events = mo.ui.table(
        _selected_events[MANDATORY_COLUMNS + STANDARD_COLUMNS + _extra_schema_columns],
        selection=None,
        page_size=15,
    )

    mo.ui.tabs({
        "Activity Schemas": schema_usages[['incidence', 'extra_schema_keys', 'missing_values']],
        "Schema Overlaps": partial_schema_usages[(partial_schema_usages != 0).any(axis=1)],
        "Selected Activity": mo.vstack([
            mo.md(f"Events of '{_selected_activity}' ({len(_selected_events)} events):"),
            activity_events,
        ]),
    })
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Analysis of Attribute Relationships
    """)
    return


@app.cell(hide_code=True)
def _(case_log, mo, px):
    # Show the pairwise linear correlation between the numeric case attributes
    _correlations = case_log.corr(numeric_only=True)

    _fig = px.imshow(_correlations, width=600)

    mo.vstack([
        mo.md("Pairwise Pearson correlation between the numeric attributes of the case log:"),
        _fig
    ])
    return


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

    nmi_bins_slider = mo.ui.slider(
        start=2, stop=20, value=10, label="Quantile bins for numeric attributes"
    )

    mo.vstack([
        mo.md("Select two attributes for multivariate analysis:"),
        mo.hstack([x_axis_dropdown, y_axis_dropdown], justify="start"),
        nmi_bins_slider
    ])
    return nmi_bins_slider, x_axis_dropdown, y_axis_dropdown


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
    return (case_log_reset,)


@app.cell(hide_code=True)
def _(
    au,
    case_log_reset,
    mo,
    nmi_bins_slider,
    x_axis_dropdown,
    y_axis_dropdown,
):
    # Assess the statistical dependence between the two selected attributes via normalized mutual information
    if x_axis_dropdown.value == y_axis_dropdown.value:
        attribute_dependence = mo.md(f"'{x_axis_dropdown.value}' is compared to itself.")
    else:
        _result = au.normalized_mutual_information(
            case_log_reset[x_axis_dropdown.value],
            case_log_reset[y_axis_dropdown.value],
            nmi_bins_slider.value,
        )

        if _result is None:
            attribute_dependence = mo.md(
                f"No rows where both '{x_axis_dropdown.value}' and "
                f"'{y_axis_dropdown.value}' are populated."
            )
        else:
            _hx, _hy, _mi, _nmi = _result
            attribute_dependence = mo.md(
                #f"H({x_axis_dropdown.value}) = **{_hx:.4f}** bits\n\n"
                #f"H({y_axis_dropdown.value}) = **{_hy:.4f}** bits\n\n"
                #f"MI({x_axis_dropdown.value}; {y_axis_dropdown.value}) = **{_mi:.4f}** bits\n\n"
                f"The attributes have a normalized mutual information NMI({x_axis_dropdown.value}; {y_axis_dropdown.value}) = **{_nmi:.4f}**"
            )

    attribute_dependence
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
        mo.md("Select a pair of attributes identified to be in a one-to-one relation to inspect them (if no such pairs have been identified, the dropdown is empty):"),
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


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Event Enrichment
    TBD where to position enrichment in the notebook and to replace with Aaron's widget
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
    event_log,
):
    cases = event_log.groupby(CASE_ID)
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
def _(mo):
    mo.md(r"""
    ##Transaction Detection
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ##Concurrent Event Detection
    """)
    return


if __name__ == "__main__":
    app.run()
