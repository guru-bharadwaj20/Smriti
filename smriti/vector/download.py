"""Download explicitly requested pinned public artifacts, verifying SHA-256."""

import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Any


def download_model(directory: str | Path, quantized: bool = False) -> tuple[Path, Path]:
    manifest: dict[str, Any] = json.loads(
        Path(__file__).with_name('model_manifest.json').read_text()
    )
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    artifact = 'onnx/model_quint8_avx2.onnx' if quantized else 'onnx/model.onnx'
    files = [artifact, 'tokenizer.json']
    for file in files:
        target = directory / Path(file).name
        url = f'https://huggingface.co/{manifest["model"]}/resolve/{manifest["revision"]}/{file}'
        if not target.exists():
            temporary = target.with_suffix(target.suffix + '.partial')
            with (
                urllib.request.urlopen(url, timeout=120) as response,
                temporary.open('wb') as output,
            ):
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            temporary.replace(target)
        expected = manifest['sha256'].get(file)
        if expected and hashlib.file_digest(target.open('rb'), 'sha256').hexdigest() != expected:
            raise ValueError(f'checksum mismatch for {file}')
    return directory / Path(artifact).name, directory / 'tokenizer.json'
