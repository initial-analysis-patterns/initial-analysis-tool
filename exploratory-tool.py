import marimo

__generated_with = "0.23.16"
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
    import numpy as np 
    import networkx as nx 
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
    return Path, au, dqu, mo, np, nx, pd, pm4py, px, tcu


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
    DEFAULT_CASE_COUNT = 1500

    _case_bounds = tcu.get_case_time_bounds(
        event_log_from_disk, CASE_ID_dropdown.value, COMPLETION_TIME_dropdown.value
    )

    CASE_WINDOW_START = _case_bounds['min'].min()
    _last_timestamp = _case_bounds['max'].max()

    # a day-resolution slider unless the log spans less than two days
    CASE_WINDOW_UNIT = 'D' if (_last_timestamp - CASE_WINDOW_START) >= pd.Timedelta(days=2) else 'h'
    _unit_length = pd.Timedelta(1, CASE_WINDOW_UNIT)

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
        mo.md("Select a time frame. Only cases that are fully contained within it are "
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

    # characterize the functional relationships between all attribute pairs
    attribute_relationships = au.find_functional_relationships(event_log)

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
    return attribute_relationships, event_log


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
        COMPLETION_TIME,
        MANDATORY_COLUMNS,
        STANDARD_COLUMNS,
        activity_list,
        activity_schema,
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


@app.cell
def _(activity_list, mo):
    activity_multiselect = mo.ui.multiselect(
        options=activity_list,
        value=activity_list[:1] if len(activity_list) >= 1 else activity_list,
        label="Select activities to see local attributes",
    )
    return (activity_multiselect,)


@app.cell
def _(mo):
    hide_case_features_checkbox = mo.ui.checkbox(
        label="Hide attributes that are also case-level attributes"
    )
    return (hide_case_features_checkbox,)


@app.cell(hide_code=True)
def _(
    ACTIVITY,
    CASE_FEATURE_COLUMNS,
    MANDATORY_COLUMNS,
    activity_multiselect,
    activity_schema,
    event_log,
    hide_case_features_checkbox,
    mo,
):
    _selected_activities = activity_multiselect.value

    if _selected_activities:
        _common_attrs = set(activity_schema.get(_selected_activities[0], []))
        for _act in _selected_activities[1:]:
            _common_attrs &= set(activity_schema.get(_act, []))
        _common_attrs = sorted(_common_attrs)
    else:
        _common_attrs = []

    if hide_case_features_checkbox.value:
        _common_attrs = [attr for attr in _common_attrs if attr not in CASE_FEATURE_COLUMNS]

    _display_columns = [attr for attr in MANDATORY_COLUMNS + _common_attrs if attr not in ['folded_data']]

    if _selected_activities:
        _filtered_log = event_log[event_log[ACTIVITY].isin(_selected_activities)][_display_columns]
    else:
        _filtered_log = event_log.iloc[0:0][_display_columns]

    local_view = mo.vstack([
        mo.md("Select one or more activities to view only the data attributes that are common to their schemas:"),
        activity_multiselect,
        hide_case_features_checkbox,
        mo.ui.table(_filtered_log, selection=None, page_size=15)
        if _selected_activities
        else mo.md("_No activities selected._"),
    ])

    # schema_usages
    return (local_view,)


@app.cell(hide_code=True)
def _(
    CASE_FEATURE_COLUMNS,
    MANDATORY_COLUMNS,
    STANDARD_COLUMNS,
    case_log,
    event_log,
    local_view,
    mo,
):
    mo.ui.tabs({
        "Global Attributes": event_log[[col for col in MANDATORY_COLUMNS+STANDARD_COLUMNS if col not in CASE_FEATURE_COLUMNS]],
        "Local Attributes": local_view,
        "Case Inspection": event_log[[col for col in MANDATORY_COLUMNS+STANDARD_COLUMNS+['folded_data'] if col not in CASE_FEATURE_COLUMNS]],
        "Case Log": case_log,
        "Raw Events": event_log
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
    attribute_overview,
    au,
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

    _schema_attributes = [
        col for col in MANDATORY_COLUMNS + STANDARD_COLUMNS + _extra_schema_columns
        if col != ACTIVITY
    ]

    activity_attribute_values = au.summarize_attribute_values(_selected_events, _schema_attributes)

    activity_events = mo.ui.table(
        _selected_events[MANDATORY_COLUMNS + STANDARD_COLUMNS + _extra_schema_columns],
        selection=None,
        page_size=15,
    )

    mo.ui.tabs({
        "Activity Schemas": schema_usages[['incidence', 'extra_schema_keys', 'missing_values']],
        "Schema Overlaps": partial_schema_usages[(partial_schema_usages != 0).any(axis=1)],
        "Attributes": attribute_overview,
        "Selected Activity": mo.vstack([
            mo.md(f"Attributes of '{_selected_activity}' over its {len(_selected_events)} events:"),
            activity_attribute_values,
            mo.md("Events:"),
            activity_events,],),
    })
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Analysis of Attribute Relationships
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    nmi_bins_slider = mo.ui.slider(
        start=2, stop=20, value=10, label="Quantile bins for numeric attributes"
    )

    max_distinct_input = mo.ui.number(
        start=2, stop=1000, value=50, step=1,
        label="Skip attributes with more distinct values than",
    )

    mo.vstack([
        mo.md("Options for the pairwise dependence analysis of the case attributes:"),
        nmi_bins_slider,
        max_distinct_input,
    ])
    return max_distinct_input, nmi_bins_slider


@app.cell(hide_code=True)
def _(au, case_log, max_distinct_input, mo, nmi_bins_slider, px):
    # Pairwise dependence between all case attributes: Pearson correlation and normalized mutual information
    case_log_reset = case_log.reset_index()

    nmi_matrix, attribute_dependence_table = au.analyze_attribute_dependence(
        case_log_reset,
        bins=nmi_bins_slider.value,
        max_distinct_values=max_distinct_input.value,
    )

    _correlations = case_log.corr(numeric_only=True)

    mo.vstack([
        mo.md("Pairwise Pearson correlation between the numeric case attributes:"),
        px.imshow(_correlations, width=600, zmin=-1, zmax=1),
        mo.md(
            "Pairwise normalized mutual information between all case attributes "
            f"(numeric attributes discretized into {nmi_bins_slider.value} quantile bins):"
        ),
        px.imshow(nmi_matrix, width=600, zmin=0, zmax=1),
        #mo.md("Values per attribute pair:"),
        #mo.ui.table(attribute_dependence_table, selection=None, page_size=15),
    ])
    return


@app.cell(hide_code=True)
def _(attribute_relationships, au, mo):
    # Select a functional relationship to inspect
    functional_relationships = attribute_relationships[
        attribute_relationships['cardinality'].isin(au.FUNCTIONAL_CARDINALITIES)
    ].reset_index(drop=True)

    _pair_labels = {
        f"{_row.attribute_a} <-> {_row.attribute_b} ({_row.cardinality})": _row.Index
        for _row in functional_relationships.itertuples()
    }

    relationship_pair_dropdown = mo.ui.dropdown(
        options=_pair_labels,
        value=next(iter(_pair_labels), None),
        label="Select attribute pair",
        searchable=True,
    )

    mo.vstack([
        mo.md(
            "Select a pair of attributes in a functional relationship, i.e. where the values of one "
            "attribute determine the values of the other, to inspect the mapping between their values "
            "(if no such pairs have been identified, the dropdown is empty):"
        ),
        mo.md("Over the events where both attributes are populated, an attribute A functionally determines an attribute B if every value of A co-occurs with exactly one value of B. Pairs are characterized as one-to-one (both directions), many-to-one or one-to-many (one direction). Many-to-many relationships are determined when neither of the former is detected. Support is the share of events where both attributes are populated. "
            "Pairs that are not in functional relationships are listed separately with their reason: many-to-many, trivial (one attribute takes fewer than two distinct values on the jointly populated events), or disjoint (the attributes are never populated on the same event)."),
        relationship_pair_dropdown
    ])
    return functional_relationships, relationship_pair_dropdown


@app.cell(hide_code=True)
def _(
    attribute_relationships,
    au,
    functional_relationships,
    mo,
    pd,
    relationship_pair_dropdown,
):
    # Show the functional relationships, the mapping of the selected pair, and the pairs that are not functional
    _non_functional = attribute_relationships[attribute_relationships['cardinality'].isin(au.FUNCTIONAL_CARDINALITIES)
    ].reset_index(drop=True)

    if functional_relationships.empty or relationship_pair_dropdown.value is None:
        _mapping_view = mo.md("No functional relationship selected.")
    else:
        _row = functional_relationships.loc[relationship_pair_dropdown.value]

        if _row['direction'] == 'a_to_b':
            _source, _target = _row['attribute_a'], _row['attribute_b']
        else:
            _source, _target = _row['attribute_b'], _row['attribute_a']

        _mapping_view = mo.vstack([
            mo.md(
                f"'{_row['attribute_a']}' <-> '{_row['attribute_b']}': **{_row['cardinality']}** "
                f"({_row['n_a']} distinct '{_row['attribute_a']}' values, "
                f"{_row['n_b']} distinct '{_row['attribute_b']}' values, "
                f"support {_row['support']:.4f} over {_row['n_rows']} events)\n\n"
                f"Functional mapping '{_source}' -> '{_target}':"
            ),
            pd.DataFrame({
                _source: list(_row['mapping'].keys()),
                _target: list(_row['mapping'].values()),
            }),
        ])

    mo.ui.tabs({
        "All functional relationships": functional_relationships.drop(columns=['mapping']),
        "Selected mapping": _mapping_view,
        "Not functional": _non_functional.drop(columns=['mapping', 'direction']),
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
    ##Complexity Reduction
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Timestamp Coincidence
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ##### Super event detection
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    min_set_size_input = mo.ui.number(
        label="Minimum set size for super-event detection",
        value=2,
        start=2,
        step=1,
    )
    min_set_size_input
    return (min_set_size_input,)


@app.cell(hide_code=True)
def _(ACTIVITY, CASE_ID, COMPLETION_TIME, event_log, min_set_size_input, pd):
    #Build timestamp-level event sets
    window_df = (
        event_log.groupby([CASE_ID, COMPLETION_TIME])[ACTIVITY]
        .agg(lambda s: frozenset(sorted(set(s))))
        .reset_index(name='event_set')
    )
    window_df = window_df[window_df['event_set'].map(len) >= min_set_size_input.value].copy()
    window_df['set_size'] = window_df['event_set'].map(len)

    #Aggregate concurrent sets
    set_summary = (  # Aggregate each concurrent event set.
        window_df.groupby('event_set')  # Group identical concurrent sets.
        .agg(occurrences=(CASE_ID, 'size'), cases_with_set=(CASE_ID, 'nunique'))  # Count windows and cases.
        .reset_index()  # Move grouped keys back to columns.
    )

    #Compute totals
    total_cases = event_log[CASE_ID].nunique()  # Count all cases in the log.
    event_totals = event_log[ACTIVITY].value_counts().to_dict()  # Count total occurrences per activity.

    #Build case-level activity universes
    case_activity_sets = event_log.groupby(CASE_ID)[ACTIVITY].agg(lambda s: set(s)).tolist()  # Build each case's activity universe.
    case_activity_sets

    #Enrich set descriptors
    set_summary['set_size'] = set_summary['event_set'].map(len)  # Compute set size.

    #Case support
    # Compute Case support: how common the concurrent set is across all cases.
    set_summary['case_support'] = set_summary['cases_with_set'] / total_cases 

    #Set coverage
    #Compute Set coverage: among cases where all events in the set appear, how often they appear concurrently.

    set_summary['cases_with_all_events'] = set_summary['event_set'].map(  # Count cases where all set events appear.
        lambda s: sum(s.issubset(case_set) for case_set in case_activity_sets)
     )
    set_summary['set_coverage'] = (set_summary['cases_with_set'] / set_summary['cases_with_all_events']).fillna(0.0) 

    #Event coverage
    # Compute Event coverage: for each set, on average, how frequent its events are relative to their individual total occurrences in the log.
    if set_summary.empty:
        set_summary['event_coverage_avg'] = pd.Series(
            index=set_summary.index,
            dtype='float64',
        )
    else:
        set_summary['event_coverage_avg'] = set_summary.apply(
            lambda r: (
                sum(
                    r['occurrences'] / event_totals[e]  # Event-level share covered by this concurrent set.
                    for e in r['event_set']  # Iterate through events in the current set.
                )
                / len(r['event_set'])  # Average over set size (number of events in the set), otherwise the coverage would be biased towards larger sets (higher sums with set having more elements)
            ),
            axis=1,  # Apply row-wise: one concurrent set at a time.
        )

    #Final ranking output
    set_summary = (  # Select and order final result columns.
        set_summary[['event_set', 'case_support', 'set_coverage', 'event_coverage_avg', 'occurrences']]
        .sort_values(['case_support', 'set_coverage', 'event_coverage_avg', 'occurrences'], ascending=False)
        .reset_index(drop=True)
    )
    return (set_summary,)


@app.cell(hide_code=True)
def _(set_summary):
    set_summary
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ##### Batch event detection
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    min_batch_cases_input = mo.ui.number(
        label="Minimum distinct cases for batch-event detection",
        value=2,
        start=2,
        step=1,
    )
    min_batch_cases_input
    return


@app.cell(hide_code=True)
def _(ACTIVITY, CASE_ID, COMPLETION_TIME, event_log):
    #Detect cross-case batch events
    batch_events = (
        event_log.groupby([ACTIVITY, COMPLETION_TIME])
        .agg(
            case_count=(CASE_ID, 'nunique'),
            case_ids=(CASE_ID, lambda s: tuple(sorted(s.astype(str).unique()))),
        )
        .reset_index()
        .query('case_count >= @min_batch_cases_input.value')
        .sort_values(['case_count', ACTIVITY, COMPLETION_TIME], ascending=[False, True, True])
        .reset_index(drop=True)
    )
    return (batch_events,)


@app.cell(hide_code=True)
def _(batch_events):
    batch_events
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Transaction Detection
    """)
    return


@app.cell(hide_code=True)
def _(ACTIVITY, event_log, mo):
    # Options for excluded events from current log
    activity_options = sorted(
        event_log[ACTIVITY].dropna().astype(str).unique().tolist()
    )

    excluded_events_input = mo.ui.multiselect(
        options=activity_options,
        value=[],
        label="Excluded events",
    )

    sim_threshold_input = mo.ui.number(
        label="Similarity threshold",
        value=0.95,
        start=0.0,
        stop=1.0,
        step=0.01,
    )

    min_set_size_tr_input = mo.ui.number(
        label="Minimum set size",
        value=2,
        start=2,
        step=1,
    )

    mo.vstack([
        excluded_events_input,
        sim_threshold_input,
        min_set_size_tr_input,
    ])
    return excluded_events_input, min_set_size_tr_input, sim_threshold_input


@app.cell(hide_code=True)
def _(
    ACTIVITY,
    CASE_ID,
    event_log,
    excluded_events_input,
    min_set_size_tr_input,
    np,
    nx,
    pd,
    sim_threshold_input,
):
    # Build case-event count table.
    count_matrix = (
        event_log.groupby([CASE_ID, ACTIVITY]).size()
        .rename('count').reset_index()
        .pivot(index=CASE_ID, columns=ACTIVITY, values='count')
        .fillna(0).astype(int)
    )

    # Exclude selected events and print updated table.
    use_cols = [c for c in count_matrix.columns if c not in excluded_events_input.value]
    count_matrix = count_matrix[use_cols].copy()

    # Build event count vectors from the case-event count matrix.
    # Each row is one event profile across all cases.
    event_vectors = count_matrix.T.astype(float).copy()

    # Compute pairwise weighted Jaccard similarity matrix (events x events).
    X = event_vectors.to_numpy()
    min_sum = np.minimum(X[:, None, :], X[None, :, :]).sum(axis=2)
    max_sum = np.maximum(X[:, None, :], X[None, :, :]).sum(axis=2)

    # np.divide computes element-wise min_sum / max_sum; using 'where' skips zero denominators,
    # and 'out' pre-fills those skipped positions with 1.0 (for identical all-zero vector pairs).
    sim_values = np.divide(
        min_sum,
        max_sum,
        out=np.ones_like(min_sum, dtype=float),
        where=max_sum > 0
        )

    similarity_matrix = pd.DataFrame(
        sim_values,
        index=event_vectors.index,
        columns=event_vectors.index
        )

    # Build a boolean adjacency matrix from the similarity threshold.
    # True means two events are connected (similar enough).
    adjacency = (similarity_matrix >= sim_threshold_input.value).copy()


    # Create an undirected graph from the adjacency matrix.
    G = nx.from_pandas_adjacency(adjacency.astype(int))

    # Find maximal cliques: fully connected groups of events.
    # Keep only cliques that meet the minimum set size.
    cliques = [sorted(list(c)) for c in nx.find_cliques(G) if len(c) >= min_set_size_tr_input.value]

    # Convert cliques to a candidate-set table.
    candidate_sets = pd.DataFrame({'event_set': cliques})
    candidate_sets['set_size'] = candidate_sets['event_set'].map(len)

    # For one candidate set, compute quality from the pairwise similarity submatrix:
    # 1) take only rows/cols of events in the set
    # 2) keep upper-triangle pairs (i < j) to avoid duplicates and diagonal
    # 3) summarize with min and mean pairwise similarity
    def set_similarity(events):
        sub = similarity_matrix.loc[events, events].values
        pair_vals = sub[np.triu_indices(len(events), k=1)]
        return float(pair_vals.mean())

    candidate_sets['similarity'] = candidate_sets['event_set'].apply(set_similarity)

    # Sort best candidates first (bigger sets, then higher similarity).
    candidate_sets = candidate_sets.sort_values(
        ['set_size', 'similarity'],
        ascending=[False, False]
    ).reset_index(drop=True)
    return (candidate_sets,)


@app.cell(hide_code=True)
def _(candidate_sets):
    candidate_sets
    return


if __name__ == "__main__":
    app.run()
