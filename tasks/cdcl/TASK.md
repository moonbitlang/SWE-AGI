## Goal

Implement a MoonBit **SAT solver** (CDCL recommended) that can parse DIMACS CNF
and solve the benchmark instances included in this repository. The authoritative
repo references are vendored in:

- `cdcl/specs/cdcl.md`
- `cdcl/specs/DIMACS.md`

## What This Task Is Really About

This is an exercise in building a **real solver**:

- Parse DIMACS CNF into an internal CNF representation
- Implement a correct SAT algorithm (CDCL is recommended for performance)
- Return a satisfying model for SAT instances and validate it deterministically

Avoid hardcoding: benchmarks are large and varied.

## Approach

Build incrementally:

1. **DIMACS parsing**: comments/whitespace, clause termination, bounds checks.
2. **CNF model**: variable/literal representation and evaluation (`eval`).
3. **Baseline solver**: DPLL + unit propagation (optional stepping stone).
4. **CDCL**: watched literals, conflict analysis, learning, backjumping.
5. **Performance**: heuristics (VSIDS optional), restarts (optional), careful allocation.

Run tests frequently while adding features.

Important: The core logic must be implemented in MoonBit.

## Scope

In scope for this solver implementation:

- DIMACS CNF parsing into `CnfFormula`
- Model checking via `CnfFormula::eval`
- SAT solving via `solve`
- Deterministic behavior across runs

Repo-specific note (important):

- The suite validates models by checking `cnf.eval(model) == true`. Returning an
  invalid model is a hard failure even if the instance is satisfiable.

Out of scope (not required by current tests):

- UNSAT proof production
- Parallel solving or randomized heuristics

## Required API

Complete the declarations in `cdcl_spec.mbt`.

Implementation notes:

- You can **freely decide** the project structure (modules/files/directories),
  the solver strategy, and any internal data structures.
- Do **not** modify the following files:
  - `cdcl_spec.mbt` - API specification
  - `specs/` folder - Reference documents
  - `dimacs/` folder - Benchmark inputs used by tests
  - `*_valid_test.mbt` - Test files
- Implement the required declarations by adding new `.mbt` files as needed.
- **You may add additional test files** (e.g., xxx_test.mbt) if needed for testing and maintenance purposes

Required entry points:

- `@cdcl.DimacsParser::parse(source : Bytes) -> CnfFormula raise`
- `@cdcl.CnfFormula::eval(self : CnfFormula, model : Model) -> Bool`
- `@cdcl.solve(cnf : CnfFormula) -> SolveResult`

## Behavioral rules

- Parsing must correctly handle DIMACS comments/whitespace and multi-line clauses.
- For SAT instances, returned `model` must satisfy `cnf.eval(model) == true`.
- Solver must be deterministic.

## Test execution

**Use `try.py` to run tests** (recommended over `moon test`):

```bash
cd cdcl
python3 try.py
```

The `try.py` script provides essential safeguards for SAT solver development:

- **Per-test timeout**: Each test has a 30-second timeout (configurable via `--timeout`)
- **OOM detection**: Detects out-of-memory conditions (return codes 137, -9, or OOM messages)
- **Test isolation**: Runs each test individually, so one failing/hanging test doesn't block others
- **Progress tracking**: Shows which test is running and overall progress

Options:

- `python3 try.py --timeout 60` - Set per-test timeout to 60 seconds
- `python3 try.py --test-file foo_test.mbt` - Run tests from a specific file
- `python3 try.py --json` - Output results as JSONL (useful for automation)

**Why not `moon test`?** Running `moon test` directly can cause the entire test suite to hang indefinitely if a single test enters an infinite loop or exhausts memory. Use `try.py` to avoid this.

## Constraints

### 1. Test Requirements

**All tests must pass for task completion**:

The model should keep running until all tests pass.

- Test files in this directory are visible for development and debugging
- Hidden tests and benchmark variations are **hidden** in the evaluation environment

**⚠️ CRITICAL - Private Test Evaluation**:

Passing only the public tests is **INSUFFICIENT** and will result in task failure. The task is complete **only when both public and private test suites pass**.

**Why Private Tests Matter**:

- **Coverage**: Private tests are the primary measure of success and represent the majority of the evaluation
- **Comprehensiveness**: Validate correctness for general CNF instances, including edge cases and corner cases not exposed in public tests
- **Performance**: Include larger instances and variations that require efficient propagation/learning
- **Anti-cheating**: Prevent solutions that merely memorize or hardcode outcomes for the included benchmarks

**Evaluation Process**:

**Step 1 - Local Testing (Development Phase)**:

Before submitting for evaluation, ensure all public tests pass locally by running `moon test` in your project directory. Local testing helps you debug and iterate quickly, but **passing local tests alone does NOT complete this task**.

**Step 2 - Server Evaluation (REQUIRED - Task Completion)**:

⚠️ **MANDATORY STEP**: You **MUST** evaluate your solution against the full test suite (public + private) using the evaluation server. This is **NOT OPTIONAL**.

**The task is incomplete until server evaluation confirms all tests pass.**

To evaluate your solution:

```bash
swe-agi-submit --project cdcl --request-id eval-001
```

The server will respond with:

- `status`: "pass" or "fail"
- `summary`: Total test count, passed count, failed count
- `errors`: Up to 5 failure messages (if any tests failed)

**Success criteria for task completion**:

- `status` == "pass"
- `summary.failed` == 0 (all tests must pass, including all private tests)

**Important Notes**:

- You cannot see private test results during development
- Server evaluation is the **only way** to verify your solution against private tests
- **Do not consider the task complete** until server evaluation returns success
- If evaluation fails, fix the issues and re-evaluate until all tests pass

### 2. Code Quality Requirements

**Correctness**:

- Zero compiler errors, warnings, or diagnostics
- No runtime panics or unhandled edge cases
- Proper error handling with meaningful error messages

**Formatting**:

- Run `moon fmt` to format all code
- Run `moon info` to generate interface files (`.mbti`)
- Follow MoonBit style conventions consistently

**Implementation Integrity**:

- Solutions must be real solvers, not benchmark-specific lookup tables
- No hardcoded mappings derived from benchmark fixtures
- Implementation should work for arbitrary CNF inputs

### 3. Software Engineering Standards

**Modularity and Organization**:

- **Use subdirectories** to organize code by functional area:
  - `dimacs/` - Parsing DIMACS CNF into internal structures
  - `cnf/` - CNF data model and evaluation
  - `solver/` - Propagation, decision heuristics, learning/backjumping
  - `types/` - Core data structures and error types
- Group related functionality together
- Avoid dumping all code in the root directory

**File Size Limits**:

- Please try to keep each file to at most **1000 lines of core code** (excluding blank lines and comments)
- Split large modules into focused, single-responsibility files
- Use meaningful file names that reflect their purpose

**Readability**:

- Clear, descriptive function and variable names
- Add comments for complex algorithms or non-obvious logic
- Document public APIs and key data structures
- Keep functions focused (prefer multiple small functions over large monolithic ones)

**Code Structure**:

- Logical separation of concerns (parsing → representation → solving)
- Minimize coupling between modules
- Use appropriate abstractions (types, enums, structs)
- Avoid global mutable state

**Example directory structure**:

```
cdcl/
├── moon.mod.json
├── moon.pkg.json
├── cdcl_spec.mbt          # API declarations (do not modify)
├── cdcl.mbt               # Main entry point
├── dimacs/
│   └── parser.mbt
├── cnf/
│   ├── model.mbt
│   └── eval.mbt
├── solver/
│   ├── propagate.mbt
│   ├── analyze.mbt
│   └── cdcl.mbt
└── types/
    ├── cnf.mbt
    └── error.mbt
```

These standards ensure your code is maintainable, understandable, and follows professional software engineering practices.

## Documentation

**Write a comprehensive README.md**:

Your implementation must include a `README.md` file that documents:

- **Project overview**: What this parser implements and its purpose
- **Architecture**: High-level design decisions and module organization
- **Implementation approach**: Key algorithms, data structures, and parsing strategy
- **Usage examples**: How to use the API (parsing code, generating JSON)
- **Testing**: How to run tests and interpret results
- **Design decisions**: Rationale for important technical choices

The README should be written **based on your actual implementation** - describe the code you built, not generic information from specifications. It should help future developers understand your codebase quickly.

## External references

This environment has public network access. You may consult SAT/CDCL resources
online, but treat the vendored spec files in `specs/` as the authoritative
baseline for behavior in this task.
