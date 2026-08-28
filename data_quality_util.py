import pandas as pd


def find_duplicate_events(event_log, comparison_columns=None):
    return event_log[
        event_log.duplicated(subset=comparison_columns, keep=False)
    ]


def remove_duplicate_events(event_log, comparison_columns=None):
    return event_log[
        ~event_log.duplicated(subset=comparison_columns, keep='first')
    ]


def summarize_duplicate_events(event_log, comparison_columns=None):
    if comparison_columns is None:
        comparison_columns = event_log.columns.tolist()

    duplicate_events = find_duplicate_events(event_log, comparison_columns)

    if duplicate_events.empty:
        kept_instances = duplicate_events.copy()
        kept_instances['Occurrences'] = pd.Series(dtype='int64')
        kept_instances['Removed'] = pd.Series(dtype='int64')
        return kept_instances

    kept_instances = duplicate_events.assign(
        Occurrences=duplicate_events.groupby(
            comparison_columns, dropna=False, sort=False
        )[comparison_columns[0]].transform('size')
    )
    kept_instances = kept_instances[
        ~kept_instances.duplicated(subset=comparison_columns, keep='first')
    ]
    kept_instances['Removed'] = kept_instances['Occurrences'] - 1

    return kept_instances
