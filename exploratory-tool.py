import marimo

__generated_with = "0.24.0"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Initial Event Log Analysis

    This notebook integrates a set of patterns for initial event log analysis that are useful for exploring the raw event log data before doing any specific process mining analysis such as behavioral, conformance, performance, or deviance analysis.
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
    import display_util as du
    du = importlib.reload(du)
    return Path, au, dqu, du, mo, np, nx, pd, pm4py, px, su, tcu


@app.cell(hide_code=True)
def _(Path, mo):
    browser = mo.ui.file_browser(
        initial_path=Path.cwd(), 
        filetypes=['.csv', '.xes'], 
        restrict_navigation=False,
        multiple=False, 
        label='Select and event log (xes or csv)')
    browser.style({"max-height": "200px", "overflow": "auto"})
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
    ## Log Initialization
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

    timestamp_analyzer1 = mo.vstack([
        mo.md("Showing the format of each timestamp column, if unambiguously detected from the data recorded therein:"),
        timestamp_format_summary
    ])
    return (timestamp_analyzer1,)


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
        label="Select a Timestamp attribute to inspect: ",
        searchable=True,
    )
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

    granularity_analyzer = mo.vstack([
        mo.md(
            f"Showing the precision of '{_selected_timestamp}' and whether any timestamp "
            "elements are constant, based on the data recorded therein:"
        ),
        timestamp_attribute_dropdown,
        mo.ui.tabs({
            "Component analysis": _component_view,
            "Constant prefixes": _prefix_view,
        }),
    ])
    return (granularity_analyzer,)


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

    log_initialization = mo.vstack([
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
        log_initialization,
        timezone_dropdown,
    )


@app.cell(hide_code=True)
def _(
    CASE_ID,
    CASE_WINDOW_START,
    CASE_WINDOW_UNIT,
    COMPLETION_TIME,
    case_window_slider,
    checkbox,
    dqu,
    event_log_from_disk,
    granularity_normalization_dropdown,
    mo,
    pd,
    tcu,
    timezone_dropdown,
):
    # Initialize the event log
    initialized_event_log = event_log_from_disk

    _messages = []

    # apply the selected timezone to all timestamp columns
    _selected_timezone = timezone_dropdown.value

    for _col in initialized_event_log.columns:
        if isinstance(initialized_event_log[_col].dtype, pd.DatetimeTZDtype):
            initialized_event_log[_col] = initialized_event_log[_col].dt.tz_convert(_selected_timezone)
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
            for _col in initialized_event_log.columns:
                if isinstance(initialized_event_log[_col].dtype, pd.DatetimeTZDtype) or pd.api.types.is_datetime64_dtype(initialized_event_log[_col]):
                    _original = initialized_event_log[_col]
                    _rounded = _original.dt.round(_freq)

                    _changed = (_rounded != _original).sum()

                    initialized_event_log[_col] = _rounded

                    _messages.append(
                        f"Rounded {_changed}/{len(_original)} values in "
                        f"'{_col}' to the nearest {_target_granularity}"
                    )

    # keep only the cases that start and end within the selected time frame
    _window_start = CASE_WINDOW_START + pd.Timedelta(case_window_slider.value[0], CASE_WINDOW_UNIT)
    _window_end = CASE_WINDOW_START + pd.Timedelta(case_window_slider.value[1], CASE_WINDOW_UNIT)

    _cases_before = initialized_event_log[CASE_ID].nunique()

    initialized_event_log = tcu.filter_cases_within_window(
        initialized_event_log, CASE_ID, COMPLETION_TIME,
        _window_start, _window_end
    )

    _messages.append(
        f"Time frame {_window_start} to {_window_end}: kept "
        f"{initialized_event_log[CASE_ID].nunique()} of {_cases_before} cases "
        f"({len(initialized_event_log)} events)"
    )

    # columns that are filled for every row vs. columns that are not consistently filled
    _fully_filled_columns = [ col for col in initialized_event_log.columns if initialized_event_log[col].notna().all() ]
    _inconsistent_columns = [ col for col in initialized_event_log.columns if col not in _fully_filled_columns ]

    # from the fully filled columns, drop those that only ever take a single value
    _constant_columns = [ col for col in _fully_filled_columns if initialized_event_log[col].nunique() <= 1 ]
    for _col in _constant_columns:
        _values = initialized_event_log[_col].unique()
        _value = _values[0] if len(_values) > 0 else None
        _messages.append(f"Dropped constant column '{_col}' with value: {_value}")
    initialized_event_log = initialized_event_log.drop(columns=_constant_columns)

    # from the inconsistently filled columns, drop those that are completely empty
    _empty_columns = [ col for col in _inconsistent_columns if initialized_event_log[col].notna().sum() == 0 ]
    for _col in _empty_columns:
        _messages.append(f"Dropped empty column '{_col}'")
    initialized_event_log = initialized_event_log.drop(columns=_empty_columns)
    _inconsistent_columns = [ col for col in _inconsistent_columns if col not in _empty_columns ]

    # check for and remove events that are exact duplicates of another event
    duplicate_event_instances = dqu.summarize_duplicate_events(initialized_event_log)

    if not duplicate_event_instances.empty:
        _events_before = len(initialized_event_log)
        initialized_event_log = dqu.remove_duplicate_events(initialized_event_log)
        _messages.append(
            f"Removed {_events_before - len(initialized_event_log)} duplicate events "
            f"in {len(duplicate_event_instances)} groups of identical events"
        )

    # Based on the selected COMPLETION TIME column, check whether events are ordered by completion time within each case and across the log
    case_ordering_summary, log_ordering_summary = tcu.analyze_event_ordering(
        initialized_event_log, CASE_ID, COMPLETION_TIME
    )

    # Based on whether the checkbox was checked, order the event log
    if checkbox.value:
        initialized_event_log['original_order'] = range(len(initialized_event_log))

        initialized_event_log = initialized_event_log.sort_values(
            by=[
                COMPLETION_TIME,
                'original_order'
            ]
        ).reset_index(drop=True)

        assert initialized_event_log[
            COMPLETION_TIME
        ].is_monotonic_increasing
        _messages.append("All events in the log are now globally ordered.")

    # add folding of inconsistent columns
    def fold_data(event):
        # activity = event[ACTIVITY]
        # non_standard_schema_columns = activity_schema[activity]
        dict = {k: v for k, v in event[_inconsistent_columns].items() if pd.notna(v)}
        return dict if dict else None

    initialized_event_log['folded_data'] = initialized_event_log.apply(fold_data, axis=1)

    # report what the initialization did, and show one kept instance per group of duplicate events
    _output = [mo.md("\n".join(f"- {_message}" for _message in _messages))]

    if not duplicate_event_instances.empty:
        _output.append(mo.md("The following events had duplicates that have been removed, retaining only one:"))
        _output.append(duplicate_event_instances)

    initialization_summary = mo.vstack([mo.md("### Summary of the Initialization"), *_output])
    return initialization_summary, initialized_event_log


@app.cell(hide_code=True)
def _(CASE_ID, COMPLETION_TIME, event_log_from_disk, mo, pd, tcu):
    # Select a time frame; only cases that start and end within it are included in the event log
    DEFAULT_CASE_COUNT = 1500

    _case_bounds = tcu.get_case_time_bounds(
        event_log_from_disk, CASE_ID, COMPLETION_TIME
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

    time_frame_selector = mo.vstack([
        mo.md("Select a time frame. Only cases that are fully contained within it are "
            f"included for analysis. The initial selection covers the first {DEFAULT_CASE_COUNT} cases."
        ),
        case_window_slider
    ])
    return (
        CASE_WINDOW_START,
        CASE_WINDOW_UNIT,
        case_window_slider,
        time_frame_selector,
    )


@app.cell(hide_code=True)
def _(
    granularity_analyzer,
    initialization_summary,
    log_initialization,
    mo,
    time_frame_selector,
    timestamp_analyzer1,
):
    mo.ui.tabs({
        "Log Initialization" : log_initialization,
        "Initialization Summary" : initialization_summary,
        "Time Frame" : time_frame_selector,
        "Timestamp attribute detection": timestamp_analyzer1,
        "Granularity Analysis" : granularity_analyzer
    })
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
def _(ACTIVITY_dropdown, CASE_ID_dropdown, COMPLETION_TIME_dropdown):
    # Name the mandatory attributes once. Everything downstream reads these
    # rather than the dropdowns, the enrichment widget included -- it has to be
    # told which columns are the case id, the timestamp and the activity.
    CASE_ID = CASE_ID_dropdown.value
    ACTIVITY = ACTIVITY_dropdown.value
    COMPLETION_TIME = COMPLETION_TIME_dropdown.value

    MANDATORY_COLUMNS = [CASE_ID, ACTIVITY, COMPLETION_TIME]
    return ACTIVITY, CASE_ID, COMPLETION_TIME, MANDATORY_COLUMNS


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Log Modification

    The widget takes an event log and creates a new event log and an accompanying case log, allowing for enrichments on each level. It also allows activity folding and unfolding. In the Enricher tab, there are two sub-tabs, one for event log enrichment and one for case log enrichment. An applied
    event log enrichment can be used in the case log enrichment. The widget employs a staging mechanism
    so that not every change leads to a full recomputation, only when changes are applied.

    **Note:** the widget is built from the initialized log, so changing the time
    zone, granularity, time frame, ordering or the mandatory-attribute dropdowns
    above rebuilds it and clears what has been applied. Changes below do not have that effect.

    Furthermore, there is also the possibility of further manual enrichment at both the event level and case level.

    Finally, the Activity Folding and Activity Unfolding tabs allow specifying a folding, resp. unfolding rule.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    # Marimo state management to make application reactive
    enrichment_applied, set_enrichment_applied = mo.state(False)
    return enrichment_applied, set_enrichment_applied


@app.cell(hide_code=True)
def _(
    ACTIVITY,
    CASE_ID,
    COMPLETION_TIME,
    initialized_event_log,
    set_enrichment_applied,
):
    from eclear import EnrichmentWidget

    CARRIED_COLUMNS = [
        col for col in ('folded_data', 'original_order')
        if col in initialized_event_log.columns
    ]

    enricher = EnrichmentWidget(
        initialized_event_log.drop(columns=CARRIED_COLUMNS),
        case_id_col=CASE_ID,
        time_col=COMPLETION_TIME,
        activity_col=ACTIVITY,
        on_apply=lambda: set_enrichment_applied(True),
    )
    return CARRIED_COLUMNS, enricher


@app.cell(hide_code=True)
def _(mo):
    _sample_enrichment = "event_log['weekday'] = event_log['time:timestamp'].apply(lambda x: x.weekday())"

    event_enrichment_code_editor = mo.ui.code_editor(
        value=_sample_enrichment,
        language="python",
        label="Write your code here")

    _intro = mo.md("Enrich the event log by hand. Anything the widget cannot express belongs here. This runs *after* the widget, on the frame it produced, so `event_log` already carries the applied event enrichments.")

    event_enrichment_submit_button = mo.ui.run_button(label="Submit")
    manual_event_enrichment = mo.vstack([_intro, event_enrichment_code_editor, event_enrichment_submit_button])
    return (
        event_enrichment_code_editor,
        event_enrichment_submit_button,
        manual_event_enrichment,
    )


@app.cell(hide_code=True)
def _(
    ACTIVITY,
    CARRIED_COLUMNS,
    CASE_ID,
    COMPLETION_TIME,
    activity_folding_code_editor,
    activity_folding_submit_button,
    activity_unfolding_code_editor,
    activity_unfolding_submit_button,
    au,
    enricher,
    enrichment_applied,
    event_enrichment_code_editor,
    event_enrichment_submit_button,
    initialized_event_log,
    su,
):
    enrichment_applied  # re-run this cell whenever the widget applies

    event_log = enricher.event_log.copy()

    # add manual enrichments here
    if event_enrichment_submit_button.value:
        exec(event_enrichment_code_editor.value)

    # apply the activity folding rule
    activity_folding_summary = None
    folded_attributes = []

    if activity_folding_submit_button.value:
        _folding_baseline = su.get_activity_baseline(event_log, ACTIVITY)

        event_log = su.apply_activity_folding(
            event_log,
            activity_folding_code_editor.value,
            context={'CASE_ID': CASE_ID, 'ACTIVITY': ACTIVITY, 'COMPLETION_TIME': COMPLETION_TIME},
        )

        activity_folding_summary, folded_attributes = su.summarize_activity_transformation(
            _folding_baseline, event_log, ACTIVITY
        )

    # apply the activity unfolding rule
    activity_unfolding_summary = None
    unfolded_attributes = []

    if activity_unfolding_submit_button.value:
        _unfolding_baseline = su.get_activity_baseline(event_log, ACTIVITY)

        event_log = su.apply_activity_unfolding(
            event_log,
            activity_unfolding_code_editor.value,
            context={'CASE_ID': CASE_ID, 'ACTIVITY': ACTIVITY, 'COMPLETION_TIME': COMPLETION_TIME},
        )

        activity_unfolding_summary, unfolded_attributes = su.summarize_activity_transformation(
            _unfolding_baseline, event_log, ACTIVITY
        )

    # characterize the functional relationships between all attribute pairs.
    # The widget's own relative times are left out: they are near-unique by
    # construction, so pairing them against everything else costs a column's
    # worth of comparisons and says nothing.
    attribute_relationships = au.find_functional_relationships(
        event_log,
        columns=[col for col in event_log.columns
                 if col not in ('rel_time', 'rel_log_time')],
    )

    # put the initialization's row-level bookkeeping back, by index
    for _col in CARRIED_COLUMNS:
        event_log[_col] = initialized_event_log[_col]
    return (
        activity_folding_summary,
        activity_unfolding_summary,
        attribute_relationships,
        event_log,
        folded_attributes,
        unfolded_attributes,
    )


@app.cell(hide_code=True)
def _(mo):
    _sample_enrichment = "case_log['events_per_day'] = case_log['no_of_events'] / (case_log['duration'].dt.total_seconds() / 86400)"

    case_enrichment_code_editor = mo.ui.code_editor(
        value=_sample_enrichment,
        language="python",
        label="Write your code here")

    _intro = mo.md("Enrich the case log by hand.  The same, one level up. case_log carries the base case attributes, the applied case enrichments and the case-level attributes found in the log.")

    case_enrichment_submit_button = mo.ui.run_button(label="Submit")
    manual_case_enrichment = mo.vstack([_intro, case_enrichment_code_editor, case_enrichment_submit_button])
    return (
        case_enrichment_code_editor,
        case_enrichment_submit_button,
        manual_case_enrichment,
    )


@app.cell(hide_code=True)
def _(
    CASE_FEATURE_COLUMNS,
    CASE_ID,
    case_enrichment_code_editor,
    case_enrichment_submit_button,
    enricher,
    enrichment_applied,
    event_log,
):
    enrichment_applied  # re-run this cell whenever the widget applies

    # start_time, end_time, no_of_events and duration, plus whatever the case
    # tab applied. start/end are the earliest and latest timestamps of the case
    # rather than its first and last rows, so an unordered log still yields a
    # non-negative duration.
    case_log = enricher.case_log

    # the case-level attributes identified further down: one value per case by
    # definition, so 'first' takes it. Assigned rather than joined -- a join
    # returns a new frame and drops the record of which enrichment produced
    # which column, which is what lets a column be read back later.
    _case_features = [col for col in CASE_FEATURE_COLUMNS if col not in case_log.columns]
    if _case_features:
        _folded = event_log.groupby(CASE_ID)[_case_features].first()
        for _col in _case_features:
            case_log[_col] = _folded[_col]

    # add manual enrichments here
    if case_enrichment_submit_button.value:
        exec(case_enrichment_code_editor.value)
    return (case_log,)


@app.cell(hide_code=True)
def _(mo):
    _sample_folding = '''def fold_activities(df):
        # Relevant for the Sepsis event log: fold "Release <letter>" into "Release",
        # keeping the letter in a new attribute ReleaseCode.
        release_code = df[ACTIVITY].str.extract(r'^Release ([A-Za-z])$')[0]

        df['ReleaseCode'] = release_code
        df.loc[release_code.notna(), ACTIVITY] = 'Release'

        return df
    '''

    activity_folding_code_editor = mo.ui.code_editor(
        value=_sample_folding,
        language="python",
        label="Define fold_activities(df)",
    )

    activity_folding_submit_button = mo.ui.run_button(label="Apply folding")

    _intro = mo.md(
        "Fold activity types whose distinction is not needed into a common activity type, optionally "
        "keeping the distinction in a new attribute. "
        "The folded log replaces the event log for all analyses below."
    )

    activity_folding = mo.vstack([_intro, activity_folding_code_editor, activity_folding_submit_button])
    return (
        activity_folding,
        activity_folding_code_editor,
        activity_folding_submit_button,
    )


@app.cell(hide_code=True)
def _(mo):
    _sample_unfolding = '''def unfold_activities(df):
        # Relevant for the Road Traffic Fine Management event log: an event named "Payment" is a
        # PartialPayment if paymentAmount is less than totalPaymentAmount, and a FullPayment otherwise.
        payment = df[ACTIVITY] == 'Payment'
        is_partial = df['paymentAmount'] < df['totalPaymentAmount']

        df.loc[payment & is_partial, ACTIVITY] = 'PartialPayment'
        df.loc[payment & ~is_partial, ACTIVITY] = 'FullPayment'

        return df
    '''

    activity_unfolding_code_editor = mo.ui.code_editor(
        value=_sample_unfolding,
        language="python",
        label="Define unfold_activities(df)",
    )

    activity_unfolding_submit_button = mo.ui.run_button(label="Apply unfolding")

    _intro = mo.md(
        "Give semantically distinct activities that are implicitly represented by one activity type "
        "their own activity type, based on a rule over the recorded attribute values. "
        "The unfolded log replaces the event log for all analyses below."
    )

    activity_unfolding = mo.vstack([_intro, activity_unfolding_code_editor, activity_unfolding_submit_button])
    return (
        activity_unfolding,
        activity_unfolding_code_editor,
        activity_unfolding_submit_button,
    )


@app.cell(hide_code=True)
def _(
    activity_folding_summary,
    activity_unfolding_summary,
    folded_attributes,
    mo,
    unfolded_attributes,
):
    def _transformation_view(summary, added_attributes, name):
        if summary is None:
            return mo.md(f"No {name} applied.")

        return mo.vstack([
            mo.md(
                f"Activity types after {name}: **{(summary['Events after'] > 0).sum()}** "
                f"(before: {(summary['Events before'] > 0).sum()})."
                + (f" Added attributes: {added_attributes}." if added_attributes else "")
            ),
            summary,
        ])

    activity_folding_result = _transformation_view(activity_folding_summary, folded_attributes, "folding")
    activity_unfolding_result = _transformation_view(activity_unfolding_summary, unfolded_attributes, "unfolding")
    return activity_folding_result, activity_unfolding_result


@app.cell(hide_code=True)
def _(
    ACTIVITY,
    CASE_ID,
    COMPLETION_TIME,
    MANDATORY_COLUMNS,
    au,
    checkbox,
    event_log,
    pd,
):
    # Based on selected mandatory attributes, classify each attribute as mandatory, standard, or else

    activity_stats = event_log[ACTIVITY].value_counts()
    activity_list = list(activity_stats.index)

    data = []
    for activity in list(activity_stats.index):
        filtered_log = event_log[event_log[ACTIVITY] == activity]
        _counts = { col: filtered_log[col].count() for col in event_log.columns}
        data.append(_counts)
    columns_per_activity = pd.DataFrame.from_records(data, index=activity_stats.index)

    everywhere_non_empty_columns = [col for col in columns_per_activity.columns if (columns_per_activity[col] != 0).all()]

    STANDARD_COLUMNS = [col for col in everywhere_non_empty_columns if col not in MANDATORY_COLUMNS] # fully_filled_columns

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
        CASE_FEATURE_COLUMNS,
        STANDARD_COLUMNS,
        activity_list,
        activity_schema,
        activity_stats,
        attribute_overview,
    )


@app.cell(hide_code=True)
def _(
    activity_folding,
    activity_folding_result,
    activity_unfolding,
    activity_unfolding_result,
    enricher,
    manual_case_enrichment,
    manual_event_enrichment,
    mo,
):
    mo.ui.tabs({
        "Enricher": enricher,
        "Manual Event Enrichment": manual_event_enrichment,
        "Manual Case Enrichment": manual_case_enrichment,
        "Activity Folding": mo.vstack([activity_folding, activity_folding_result]),
        "Activity Unfolding": mo.vstack([activity_unfolding, activity_unfolding_result]),
    })
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Events View

    Use for overview or filter for a specific case, activity, or time period. Switch between event log and case table view.
    """)
    return


@app.cell(hide_code=True)
def _(activity_list, mo):
    activity_multiselect = mo.ui.multiselect(
        options=activity_list,
        value=activity_list[:1] if len(activity_list) >= 1 else activity_list,
        label="Select activities to see local attributes",
    )
    return (activity_multiselect,)


@app.cell(hide_code=True)
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
    du,
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
        du.table(_filtered_log, selection=None, page_size=15)
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
    du,
    event_log,
    local_view,
    mo,
):
    # du.table rather than the frames themselves: a timedelta column pushes marimo's
    # chart builder off the Arrow path, and the CSV fallback renames every column
    # containing a '.' -- which is every tracked enrichment.
    mo.ui.tabs({
        "Global Attributes": du.table(event_log[[col for col in MANDATORY_COLUMNS+STANDARD_COLUMNS if col not in CASE_FEATURE_COLUMNS]]),
        "Local Attributes": local_view,
        "Case Inspection": du.table(event_log[[col for col in MANDATORY_COLUMNS+STANDARD_COLUMNS+['folded_data'] if col not in CASE_FEATURE_COLUMNS]]),
        "Case Log": du.table(case_log),
        "Raw Events": du.table(event_log)
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
    du,
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

    activity_events = du.table(
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


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Attribute Rule Compliance
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    _sample_rule = '''def check_rule(df):
        # Relevant for the Sepsis event log: attribute SIRSCriteria2OrMore is expected to be True if at least
        # two of the attributes SIRSCritHeartRate, SIRSCritLeucos, SIRSCritTachypnea, and SIRSCritTemperature are True.

        criteria = ['SIRSCritHeartRate', 'SIRSCritLeucos', 'SIRSCritTachypnea', 'SIRSCritTemperature']

        # events where the attributes are not populated cannot be evaluated and are not violations
        evaluable = df[criteria + ['SIRSCriteria2OrMore']].notna().all(axis=1)
        populated = df[evaluable]

        expected = populated[criteria].astype(bool).sum(axis=1) >= 2
        return populated[expected != populated['SIRSCriteria2OrMore'].astype(bool)]
    '''

    rule_code_editor = mo.ui.code_editor(
        value=_sample_rule,
        language="python",
        label="Define check_rule(df):",
    )

    rule_check_button = mo.ui.run_button(label="Check rule")

    mo.vstack([
        mo.md("Domain-specific expectations about attribute values can be expressed as a rule and checked against the log."),
        mo.md("Write a function `check_rule(df)` that returns the rule violations."),
        rule_code_editor,
        rule_check_button,
    ])
    return rule_check_button, rule_code_editor


@app.cell(hide_code=True)
def _(
    ACTIVITY,
    CASE_ID,
    COMPLETION_TIME,
    dqu,
    event_log,
    mo,
    np,
    rule_check_button,
    rule_code_editor,
):
    # Evaluate the user-defined rule and report the violations
    if not rule_check_button.value:
        rule_check_result = mo.md("Press *Check rule* to evaluate the rule.")
    else:
        try:
            rule_violations = dqu.run_rule_check(
                event_log,
                rule_code_editor.value,
                context={
                    'CASE_ID': CASE_ID,
                    'ACTIVITY': ACTIVITY,
                    'COMPLETION_TIME': COMPLETION_TIME,
                    'np': np,
                },
            )

            _summary, _violating_cases = dqu.summarize_rule_violations(
                event_log, rule_violations, CASE_ID
            )

            rule_check_result = mo.vstack([
                _summary,
                mo.md(
                    "The violations could not be attributed to cases: the returned frame has "
                    f"no '{CASE_ID}' column and is not indexed by it."
                    if _violating_cases is None
                    else f"Violating cases ({len(_violating_cases)}): {_violating_cases[:50]}"
                    + (" ..." if len(_violating_cases) > 50 else "")
                ),
                mo.ui.table(rule_violations, selection=None, page_size=15),
            ])
        except Exception as _error:
            rule_check_result = mo.md(
                f"The rule could not be evaluated: `{type(_error).__name__}: {_error}`"
            )

    rule_check_result
    return


if __name__ == "__main__":
    app.run()
