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

## Result (4 October 2026)

Three conditions at a 1,500-token budget: the file list only (`baseline`), the
repository's source packed to the same budget (`whole_repo`), and Smriti's packed
context (`smriti`).

| Model | Baseline solved | Whole repo solved | Smriti solved |
| --- | --- | --- | --- |
| Qwen2.5-Coder-7B-Instruct Q4_K_M (llama.cpp, CPU) | 0/8 | 8/8 | 8/8 |
| Qwen2.5-0.5B-Instruct Q4_K_M (2 October, no whole-repo condition) | 0/8 | — | 0/8 |

With the 7B model, code context is decisive. Given only file names, the model
guessed function names (`calculate_total`, `apply_coupon`, …) and edited a real
function once, without fixing it. With code in the prompt, it found and fixed the
right function on every task. Smriti ties the whole-repo condition, because the
`shop` fixture is small enough (about 2,100 characters) to fit whole in the
budget. This shows that Smriti's context is sufficient. It cannot show that
Smriti beats simply including the repository; that needs repositories larger
than the budget.

The 0.5B model invented new function names in all 16 replies, so its run says
nothing about Smriti.
