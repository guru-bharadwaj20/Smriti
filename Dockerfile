# Optional container build. Model weights are never baked in; mount them at
# /models and set SMRITI_MODEL_DIR to enable vector retrieval.
FROM python:3.12-slim AS build
WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY smriti ./smriti
RUN pip install --no-cache-dir build && python -m build --wheel --outdir /dist

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home smriti
COPY --from=build /dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl
COPY scripts/smoke_install.py /opt/smriti/smoke_install.py
USER smriti
WORKDIR /repo
ENTRYPOINT ["smriti"]
CMD ["--help"]
