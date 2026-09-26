"""Repository defaults < TOML configuration < explicit environment overrides."""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    root: Path
    data_dir: Path
    budget: int = 8000
    tokenizer: str = 'cl100k_base'
    model_dir: Path | None = None


def load_config(root: Path, environ: dict[str, str] | None = None) -> Config:
    root = root.resolve()
    file = root / 'smriti.toml'
    values = (
        tomllib.loads(file.read_text(encoding='utf-8')).get('smriti', {}) if file.exists() else {}
    )
    unknown = set(values) - {'data_dir', 'budget', 'tokenizer', 'model_dir'}
    if unknown:
        raise ValueError(f'Unknown configuration keys: {sorted(unknown)}')
    env = os.environ if environ is None else environ
    directory = Path(env.get('SMRITI_DATA_DIR', str(values.get('data_dir', '.smriti'))))
    budget = int(env.get('SMRITI_BUDGET', str(values.get('budget', 8000))))
    if budget < 0:
        raise ValueError('Token budget cannot be negative')
    model = env.get('SMRITI_MODEL_DIR', values.get('model_dir'))
    return Config(
        root,
        (root / directory).resolve(),
        budget,
        env.get('SMRITI_TOKENIZER', str(values.get('tokenizer', 'cl100k_base'))),
        (root / Path(model)).resolve() if model is not None else None,
    )
