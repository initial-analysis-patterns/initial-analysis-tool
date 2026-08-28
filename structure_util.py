import pandas as pd


def get_activity_occurrence_counts(event_log, case_id_column, activity_column):
    return event_log.groupby([case_id_column, activity_column]).size().unstack(fill_value=0)


def summarize_activity_occurrence(occurrence_counts):
    total_cases = len(occurrence_counts)

    cases_with_activity = (occurrence_counts > 0).sum()
    cases_once = (occurrence_counts == 1).sum()
    cases_multiple = (occurrence_counts > 1).sum()

    return pd.DataFrame({
        'Cases': cases_with_activity,
        'Coverage %': (cases_with_activity / total_cases * 100).round(2),
        'Cases (once)': cases_once,
        'Cases (once) %': (cases_once / total_cases * 100).round(2),
        'Cases (multiple)': cases_multiple,
        'Cases (multiple) %': (cases_multiple / total_cases * 100).round(2),
    }).sort_values('Coverage %', ascending=False)


def get_occurrence_distribution(occurrence_counts, activity):
    counts_in_cases = occurrence_counts[activity][occurrence_counts[activity] > 0]

    distribution = counts_in_cases.value_counts().sort_index()

    return pd.DataFrame({
        'Occurrences per case': distribution.index,
        'Cases': distribution.values,
        'Percentage of cases with activity': (distribution.values / len(counts_in_cases) * 100).round(2)
    })
