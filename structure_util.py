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


def get_activity_baseline(event_log, activity_column):
    """Record what is needed to describe an activity transformation, without copying the log itself."""
    return event_log[activity_column].value_counts(), list(event_log.columns)


def apply_activity_transformation(event_log, transformation_code, function_name, context=None):
    """Execute user-provided code on the event log and return the resulting log.

    The code must define a function named function_name, which receives the event log itself - not a
    copy - and returns it after modification, so that assignments such as df[col] = ... change the
    log in place. It is executed in a namespace containing pandas as 'pd' plus whatever is passed in
    context (typically the mandatory attribute names).
    """
    scope = {'pd': pd}
    if context:
        scope.update(context)

    exec(transformation_code, scope)

    if function_name not in scope:
        raise ValueError(f"The code must define a function {function_name}(df).")

    transformed_log = scope[function_name](event_log)

    if not isinstance(transformed_log, pd.DataFrame):
        raise TypeError(f"{function_name}(df) must return the modified event log as a DataFrame.")

    return transformed_log


def apply_activity_folding(event_log, folding_code, context=None):
    return apply_activity_transformation(event_log, folding_code, 'fold_activities', context)


def apply_activity_unfolding(event_log, unfolding_code, context=None):
    return apply_activity_transformation(event_log, unfolding_code, 'unfold_activities', context)


def summarize_activity_transformation(baseline, transformed_log, activity_column):
    """Compare the activity types before and after the transformation, and list the attributes added."""
    before, before_columns = baseline
    after = transformed_log[activity_column].value_counts()

    counts = pd.DataFrame({'Events before': before, 'Events after': after}).fillna(0).astype(int)

    counts['Change'] = [
        'removed' if row['Events after'] == 0
        else 'new' if row['Events before'] == 0
        else 'unchanged' if row['Events before'] == row['Events after']
        else 'changed'
        for _, row in counts.iterrows()
    ]

    counts = counts.sort_values(['Change', 'Events after'], ascending=[True, False])
    counts.index.name = activity_column

    added_attributes = [col for col in transformed_log.columns if col not in before_columns]

    return counts, added_attributes
