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
    ## Temporal Characteristics of the Log Overview
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
def _(event_log_from_disk, mo, tcu):
    # Show the granularity level of the encoded timestamps in the log, including whether timestamp components and timezone are constant
    timestamp_component_summary, timestamp_constant_prefixes = tcu.analyze_timestamp_components(event_log_from_disk)

    mo.vstack([
        mo.md("Showing the precision of each timestamp column and whether any timestamp elements are constant, based on the data recorded therein:"),
        mo.ui.tabs({
        "Component analysis": timestamp_component_summary,
        "Constant prefixes": timestamp_constant_prefixes,
    })
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
        mo.md("## Sampling of Cases for Exploratory Analysis"),
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

    if duplicate_event_instances.empty:
        _output.append(mo.md("No duplicated events were found in the log."))
    else:
        _output.append(mo.md("The following events had duplicates that have been removed, retaining only one:"))
        _output.append(duplicate_event_instances)

    mo.vstack(_output)
    return event_log, redundant_attribute_candidates


@app.cell(hide_code=True)
def _(
    ACTIVITY_dropdown,
    CASE_ID_dropdown,
    COMPLETION_TIME_dropdown,
    event_log,
    fully_filled_columns,
    mo,
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

    mo.vstack([
        mo.md("Case feature columns (unique value per case, possibly NaN):"),
        mo.md(", ".join(f"`{col}`" for col in CASE_FEATURE_COLUMNS) or "_none_")
    ])
    return (
        ACTIVITY,
        CASE_FEATURE_COLUMNS,
        CASE_ID,
        COMPLETION_TIME,
        MANDATORY_COLUMNS,
        STANDARD_COLUMNS,
        activity_list,
        activity_stats,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Event Log View

    Use for overview or filter for a specific case, activity, or time period. Switch between event log and case table view.
    """)
    return


@app.cell(hide_code=True)
def _(
    CASE_FEATURE_COLUMNS,
    MANDATORY_COLUMNS,
    STANDARD_COLUMNS,
    case_log,
    event_log,
    mo,
):
    mo.ui.tabs({
        "Event Log": event_log[[col for col in MANDATORY_COLUMNS+STANDARD_COLUMNS+['folded_data'] if col not in CASE_FEATURE_COLUMNS]],
        "Case Log": case_log
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
    ## Activity-wise Attribute Filling

    Select an activity type and an attribute from its schema to see how the attribute is populated for the activity type.
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
def _(
    ACTIVITY,
    CASE_ID,
    COMPLETION_TIME,
    activity_dropdown,
    attribute_dropdown,
    au,
    event_log,
    mo,
):
    # Determine how often the selected attribute changes across the selected activity's events within a case
    if attribute_dropdown.value is None:
        attribute_change_frequency = mo.md(
            f"'{activity_dropdown.value}' has no populated attributes."
        )
    else:
        _change_counts = au.get_change_counts_per_case(
            event_log, CASE_ID, COMPLETION_TIME, ACTIVITY,
            activity_dropdown.value, attribute_dropdown.value
        )

        attribute_change_frequency = mo.md(
            f"Cases considered ('{attribute_dropdown.value}' populated at least once "
            f"on '{activity_dropdown.value}'): **{len(_change_counts)}**\n\n"
            f"Average number of changes per case: **{_change_counts.mean():.4f}**\n\n"
            f"Variance: **{_change_counts.var():.4f}**"
        )

    attribute_change_frequency
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Activity-Attribute Association
    It should be checked whether an attribute recorded for an activity is intrinsically associated with that activity. This is an analysis that requires domain knowledge and cannot be automated.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    activity_attribute_association_notes_editor = mo.ui.code_editor(
        language="python",
        label="Write your notes on the activity-attribute associations here")

    mo.vstack([activity_attribute_association_notes_editor])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Analysis of an Attribute in Isolation
    """)
    return


@app.cell(hide_code=True)
def _(MANDATORY_COLUMNS, event_log, mo):
    # Select an attribute to inspect how it is filled across and within cases
    _selectable_attributes = [
        col for col in event_log.columns
        if col not in MANDATORY_COLUMNS and col != 'folded_data'
    ]

    filling_attribute_dropdown = mo.ui.dropdown(
        options=_selectable_attributes,
        value=_selectable_attributes[0] if _selectable_attributes else None,
        label="Attribute: ",
        searchable=True,
    )

    mo.vstack([
        mo.md("Select an attribute to analyze."),
        filling_attribute_dropdown
    ])
    return (filling_attribute_dropdown,)


@app.cell(hide_code=True)
def _(CASE_ID, au, event_log, filling_attribute_dropdown, mo):
    # Show the distribution of case-wise filling classes for the selected attribute
    case_wise_filling_distribution = au.get_case_wise_filling(
        event_log, CASE_ID, filling_attribute_dropdown.value
    )

    mo.vstack([
        mo.md(
            f"Case-wise distribution of attribute '{filling_attribute_dropdown.value}':"
        ),
        case_wise_filling_distribution
    ])
    return


@app.cell(hide_code=True)
def _(au, event_log, filling_attribute_dropdown, mo):
    # Characterize the values of the selected attribute: categorically, or quantitatively if numeric

    attribute_value_characterization = au.characterize_attribute_values(
        event_log, filling_attribute_dropdown.value
    )

    mo.vstack([
        mo.md(
            f"Value characterization of attribute '{filling_attribute_dropdown.value}':"
        ),
        attribute_value_characterization.rename(columns=str)
    ])
    return


@app.cell(hide_code=True)
def _(
    CASE_ID,
    COMPLETION_TIME,
    au,
    checkbox,
    event_log,
    filling_attribute_dropdown,
    mo,
    pd,
):
    # Check whether the selected attribute is monotonically non-decreasing over time
    _attribute = filling_attribute_dropdown.value

    if not pd.api.types.is_numeric_dtype(event_log[_attribute]):
        attribute_monotonicity = mo.md(
            f"'{_attribute}' is not numeric, so monotonicity is not checked."
        )
    else:
        _monotonicity_case_flags = au.get_case_level_monotonic_flags(
            event_log, CASE_ID, COMPLETION_TIME, _attribute
        )
        _violating_cases = _monotonicity_case_flags[~_monotonicity_case_flags].index.tolist()

        if checkbox.value:
            _log_level = (
                f"Monotonically increasing over the whole log: "
                f"**{au.is_log_level_monotonic(event_log, _attribute)}**"
            )
        else:
            _log_level = (
                "Log-level monotonicity is not checked: the events are not globally "
                "ordered by completion time. Enable the ordering option during initialization."
            )

        attribute_monotonicity = mo.md(
            f"Attribute '{filling_attribute_dropdown.value}' is monotonically increasing within every case: **{_monotonicity_case_flags.all()}**\n\n"
            f"{_log_level}\n\n"
            f"Cases where '{_attribute}' is not monotonically increasing "
            f"({len(_violating_cases)}): {_violating_cases}"
        )

    attribute_monotonicity
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
                f"NMI({x_axis_dropdown.value}; {y_axis_dropdown.value}) = **{_nmi:.4f}**"
            )

    attribute_dependence
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Redundant Attributes
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
        mo.md("Select a pair of redundant attribute candidates, i.e., attributes that show information in a one-to-one relation, to inspect (if no candidates have been found, the dropdown is empty):"),
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
    TBD where to position in the notebook
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
