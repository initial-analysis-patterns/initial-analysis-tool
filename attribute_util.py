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
    # unobserved categories (e.g. empty quantile bins) have probability 0 and contribute nothing
    probabilities = probabilities[probabilities > 0]
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


def get_monotonicity_label(non_decreasing, non_increasing):
    if non_decreasing and non_increasing:
        return 'constant'
    if non_decreasing:
        return 'non-decreasing'
    if non_increasing:
        return 'non-increasing'
    return 'none'


def get_log_level_monotonicity(event_log, attribute):
    # assumes the log is already globally ordered by completion time
    values = event_log[attribute].dropna()

    return get_monotonicity_label(
        values.is_monotonic_increasing, values.is_monotonic_decreasing
    )


def get_monotonicity_per_attribute(event_log, case_id_column, completion_time_column, attributes, check_log_level=False):
    # sorting once for all attributes, instead of once per attribute
    by_case = event_log.sort_values([case_id_column, completion_time_column])
    case_groups = by_case.groupby(case_id_column)

    def direction_flags(values):
        non_null = values.dropna()
        return non_null.is_monotonic_increasing, non_null.is_monotonic_decreasing

    rows = []
    for attribute in attributes:
        flags = case_groups[attribute].apply(direction_flags)
        non_decreasing = flags.map(lambda case_flags: case_flags[0])
        non_increasing = flags.map(lambda case_flags: case_flags[1])

        rows.append({
            'Attribute': attribute,
            'Monotonicity within cases': get_monotonicity_label(
                non_decreasing.all(), non_increasing.all()
            ),
            'Cases not monotonic': int((~(non_decreasing | non_increasing)).sum()),
            'Monotonicity over log': (
                get_log_level_monotonicity(event_log, attribute) if check_log_level else None
            ),
        })

    return pd.DataFrame(
        rows,
        columns=['Attribute', 'Monotonicity within cases', 'Cases not monotonic', 'Monotonicity over log'],
    ).set_index('Attribute')


def summarize_attribute_values(event_log, attributes):
    rows = []

    for attribute in attributes:
        values = event_log[attribute]
        non_null = values.dropna()
        counts = non_null.value_counts()
        is_numeric = pd.api.types.is_numeric_dtype(values)

        rows.append({
            'Attribute': attribute,
            'Events populated': int(len(non_null)),
            'Events populated %': round(len(non_null) / len(event_log) * 100, 2) if len(event_log) else None,
            'Distinct values': int(non_null.nunique()),
            'Most frequent value': counts.index[0] if not counts.empty else None,
            'Most frequent %': round(counts.iloc[0] / len(event_log) * 100, 2) if not counts.empty and len(event_log) else None,
            'Mean': round(non_null.mean(), 4) if is_numeric and not non_null.empty else None,
            'Median': non_null.median() if is_numeric and not non_null.empty else None,
        })

    return pd.DataFrame(rows, columns=[
        'Attribute', 'Events populated', 'Events populated %', 'Distinct values',
        'Most frequent value', 'Most frequent %', 'Mean', 'Median',
    ])


def _mutual_information_from_crosstab(x, y):
    joint = pd.crosstab(x, y, normalize=True).to_numpy()

    marginal_x = joint.sum(axis=1, keepdims=True)
    marginal_y = joint.sum(axis=0, keepdims=True)

    positive = joint > 0
    expected = (marginal_x @ marginal_y)[positive]

    return float((joint[positive] * np.log2(joint[positive] / expected)).sum())


def analyze_attribute_dependence(data, attributes=None, bins=10, max_distinct_values=None):
    """Normalized mutual information for every pair of attributes, plus Pearson correlation where both are numeric."""
    if attributes is None:
        attributes = data.columns.tolist()

    if max_distinct_values is not None:
        attributes = [a for a in attributes if data[a].nunique(dropna=True) <= max_distinct_values]

    binned = {attribute: discretize(data[attribute], bins) for attribute in attributes}

    correlations = data[attributes].corr(numeric_only=True)

    nmi_matrix = pd.DataFrame(float('nan'), index=attributes, columns=attributes)
    for attribute in attributes:
        nmi_matrix.loc[attribute, attribute] = 1.0

    rows = []
    for attribute_a, attribute_b in itertools.combinations(attributes, 2):
        mask = data[attribute_a].notna() & data[attribute_b].notna()

        if mask.any():
            x_binned = binned[attribute_a][mask]
            y_binned = binned[attribute_b][mask]

            hx = entropy(x_binned)
            hy = entropy(y_binned)
            mi = _mutual_information_from_crosstab(x_binned, y_binned)

            denominator = (hx + hy) / 2
            nmi = mi / denominator if denominator > 0 else 0.0
        else:
            nmi = None

        if nmi is not None:
            nmi_matrix.loc[attribute_a, attribute_b] = nmi
            nmi_matrix.loc[attribute_b, attribute_a] = nmi

        pearson = None
        if attribute_a in correlations.index and attribute_b in correlations.index:
            pearson = correlations.loc[attribute_a, attribute_b]

        rows.append({
            'attribute_a': attribute_a,
            'attribute_b': attribute_b,
            'NMI': round(nmi, 4) if nmi is not None else None,
            'Pearson': round(pearson, 4) if pearson is not None and pd.notna(pearson) else None,
            'Jointly populated rows': int(mask.sum()),
        })

    dependence_table = pd.DataFrame(rows, columns=[
        'attribute_a', 'attribute_b', 'NMI', 'Pearson', 'Jointly populated rows',
    ]).sort_values('NMI', ascending=False, na_position='last').reset_index(drop=True)

    return nmi_matrix, dependence_table


FUNCTIONAL_CARDINALITIES = ['one-to-one', 'many-to-one', 'one-to-many']


def functional_relationship(series_a, series_b):
    """Characterize the value-level relationship between two attributes over jointly-populated rows.

    Always returns a dict describing the pair. 'cardinality' is one of:
    - 'one-to-one'    : functional in both directions
    - 'many-to-one'   : a functionally determines b only
    - 'one-to-many'   : b functionally determines a only
    - 'many-to-many'  : neither direction is functional (not a functional relationship)
    - 'trivial'       : fewer than two distinct values on either side
    - 'disjoint'      : the two attributes are never jointly populated

    'direction' and 'mapping' are populated only for the three functional cardinalities and are None
    otherwise. 'n_a', 'n_b', 'n_pairs' are the distinct-value and distinct-pair counts over the
    jointly-populated rows. 'n_rows' is the number of rows where both attributes are populated and
    'support' is that count divided by the total number of rows (the common association-rule
    definition), i.e. the share of the log that backs the observed relationship. The non-functional
    cardinalities are reported for transparency and filtered out at display time.
    """
    mask = series_a.notna() & series_b.notna()
    n_rows = int(mask.sum())
    support = n_rows / len(series_a) if len(series_a) else 0.0
    pairs = pd.DataFrame({'a': series_a[mask], 'b': series_b[mask]}).drop_duplicates()

    n_a, n_b, n_pairs = pairs['a'].nunique(), pairs['b'].nunique(), len(pairs)
    result = {'cardinality': None, 'direction': None, 'mapping': None,
              'n_a': n_a, 'n_b': n_b, 'n_pairs': n_pairs, 'n_rows': n_rows, 'support': support}

    if n_pairs == 0:
        return {**result, 'cardinality': 'disjoint'}

    if n_a < 2 or n_b < 2:
        return {**result, 'cardinality': 'trivial'}  # fewer than two distinct values on either side

    a_determines_b = pairs.groupby('a')['b'].nunique().max() == 1
    b_determines_a = pairs.groupby('b')['a'].nunique().max() == 1

    if a_determines_b and b_determines_a:
        cardinality, direction, mapping = 'one-to-one', 'a_to_b', pairs.set_index('a')['b'].to_dict()
    elif a_determines_b:
        cardinality, direction, mapping = 'many-to-one', 'a_to_b', pairs.set_index('a')['b'].to_dict()
    elif b_determines_a:
        cardinality, direction, mapping = 'one-to-many', 'b_to_a', pairs.set_index('b')['a'].to_dict()
    else:
        return {**result, 'cardinality': 'many-to-many'}  # not a functional relationship

    return {**result, 'cardinality': cardinality, 'direction': direction, 'mapping': mapping}


def find_functional_relationships(event_log, columns=None):
    """Characterize every attribute pair; functional and non-functional pairs are both returned."""
    if columns is None:
        columns = event_log.columns.tolist()

    all_pairs = []
    for attribute_a, attribute_b in itertools.combinations(columns, 2):
        relationship = functional_relationship(event_log[attribute_a], event_log[attribute_b])
        all_pairs.append({
            'attribute_a': attribute_a,
            'attribute_b': attribute_b,
            'cardinality': relationship['cardinality'],
            'direction': relationship['direction'],
            'n_a': relationship['n_a'],
            'n_b': relationship['n_b'],
            'n_pairs': relationship['n_pairs'],
            'n_rows': relationship['n_rows'],
            'support': relationship['support'],
            'mapping': relationship['mapping'],
        })

    return pd.DataFrame(all_pairs, columns=[
        'attribute_a', 'attribute_b', 'cardinality', 'direction',
        'n_a', 'n_b', 'n_pairs', 'n_rows', 'support', 'mapping',
    ])
