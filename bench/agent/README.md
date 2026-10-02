# Coding-agent task-success comparison (optional)

`compare.py` measures whether Smriti's context helps a coding model fix bugs.
The fixture `shop` package is correct code; each of the 8 tasks in `tasks.json`
injects one bug, and the harness verifies that the task's check passes on the
clean fixture and fails after injection. For every task, a local model gets the
issue plus either the repository file list (`baseline`) or Smriti's packed
context at 1,500 tokens (`smriti`), and must reply with one corrected function.
The reply replaces the same-named definition and the check runs with bytecode
caching disabled. One attempt per task and condition, temperature 0.

```sh
python -m bench.agent.compare <model.gguf> --output bench/agent/results.json
```

`tests/test_agent_compare.py` validates the harness: an oracle agent that returns
the correct function solves 8/8 in both conditions; an agent that returns no code
solves 0/8.

## Result (2 October 2026)

| Model | Baseline solved | Smriti solved |
| --- | --- | --- |
| Qwen2.5-0.5B-Instruct Q4_K_M (llama.cpp, CPU) | 0/8 | 0/8 |

This result is uninformative about Smriti. The 0.5B model invented new function
names (`adjust_price`, `fix_receipts`, …) in all 16 replies instead of editing the
named definition, even when the Smriti prompt contained the buggy function, so
no reply could be applied in either condition. A stronger coder model is needed
for a meaningful comparison; the network was unavailable to download one during
this run. Re-run the command above with any instruct GGUF to extend the table.
