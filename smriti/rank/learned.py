"""Small deterministic CPU logistic ranking model with explicit feature contracts."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class CPURanker:
    weights: np.ndarray
    mean: np.ndarray
    scale: np.ndarray

    @classmethod
    def fit(
        cls,
        features: Any,
        labels: Any,
        steps: int = 500,
        learning_rate: float = 0.05,
        regularization: float = 0.01,
    ) -> 'CPURanker':
        values = np.asarray(features, dtype=np.float64)
        target = np.asarray(labels, dtype=np.float64)
        if values.ndim != 2 or values.shape[0] != len(target) or values.shape[1] == 0:
            raise ValueError('Aligned nonempty feature matrix and binary labels required')
        if (
            not np.isfinite(values).all()
            or not np.isfinite(target).all()
            or not set(target) <= {0.0, 1.0}
        ):
            raise ValueError('Finite features and binary labels required')
        if not len(target) or not 0 < target.sum() < len(target):
            raise ValueError('Training requires both positive and negative candidates')
        if steps < 1 or learning_rate <= 0 or regularization < 0:
            raise ValueError('Invalid training configuration')
        mean = values.mean(axis=0)
        scale = np.maximum(values.std(axis=0), 1e-12)
        design = np.column_stack([np.ones(len(values)), (values - mean) / scale])
        weights = np.zeros(design.shape[1])
        balanced = np.where(target == 1, 0.5 / target.sum(), 0.5 / (len(target) - target.sum()))
        for _ in range(steps):
            logits = np.clip(design @ weights, -40, 40)
            probabilities = 1 / (1 + np.exp(-logits))
            penalty = regularization * weights
            penalty[0] = 0
            weights -= learning_rate * (design.T @ ((probabilities - target) * balanced) + penalty)
        return cls(weights, mean, scale)

    @classmethod
    def fit_validation(
        cls,
        rows: Iterable[tuple[str, list[float], int]],
        split: Callable[[str], str],
        **options: Any,
    ) -> 'CPURanker':
        """Train only on instances the evaluation split assigns to validation."""
        rows = list(rows)
        leaked = sorted({instance for instance, _, _ in rows if split(instance) != 'validation'})
        if leaked:
            raise ValueError(f'Held-out instances must not train the ranker: {leaked[:3]}')
        return cls.fit([row[1] for row in rows], [row[2] for row in rows], **options)

    def predict(self, features: Any) -> np.ndarray:
        values = np.asarray(features, dtype=np.float64)
        if values.ndim != 2 or values.shape[1] != len(self.mean) or not np.isfinite(values).all():
            raise ValueError('Finite feature matrix matching model dimensionality required')
        design = np.column_stack([np.ones(len(values)), (values - self.mean) / self.scale])
        return np.asarray(design @ self.weights, dtype=np.float64)
