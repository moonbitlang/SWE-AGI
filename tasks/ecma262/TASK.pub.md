## Goal

Implement a MoonBit **JavaScript expression evaluator** compatible with the
ECMAScript specification (ECMA-262) and this repository’s test suite.
The authoritative repo references are vendored in:

- `ecma262/specs/ecma262.md`
- `ecma262/specs/ES.txt`

## What This Task Is Really About

This is an exercise in implementing:

- A JavaScript expression parser
- A JavaScript runtime/evaluator for the tested subset
- A formatter whose output matches the suite’s expected strings exactly

**Important mindset**: The suite includes many coercion and formatting edge
cases; avoid hardcoding outputs for particular inputs.

## Approach

Build incrementally:

1. Literals (numbers/strings/bools/null/undefined).
2. Unary operators and basic conversions.
3. Binary operators and precedence (`+`, comparisons, logical ops).
4. Objects/arrays and built-ins used by tests.
5. Implement output formatting as a first-class contract (spacing/quotes/escapes).

Run tests frequently while adding features.

## Scope

In scope for this evaluator (as exercised by tests):

- Parsing and evaluating JavaScript expressions (not full programs)
- Numeric/string/boolean/null/undefined values and conversions used by tests
- Operator semantics and precedence for the tested subset
- Deterministic output formatting as a stable string

Repo-specific note (important):

- The returned string formatting is part of the conformance oracle; match it exactly.

Out of scope (not required by current tests):

- Full JS program execution (modules, statements, async IO)
- Host APIs (DOM, timers, networking)

## Required API

Complete the declarations in `ecma262_spec.mbt`.

Implementation notes:

- You can **freely decide** the project structure (modules/files/directories),
  the parsing/evaluation strategy, and any internal data structures.
- Do **not** modify the following files:
  - `ecma262_spec.mbt` - API specification
  - `specs/` folder - Reference documents
  - `*_pub_test.mbt` - Public test files (`ecma262_valid_pub_test.mbt`)
  - `*_priv_test.mbt` - Private test files (intended for private testing, but available here in a full-public test setting)
- Implement the required declarations by adding new `.mbt` files as needed.
- **You may add additional test files** (e.g., xxx_test.mbt) if needed for testing and maintenance purposes
  edge cases not covered by existing tests.

Required entry points:

- `@ecma262.eval_expr(expr : String) -> String`

## Behavioral rules

- Evaluate expressions with JavaScript-compatible semantics for the tested subset.
- The returned string must match the suite’s formatting exactly.
- Behavior must be deterministic.

## Test execution

```bash
cd ecma262
moon test
```

Use `moon test --update` only if you intentionally change snapshots.

If tests hang due to infinite loops or run out of memory, `try.py` (requires python3) can run each test individually with timeout and OOM detection:

```bash
python3 try.py
python3 try.py --timeout 60              # custom timeout (default: 30s)
python3 try.py --test-file foo_test.mbt  # run specific file
python3 try.py --json                    # output as JSONL
```

This is slower than `moon test` since it runs tests one by one.

## Constraints

### 1. Test Requirements

**All tests must pass for task completion**:

The model should keep running until all tests pass.

- **Public tests** (`*_pub_test.mbt`): Test cases visible in this repository
- **Private tests** (`*_priv_test.mbt`): Additional test cases (available in this full-public test setting)

**Testing Process**:

Run all tests locally to verify your solution:

```bash
moon test
```

All tests (both `*_pub_test.mbt` and `*_priv_test.mbt`) must pass for task completion.

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

- Solutions must be real parsers/evaluators, not test-specific lookup tables
- No hardcoded mappings derived from test fixtures
- Implementation should generalize to other expressions in the supported subset

### 3. Software Engineering Standards

**Modularity and Organization**:

- **Use subdirectories** to organize code by functional area:
  - `parser/` - Expression parsing and AST construction
  - `runtime/` - Value model and evaluation rules
  - `printer/` - Output formatting contract
  - `types/` - Core data structures and errors
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

- Logical separation of concerns (parsing → evaluation → formatting)
- Minimize coupling between modules
- Use appropriate abstractions (types, enums, structs)
- Avoid global mutable state

**Example directory structure**:

```
ecma262/
├── moon.mod.json
├── moon.pkg.json
├── ecma262_spec.mbt       # API declarations (do not modify)
├── ecma262.mbt            # Main entry point
├── parser/
│   └── parser.mbt
├── runtime/
│   └── eval.mbt
├── printer/
│   └── format.mbt
└── types/
    ├── value.mbt
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

This environment has public network access. You may consult ECMA-262 resources
online, but treat the vendored spec files in `specs/` as the authoritative
baseline for behavior in this task.
