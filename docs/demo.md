# Reproducible demos

From the repository root after installing Smriti, run these commands. Each uses a
new temporary fixture and checks the actual result before printing JSON.

| Scenario | Command | Evidence |
| --- | --- | --- |
| Cold index, one-line edit | `python scripts/demo_index.py --files 20` | Indexed file count, one changed file, measured seconds |
| Issue context | `python scripts/demo_context.py` | Real token count, tokenizer, selected code within 8,000 tokens |
| Session persistence | `python scripts/demo_sessions.py` | Same fact and code anchor after closing and reopening SQLite |
| Memory history | `python scripts/demo_memory_history.py` | Rename identity, stale reason, blocked conflict, resolved merge, revert |

These small synthetic fixtures demonstrate behavior. They do not measure SWE-bench
accuracy or establish production latency. The memory-history script drives the
parser identity adapter and memory branches directly; Git synchronization has its
own integration tests.

[Watch the recorded walkthrough](demo/smriti-demo.webm). Its four five-second scenes
are explicitly labeled as a replay of freshly executed results. Timing values
come from `perf_counter`; [the accompanying JSON](demo/smriti-demo.json) retains the
complete outputs. The video duration is independent of execution time.

To regenerate it, install `websockets>=14,<16` in the Python used for the recorder,
install Chrome, then run:

```powershell
python scripts/record_demo.py --python .venv/Scripts/python.exe --output docs/demo/smriti-demo.webm
```

The recorder starts an isolated headless Chrome profile with a loopback debugging
endpoint, renders actual results on a canvas, encodes WebM with MediaRecorder,
and terminates its browser. `--chrome` selects another Chrome executable. Its
JSON report and final-scene PNG use the same output basename.
