import numpy as np
import pytest

from smriti.rank.learned import CPURanker


def test_cpu_ranker_learns_order_and_is_deterministic():
    features = [[0, 0], [0.1, 0.2], [0.8, 0.7], [1, 1]]
    labels = [0, 0, 1, 1]
    first = CPURanker.fit(features, labels)
    second = CPURanker.fit(features, labels)
    assert first.predict(features)[2] > first.predict(features)[1]
    assert np.array_equal(first.weights, second.weights)
    with pytest.raises(ValueError):
        CPURanker.fit(features, [1, 1, 1, 1])
    with pytest.raises(ValueError):
        first.predict([[float('nan'), 0]])


def test_cpu_ranker_refuses_held_out_training_rows():
    from bench.swebench.splits import instance_split

    ids = [f'repo__task-{n}' for n in range(40)]
    validation = [i for i in ids if instance_split(i) == 'validation']
    held_out = next(i for i in ids if instance_split(i) == 'held_out')
    rows = [(v, [float(n), 0.0], n % 2) for n, v in enumerate(validation)]
    model = CPURanker.fit_validation(rows, instance_split)
    assert len(model.mean) == 2
    with pytest.raises(ValueError, match='Held-out'):
        CPURanker.fit_validation([*rows, (held_out, [0.0, 0.0], 0)], instance_split)
