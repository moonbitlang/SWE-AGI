## Goal

Implement a MoonBit **Lua 5.4 interpreter** that can execute Lua chunks and pass
this repository’s test suite. The authoritative repo references are vendored in:

- `lua/specs/lua.md`
- `lua/specs/lua-5.4.8-manual.of`
- `lua/specs/README.md`

## What This Task Is Really About

This is an exercise in building a **real language implementation**:

- parsing Lua source into an executable form
- implementing Lua runtime semantics for the tested subset
- providing standard libraries required by the suite

Avoid hardcoding: tests include many programs and runtime behaviors.

## Approach

Build incrementally:

1. Lexer/parser for Lua chunk syntax used by tests.
2. Core runtime: values, environments, function calls, control flow.
3. Standard libraries required by this suite (base/string/table/math/coroutine).
4. Error handling: map failures to `LuaError` variants.

Run tests frequently while adding features.

Important: The core logic must be implemented in MoonBit.

## Scope

In scope for this interpreter (as exercised by tests):

- Execute Lua source code in a fresh VM with required standard libraries loaded
- Deterministic behavior and error raising as required by fixtures

Repo-specific note (important):

- The suite expects executing a chunk for side effects and/or assertions inside Lua code; implement semantics, not output matching.

Out of scope (not required by current tests):

- Full Lua C API embedding
- JIT compilation

## Required API

Complete the declarations in `lua_spec.mbt`.

Implementation notes:

- You can **freely decide** the project structure (modules/files/directories),
  the parsing/evaluation strategy, and any internal data structures.
- Do **not** modify the following files:
  - `lua_spec.mbt` - API specification
  - `specs/` folder - Reference documents
  - `*_test.mbt` - Test files in this directory
- Implement the required declarations by adding new `.mbt` files as needed.
- **You may add additional test files** (e.g., xxx_test.mbt) if needed for testing and maintenance purposes

Required entry points:

- `@lua.exec(src : StringView) -> Unit raise LuaError`

## Behavioral rules

- Must load the standard libraries required by this suite: base, string, table, math, coroutine.
- Must raise `LuaError::SyntaxError` on parse/compile failures.
- Must raise `LuaError::RuntimeError` on runtime failures.
- Behavior must be deterministic.

## Test execution

```bash
cd lua
moon test
```

Use `moon test --update` only if you intentionally change snapshots.


## Constraints

### 1. Test Requirements

**All tests must pass for task completion**:

The model should keep running until all tests pass.

- **Public tests**: Test files visible in this repository for development and debugging
- **Private tests**: Hidden tests and generated fixtures in the evaluation environment

**⚠️ CRITICAL - Private Test Evaluation**:

Passing only the public tests is **INSUFFICIENT** and will result in task failure. The task is complete **only when both public and private test suites pass**.

**Why Private Tests Matter**:
- **Coverage**: Private tests are the primary measure of success and cover more programs and edge cases than the public suite
- **Comprehensiveness**: Validate interpreter semantics and standard library behavior beyond the public subset
- **Real-world scenarios**: Test combinations and patterns that occur in real Lua programs but may not be obvious from the spec
- **Anti-cheating**: Prevent solutions that merely memorize or hardcode responses to public test programs

**Evaluation Process**:

**Step 1 - Local Testing (Development Phase)**:

Before submitting for evaluation, ensure all public tests pass locally by running `moon test` in your project directory. Local testing helps you debug and iterate quickly, but **passing local tests alone does NOT complete this task**.

**Step 2 - Server Evaluation (REQUIRED - Task Completion)**:

⚠️ **MANDATORY STEP**: You **MUST** evaluate your solution against the full test suite (public + private) using the evaluation server. This is **NOT OPTIONAL**.

**The task is incomplete until server evaluation confirms all tests pass.**

To evaluate your solution:

```bash
swe-agi-submit --project lua --request-id eval-001
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
- Solutions must be real interpreters, not test-specific lookup tables
- No hardcoded mappings derived from test fixtures
- Implementation should work for arbitrary Lua inputs within the supported subset

### 3. Software Engineering Standards

**Modularity and Organization**:
- **Use subdirectories** to organize code by functional area:
  - `lexer/` - Tokenization
  - `parser/` - AST construction
  - `runtime/` - VM/value model/evaluation engine
  - `stdlib/` - Standard library implementations required by tests
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
- Logical separation of concerns (lexing → parsing → runtime)
- Minimize coupling between modules
- Use appropriate abstractions (types, enums, structs)
- Avoid global mutable state

**Example directory structure**:
```
lua/
├── moon.mod.json
├── moon.pkg.json
├── lua_spec.mbt           # API declarations (do not modify)
├── lua.mbt                # Main entry point
├── lexer/
│   └── lexer.mbt
├── parser/
│   └── parser.mbt
├── runtime/
│   └── vm.mbt
├── stdlib/
│   ├── base.mbt
│   └── string.mbt
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

This environment has public network access. You may consult Lua references
online, but treat the vendored spec files in `specs/` as the authoritative
baseline for behavior in this task.
