"""Repository defaults < TOML configuration < explicit environment overrides."""
from dataclasses import dataclass
import os
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class Config:
    root: Path
    data_dir: Path
    budget: int = 8000
    tokenizer: str = 'cl100k_base'


def load_config(root: Path, environ: dict[str, str] | None = None) -> Config:
    root = root.resolve()
    file = root / 'smriti.toml'
    values = tomllib.loads(file.read_text(encoding='utf-8')).get('smriti', {}) if file.exists() else {}
    unknown = set(values) - {'data_dir', 'budget', 'tokenizer'}
    if unknown:
        raise ValueError(f'Unknown configuration keys: {sorted(unknown)}')
    env = os.environ if environ is None else environ
    directory = Path(env.get('SMRITI_DATA_DIR', str(values.get('data_dir', '.smriti'))))
    budget = int(env.get('SMRITI_BUDGET', str(values.get('budget', 8000))))
    if budget < 0:
        raise ValueError('Token budget cannot be negative')
    return Config(root, (root / directory).resolve(), budget,
                  env.get('SMRITI_TOKENIZER', str(values.get('tokenizer', 'cl100k_base'))))
