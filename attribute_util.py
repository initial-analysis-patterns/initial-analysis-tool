import itertools

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
