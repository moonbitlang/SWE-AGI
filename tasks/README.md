# SWE-AGI Task Suite (MoonBit)

This directory contains the SWE-AGI task suite: 22 specification-driven,
production-scale software construction tasks in MoonBit. Each task is packaged
as a cold-start starter repository with normative references and a fixed API
scaffold, and is scored only by whether the final submission passes hidden
private tests.

## Task Packaging

Each task directory contains:

- `specs/`: normative references (standards, RFCs, and other authoritative docs)
- `TASK.md`: task statement, acceptance criteria, and constraints
- `moon.mod.json`, `moon.pkg.json`: MoonBit module/package metadata
- `*_spec.mbt`: declaration-first scaffold that freezes the public API
- `*_pub_test.mbt`: visible public tests for local iteration
- `*_priv_test.mbt`: held-out private tests used by the evaluator

Many tasks also include `README.mbt.md` and auxiliary scripts/fixtures to
support test generation and provenance tracking.

## Quick Start

Prerequisites:

- MoonBit toolchain installed

Run tests for a single task:

```bash
cd toml
moon test
```

Format and type-check:

```bash
moon fmt
moon check
moon info
```

## Public/Private Split Evaluation

SWE-AGI uses a public/private test split: agents develop against public tests
and submit for scoring against hidden private tests via `swe-agi-submit`.

See `EVALUATION.md` for the end-to-end evaluation protocol and `../docker/` for
the containerized client/server harness that enforces the split.

## Tasks

Template and domain-specific languages:

- `pug`
- `jq`

Data serialization and configuration formats:

- `csv`
- `ini`
- `yaml`
- `toml`

Markup and document formats:

- `xml`
- `html5`

Programming language front-ends:

- `c99`
- `lua`
- `ecma262`
- `python`
- `r6rs`

Binary formats and streaming decoders:

- `git_object`
- `protobuf`
- `zip`
- `capnp`
- `wasm`

Networking and protocol state machines:

- `uri`
- `hpack`
- `url`

Automated reasoning and SAT solving:

- `cdcl`

## Contributing

See `CONTRIBUTING.md`.

## License

Apache License 2.0. See `LICENSE`.

Third-party specifications and test materials under `*/specs/` may carry their
own licenses. See the relevant `specs/README.md`, `LICENSE`, and `NOTICE` files
in those directories.
