## Goal

Implement a MoonBit **Pug template engine** that can parse Pug templates, render
HTML, and pass this repository’s test suite (including JS interpolation cases).
The authoritative repo reference is vendored in:

- `pug/specs/pug.md`

## What This Task Is Really About

This is an exercise in building a **real template engine**:

- Lexing/parsing indentation-sensitive Pug syntax into an AST (`Document`)
- Evaluating interpolation and expressions required by tests
- Rendering deterministic HTML output

Avoid hardcoding: fixtures include many templates and edge cases.

## Approach

Build incrementally:

1. Lexer/parser for tags, attributes, text, blocks, and indentation.
2. AST model and JSON encoding for tests (`Document::to_test_json`).
3. Rendering pipeline for deterministic HTML output.
4. Includes/extends support via `TemplateRegistry` where required.
5. JavaScript expression evaluation for interpolation as required by tests.

Run tests frequently while adding features.

## Scope

In scope for this suite:

- Parsing Pug templates into `Document`
- Rendering to HTML via `render*` APIs in `pug_spec.mbt`
- Locals/registry plumbing used by tests
- Deterministic outputs and JSON inspection helpers

Repo-specific note (important):

- Tests define observable behavior via rendered output strings and/or JSON inspection; match them exactly.

Out of scope (not required by current tests):

- Full Pug feature completeness beyond what the corpus covers

## Required API

Complete the declarations in `pug_spec.mbt`.

Implementation notes:

- You can **freely decide** the project structure (modules/files/directories),
  the parsing/rendering strategy, and any internal data structures.
- Do **not** modify the following files:
  - `pug_spec.mbt` - API specification
  - `specs/` folder - Reference documents
  - `*_test.mbt` - Test files in this directory (including generated fixtures)
- Implement the required declarations by adding new `.mbt` files as needed.
- **You may add additional test files** (e.g., xxx_test.mbt) if needed for testing and maintenance purposes

Required entry points:

- `@pug.parse(input : String) -> Document`
- `@pug.parse_with_registry(input : String, registry : TemplateRegistry) -> Document`
- `@pug.Document::to_test_json(self : Document) -> Json`
- `@pug.render(input : String) -> String`
- `@pug.render_pretty(input : String) -> String`
- `@pug.render_with_locals(input : String, locals : Locals) -> String`
- `@pug.render_with_registry(input : String, registry : TemplateRegistry, locals? : Locals) -> String`
- `@pug.compile(input : String) -> CompiledTemplate`
- `@pug.CompiledTemplate::render(self : CompiledTemplate, locals : Locals) -> String`
- `@pug.eval_js_expression(expr : String, locals : Locals) -> String`

## Behavioral rules

- Parsing must be indentation-sensitive and deterministic.
- Rendering output must match expected HTML strings exactly.
- Includes/extends resolution must follow the registry-based behavior required by tests.
- Interpolation JS evaluation must match the suite’s expectations.

## Test execution

```bash
cd pug
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

- Solutions must be real parsers/renderers, not test-specific lookup tables
- No hardcoded mappings derived from test fixtures
- Implementation should work for arbitrary templates within the supported subset

### 3. Software Engineering Standards

**Modularity and Organization**:

- **Use subdirectories** to organize code by functional area:
  - `lexer/` - Tokenization and indentation handling
  - `parser/` - AST construction
  - `render/` - HTML rendering pipeline
  - `js/` - JS interpolation evaluator (as required by tests)
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

- Logical separation of concerns (lexing → parsing → rendering)
- Minimize coupling between modules
- Use appropriate abstractions (types, enums, structs)
- Avoid global mutable state

**Example directory structure**:

```
pug/
├── moon.mod.json
├── moon.pkg.json
├── pug_spec.mbt           # API declarations (do not modify)
├── pug.mbt                # Main entry point
├── lexer/
│   └── lexer.mbt
├── parser/
│   └── parser.mbt
├── render/
│   └── render.mbt
├── js/
│   └── eval.mbt
└── types/
    ├── ast.mbt
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

This environment has public network access. You may consult Pug references
online, but treat the vendored spec files in `specs/` as the authoritative
baseline for behavior in this task.
