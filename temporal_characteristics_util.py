import re

import pandas as pd

def infer_timestamp_format_from_column(series):
    """
    Infer a common timestamp format from a pandas Series.

    Supports:
      %Y-%m-%d
      %Y-%d-%m
      %m-%d-%Y
      %d-%m-%Y

    with optional:
      HH:MM:SS
      timezone offset like +00:00
    """

    candidates = {
        "YMD": "%Y-%m-%d",
        "YDM": "%Y-%d-%m",
        "MDY": "%m-%d-%Y",
        "DMY": "%d-%m-%Y",
    }

    possible = set(candidates.keys())
    detected_suffix = None

    for value in series.dropna():
        s = str(value).strip()

        match = re.match(
            r"^(\d{1,4})[-/](\d{1,2})[-/](\d{1,4})"
            r"(?:[ T](\d{2}):(\d{2}):(\d{2})([+-]\d{2}:\d{2}|Z)?)?$",
            s
        )

        if not match:
            continue

        a, b, c, hour, minute, second, tz = match.groups()
        a, b, c = int(a), int(b), int(c)

        valid_for_row = set()

        if len(match.group(1)) == 4 and 1 <= b <= 12 and 1 <= c <= 31:
            valid_for_row.add("YMD")

        if len(match.group(1)) == 4 and 1 <= b <= 31 and 1 <= c <= 12:
            valid_for_row.add("YDM")

        if len(match.group(3)) == 4 and 1 <= a <= 12 and 1 <= b <= 31:
            valid_for_row.add("MDY")

        if len(match.group(3)) == 4 and 1 <= a <= 31 and 1 <= b <= 12:
            valid_for_row.add("DMY")

        possible &= valid_for_row

        if hour is not None:
            detected_suffix = (
                "T%H:%M:%S"
                if "T" in s
                else " %H:%M:%S"
            )

            if tz is not None:
                detected_suffix += "%z"

        if len(possible) == 1:
            break

    if len(possible) == 1:
        key = next(iter(possible))
        return {
            "status": "DETECTED",
            "format": candidates[key] + (detected_suffix or "")
        }

    if len(possible) > 1:
        return {
            "status": "AMBIGUOUS",
            "format": ", ".join(
                candidates[x] + (detected_suffix or "")
                for x in sorted(possible)
            )
        }

    return {
        "status": "NOT DETECTED",
        "format": None
    }


COMPONENT_LEVELS = [
    'year',
    'month',
    'day',
    'hour',
    'minute',
    'second',
    'millisecond',
    'sub-millisecond',
    'timezone'
]


_FREQ_ALIASES = {
    'year': 'Y',
    'month': 'm',
    'day': 'D',
    'hour': 'h',
    'minute': 'min',
    'second': 's',
    'millisecond': 'ms'
}


def get_components(ts):
    return (
        ts.year,
        ts.month,
        ts.day,
        ts.hour,
        ts.minute,
        ts.second,
        ts.microsecond // 1000,
        (ts.microsecond % 1000) * 1000 + ts.nanosecond,
        str(ts.tzinfo) if ts.tzinfo is not None else None,
    )

def analyze_timestamp_components(event_log):
    timestamp_columns = [
        col
        for col in event_log.columns
        if (
            isinstance(event_log[col].dtype, pd.DatetimeTZDtype)
            or pd.api.types.is_datetime64_dtype(event_log[col])
        )
    ]
    # detailed component analysis
    summaries = []
    for col in timestamp_columns:
        timestamps = event_log[col].dropna()
        if timestamps.empty:
            continue
        components_df = pd.DataFrame(
            timestamps.apply(get_components).tolist(),
            columns=COMPONENT_LEVELS
        )
        # dropna=False ensures that timezone-naive timestamps are treated
        # as having one consistent "no timezone" value
        unique_counts = components_df.nunique(dropna=False)
        is_constant = unique_counts == 1
        summary = pd.DataFrame({
            'Timestamp column': col,
            'Level': COMPONENT_LEVELS,
            'Constant': is_constant.values,
            'Unique values': unique_counts.values,
            'Value': [
                components_df[level].iloc[0]
                if is_constant[level]
                else None
                for level in COMPONENT_LEVELS
            ],
        })
        summaries.append(summary)
    if summaries:
        timestamp_component_summary = pd.concat(
            summaries,
            ignore_index=True
        )
    else:
        timestamp_component_summary = pd.DataFrame(
            columns=[
                'Timestamp column',
                'Level',
                'Constant',
                'Unique values',
                'Value'
            ]
        )
    # determine the constant temporal prefix for each timestamp column
    # timezone is excluded because it is not part of the
    # coarsest-to-finest temporal hierarchy
    constant_prefixes = []
    for col in timestamp_columns:
        timestamps = event_log[col].dropna()
        if timestamps.empty:
            continue
        components_df = pd.DataFrame(
            timestamps.apply(get_components).tolist(),
            columns=COMPONENT_LEVELS
        )
        unique_counts = components_df.nunique(dropna=False)
        constant_prefix = []
        for level in COMPONENT_LEVELS[:-1]:
            if unique_counts[level] != 1:
                break
            constant_prefix.append(
                f"{level}={components_df[level].iloc[0]}"
            )
        constant_prefixes.append({
            'Timestamp column': col,
            'Constant prefix': (
                ', '.join(constant_prefix)
                if constant_prefix
                else 'None'
            )
        })
    timestamp_constant_prefixes = pd.DataFrame(constant_prefixes)
    return timestamp_component_summary, timestamp_constant_prefixes


def analyze_event_ordering(event_log, case_id_column, completion_time_column):
    case_ordering = (
        event_log
        .groupby(case_id_column)[completion_time_column]
        .apply(lambda timestamps: timestamps.is_monotonic_increasing)
    )
    cases_total = len(case_ordering)
    cases_ordered = case_ordering.sum()
    cases_unordered = cases_total - cases_ordered
    case_ordering_summary = pd.DataFrame({
        'Cases': [cases_total],
        'Ordered': [cases_ordered],
        'Not ordered': [cases_unordered],
        'All ordered': [case_ordering.all()]
    })
    log_ordered = event_log[
        completion_time_column
    ].is_monotonic_increasing
    log_ordering_summary = pd.DataFrame({
        'Events': [len(event_log)],
        'Globally ordered': [log_ordered]
    })
    return case_ordering_summary, log_ordering_summary
