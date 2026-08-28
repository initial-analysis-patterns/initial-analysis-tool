import itertools

import numpy as np
import pandas as pd


def one_to_one_mapping(series_a, series_b):
    """Return the A -> B value mapping if the pair is one-to-one over jointly-populated rows, else None."""
    mask = series_a.notna() & series_b.notna()
    if not mask.any():
        return None

    pairs = pd.DataFrame({'a': series_a[mask], 'b': series_b[mask]}).drop_duplicates()

    if pairs['a'].nunique() < 2 or pairs['b'].nunique() < 2:
        return None  # trivial: fewer than two distinct values on either side

    a_to_b_unique = pairs.groupby('a')['b'].nunique().max() == 1
    b_to_a_unique = pairs.groupby('b')['a'].nunique().max() == 1

    if a_to_b_unique and b_to_a_unique:
        return pairs.set_index('a')['b'].to_dict()
    return None


def find_redundant_attribute_pairs(event_log, columns=None):
    if columns is None:
        columns = event_log.columns.tolist()

    redundant_pairs = []
    for attribute_a, attribute_b in itertools.combinations(columns, 2):
        mapping = one_to_one_mapping(event_log[attribute_a], event_log[attribute_b])
        if mapping is not None:
            redundant_pairs.append({
                'attribute_a': attribute_a,
                'attribute_b': attribute_b,
                'n_values': len(mapping),
                'mapping': mapping,
            })

    return pd.DataFrame(redundant_pairs)


FILLING_CLASSES = ['missing', 'populated once', 'populated multiple times (same value)', 'populated multiple times (different values)']


def classify_case(values):
    non_null = values.dropna()
    if len(non_null) == 0:
        return 'missing'
    if len(non_null) == 1:
        return 'populated once'
    if non_null.nunique() == 1:
        return 'populated multiple times (same value)'
    return 'populated multiple times (different values)'


def get_case_wise_filling(event_log, case_id_column, attribute):
    case_classification = event_log.groupby(case_id_column)[attribute].apply(classify_case)

    counts = case_classification.value_counts().reindex(FILLING_CLASSES, fill_value=0)
    percentages = (counts / len(case_classification) * 100).round(2)

    return pd.DataFrame({
        'Filling class': FILLING_CLASSES,
        'Cases': counts.values,
        'Percentage': percentages.values
    })


def get_value_distribution(event_log, attribute):
    # dropna=False keeps missing values in the counts instead of dropping them
    counts = event_log[attribute].value_counts(dropna=False)
    counts.index = counts.index.map(lambda value: 'missing' if pd.isna(value) else value)
    # different missing sentinels (NaN, None, NaT) are counted as one 'missing' value
    counts = counts.groupby(level=0, sort=False).sum()
    percent = counts / len(event_log) * 100
    return pd.DataFrame(
        [counts.values, percent.values],
        index=['count', 'percent'],
        columns=counts.index,
    )


def get_numeric_summary(event_log, attribute):
    values = event_log[attribute].dropna()
    return pd.Series({
        'average': values.mean(),
        'variance': values.var(),
        'stdev': values.std(),
        'median': values.median(),
    }, name=attribute)


def characterize_attribute_values(event_log, attribute):
    if pd.api.types.is_numeric_dtype(event_log[attribute]):
        return get_numeric_summary(event_log, attribute).to_frame().T

    return get_value_distribution(event_log, attribute)


def get_case_level_monotonic_flags(event_log, case_id_column, completion_time_column, attribute):
    by_case = event_log.sort_values([case_id_column, completion_time_column])

    def is_monotonic(series):
        return series.dropna().is_monotonic_increasing

    return by_case.groupby(case_id_column)[attribute].apply(is_monotonic)


def is_log_level_monotonic(event_log, attribute):
    # assumes the log is already globally ordered by completion time
    return event_log[attribute].dropna().is_monotonic_increasing


def count_changes(series):
    non_null = series.dropna()
    if non_null.empty:
        return None  # attribute never populated in this case - excluded from the statistics
    # comparing against shift() flags the first non-null value as a "change" too (it has no predecessor), so subtract 1 to correct for that
    return (non_null != non_null.shift()).sum() - 1


def get_change_counts_per_case(event_log, case_id_column, completion_time_column, activity_column, activity, attribute):
    # a stable sort keeps the original row order for events of a case that share a timestamp
    ordered_log = event_log.sort_values(
        by=[case_id_column, completion_time_column], kind='stable'
    )
    activity_log = ordered_log[ordered_log[activity_column] == activity]
    counts = activity_log.groupby(case_id_column)[attribute].apply(count_changes)
    return counts.dropna()


def discretize(series, bins):
    if pd.api.types.is_numeric_dtype(series):
        return pd.qcut(series, bins, duplicates='drop')
    return series


def entropy(series):
    probabilities = series.dropna().value_counts(normalize=True)
    return -(probabilities * np.log2(probabilities)).sum()


def mutual_information(x, y):
    joint = pd.crosstab(x, y, normalize=True)
    px = joint.sum(axis=1)
    py = joint.sum(axis=0)
    mi = 0.0
    for i in joint.index:
        for j in joint.columns:
            p_xy = joint.loc[i, j]
            if p_xy > 0:
                mi += p_xy * np.log2(p_xy / (px[i] * py[j]))
    return mi


def normalized_mutual_information(x, y, bins):
    mask = x.notna() & y.notna()
    if not mask.any():
        return None  # no jointly-populated rows

    x_binned = discretize(x[mask], bins)
    y_binned = discretize(y[mask], bins)

    hx = entropy(x_binned)
    hy = entropy(y_binned)
    mi = mutual_information(x_binned, y_binned)

    denom = (hx + hy) / 2
    nmi = mi / denom if denom > 0 else 0.0

    return hx, hy, mi, nmi
