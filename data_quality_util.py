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


def run_rule_check(event_log, rule_code, context=None):
    """Execute user-provided rule code and return what its check_rule function reports as violations.

    The code must define check_rule(df); it is executed in a namespace containing pandas as 'pd'
    plus whatever is passed in context (typically the mandatory attribute names).
    """
    scope = {'pd': pd}
    if context:
        scope.update(context)

    exec(rule_code, scope)

    if 'check_rule' not in scope:
        raise ValueError("The rule code must define a function check_rule(df).")

    violations = scope['check_rule'](event_log)

    if isinstance(violations, pd.Series):
        violations = violations.to_frame()

    if not isinstance(violations, pd.DataFrame):
        raise TypeError("check_rule(df) must return a DataFrame or a Series of violations.")

    return violations


def get_violating_cases(violations, case_id_column):
    """The case identifiers in a violations frame, whether they are a column or the index."""
    if case_id_column in violations.columns:
        return violations[case_id_column].dropna().unique().tolist()

    if violations.index.name == case_id_column:
        return violations.index.dropna().unique().tolist()

    return None  # the violations cannot be attributed to cases


def summarize_rule_violations(event_log, violations, case_id_column):
    violating_cases = get_violating_cases(violations, case_id_column)
    cases_in_log = event_log[case_id_column].nunique() if case_id_column in event_log.columns else None

    if violating_cases is None:
        cases_violating = None
        share = None
    else:
        cases_violating = len(violating_cases)
        share = round(cases_violating / cases_in_log * 100, 2) if cases_in_log else None

    summary = pd.DataFrame({
        'Violations reported': [len(violations)],
        'Cases violating': [cases_violating],
        'Cases in log': [cases_in_log],
        'Cases violating %': [share],
    })

    return summary, violating_cases
