import pandas as pd


def get_duplicate_event_mask(event_log, case_id_column, comparison_columns=None, keep=False):
    if comparison_columns is None:
        comparison_columns = [col for col in event_log.columns if col != case_id_column]

    return event_log.groupby(case_id_column, sort=False, group_keys=False).apply(
        lambda trace: trace.duplicated(subset=comparison_columns, keep=keep)
    )


def find_duplicate_events(event_log, case_id_column, comparison_columns=None):
    return event_log[
        get_duplicate_event_mask(event_log, case_id_column, comparison_columns, keep=False)
    ]


def remove_duplicate_events(event_log, case_id_column, comparison_columns=None):
    return event_log[
        ~get_duplicate_event_mask(event_log, case_id_column, comparison_columns, keep='first')
    ]


def get_duplicate_activities_by_case(duplicate_events, case_id_column, activity_column):
    return (
        duplicate_events.groupby(case_id_column)[activity_column]
        .apply(lambda names: sorted(set(names)))
        .reset_index(name='duplicated_activities')
    )
