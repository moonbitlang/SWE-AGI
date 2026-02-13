# SWE-AGI: Benchmarking Specification-Driven Software Construction with MoonBit in the Era of Autonomous Agents

SWE-AGI is an open-source benchmark for evaluating end-to-end, specification-
driven construction of production-scale software systems in MoonBit. Tasks
require agents to implement standards-compliant systems (e.g., parsers,
interpreters, binary decoders, SAT solvers) strictly from authoritative
specifications (RFCs/standards) under a fixed API scaffold.

SWE-AGI is designed to be retrieval-resistant: many target systems are largely
absent from the current MoonBit ecosystem, so success depends on sustained
specification comprehension, architectural decisions, and long-horizon
implementation rather than copying near-matching code.

## Paper Website

[swe-agi.com](https://swe-agi.com)

## Evaluation Results

[moonbitlang/SWE-AGI-Eval](https://github.com/moonbitlang/SWE-AGI-Eval) is where we store evaluation results.

## Repository Layout

- `tasks/`: spec-driven task suites (MoonBit modules/packages)
  - Start here: `tasks/README.md`
  - Evaluation protocol (public/private split): `tasks/EVALUATION.md`
  - Contributing new suites: `tasks/CONTRIBUTING.md`
- `docker/`: Docker-based client/server evaluation environment
  - See: `docker/README.md`
- `paper/`: LaTeX source for the SWE-AGI paper
- `website/`: scripts/templates for rendering a simple website/leaderboard

## Quick Start (Local)

1. Install the MoonBit toolchain.
2. Pick a suite under `tasks/` and run tests:

```bash
cd tasks/toml
moon test
```

Most suites follow the same conventions:

- `specs/`: normative references used to derive requirements and tests
- `TASK.md`: task statement, acceptance criteria, and constraints
- `*_spec.mbt`: declaration-first scaffold that freezes the public API
- `*_pub_test.mbt`: visible public tests for fast local iteration
- `*_priv_test.mbt`: held-out private tests used by the evaluator

## Agent Evaluation (Public/Private Split)

SWE-AGI scores only final submissions against hidden private tests. During
development, agents iterate locally using the public tests (a visible subset;
typically ~10% of the full suite), add their own spec-grounded checks, and
submit for evaluation via `swe-agi-submit` until the private test suite passes.

For the containerized client/server setup that enforces this split, see
`docker/README.md` and `tasks/EVALUATION.md`.

## Scope

SWE-AGI targets production-scale tasks in the 1e3 to 1e4 core-LOC regime and
currently consists of 22 tasks spanning seven categories (data formats, markup,
language front-ends, binary decoders, networking/protocol state machines,
template/DSL tasks, and SAT solving).

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=moonbitlang/SWE-AGI&type=Date)](https://www.star-history.com/#moonbitlang/SWE-AGI&Date)

## License

Licensed under the Apache License, Version 2.0. See `LICENSE`.

This repository also includes third-party specifications and test materials
under `tasks/**/specs/`, which may carry their own licenses; see the relevant
`specs/README.md`, `LICENSE`, and `NOTICE` files in those directories.
