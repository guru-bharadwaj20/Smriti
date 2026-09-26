from bench.swebench.report import paired_interval, summarize


def test_paired_bootstrap_uses_instances_and_empty_gold_is_undefined():
    rows = [
        {
            'results': {
                'full': {'function_recall': {'10': 0.8}},
                'bm25': {'function_recall': {'10': 0.3}},
            }
        },
        {
            'results': {
                'full': {'function_recall': {'10': None}},
                'bm25': {'function_recall': {'10': None}},
            }
        },
    ]
    result = paired_interval(rows, 'full', 'bm25', samples=50)
    assert result['paired_instances'] == 1
    assert result['mean_difference'] == 0.5
    assert result['interval95'] == [0.5, 0.5]
    assert result == paired_interval(rows, 'full', 'bm25', samples=50)


def test_tooling_failure_does_not_fabricate_score():
    manifest = {
        'dataset_rows': 2,
        'instances': [{'evaluation_id': 'same'}, {'evaluation_id': 'same'}],
    }
    report = summarize(
        [], [{'evaluation_id': 'same', 'configuration_id': 'c', 'stage': 'checkout'}], manifest, 'c'
    )
    assert report['measured_unique'] == 0
    assert report['remaining_unique'] == 1
    assert report['failures_by_stage'] == {'checkout': 1}
    assert report['splits']['held_out']['methods']['full']['mean_function_recall10'] is None
