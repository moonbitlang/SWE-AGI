## Goal

Implement a MoonBit **INI parser** compatible with this repository’s INI dialect
as defined by the test suite. The authoritative repo reference is vendored in:

- `ini/specs/ini.md`

## What This Task Is Really About

This is an exercise in building a **real line-oriented parser**:

- Tokenize/parse section headers and key/value lines
- Apply comment and quoting rules consistently
- Produce a structured `Ini` value and a stable JSON encoding for tests

**Important mindset**: Don’t hardcode special cases for particular test strings.
If tests were regenerated with different keys/values, your parser should still
work.

## Approach

Build incrementally:

1. Line splitting (LF/CRLF) and blank/comment lines.
2. Global key/value pairs and section headers.
3. Key/value separators (`=` and `:`) and whitespace handling.
4. Quoted values and inline comment rules.
5. Multiline continuation rules (backslash continuation).
6. Implement `Ini::to_test_json()` as the test oracle.

Run tests frequently while adding features.

Important: The core logic must be implemented in MoonBit.

## Scope

In scope for this parser implementation (as exercised by tests):

- Sections and key/value pairs with the suite’s separators and whitespace rules
- Comments (`;` and `#`) including inline comment behavior for unquoted values
- Quoted values (single/double) and escapes used by tests
- Multiline values with backslash continuation
- Deterministic JSON encoding via `Ini::to_test_json()`

Repo-specific note (important):

- INI has no single universal standard; the tests and `ini_spec.mbt` define the behavior here.

Out of scope (not required by current tests):

- Supporting every INI dialect option from other ecosystems
- Type inference (all values are strings)

## Required API

Complete the declarations in `ini_spec.mbt`.

Implementation notes:

- You can **freely decide** the project structure (modules/files/directories),
  the parsing strategy, and any internal data structures.
- Do **not** modify the following files:
  - `ini_spec.mbt` - API specification
  - `specs/` folder - Reference documents
  - `*_pub_test.mbt` - Public test files (`ini_valid_pub_test.mbt`, `ini_invalid_pub_test.mbt`)
  - `*_priv_test.mbt` - Private test files (`ini_valid_priv_test.mbt`, `ini_invalid_priv_test.mbt`)
- Implement the required declarations by adding new `.mbt` files as needed.
- **You may add additional test files** (e.g., xxx_test.mbt) if needed for testing and maintenance purposes

Required entry points:

- `@ini.parse(input : StringView) -> Result[Ini, ParseError]`
- `@ini.ParseError::to_string(self) -> String`
- `@ini.Ini::to_test_json(self) -> Json`

## Behavioral rules

- Global (pre-section) keys belong to a special section `""` in JSON.
- Duplicate keys and section redefinition behaviors must match tests.
- Invalid forms in `ini_invalid_pub_test.mbt` and `ini_invalid_priv_test.mbt` must be rejected.
- `Ini::to_test_json()` must match the encoding contract in `ini_spec.mbt`.

## Test execution

```bash
cd ini
moon test
```

Use `moon test --update` only if you intentionally change snapshots.


## Constraints

### 1. Test Requirements

**All tests must pass for task completion**:

The model should keep running until all tests pass.

- **Public tests** (`*_pub_test.mbt`): ~10% of total cases, visible in this repository for development and debugging
- **Private tests** (`*_priv_test.mbt`): ~90% of total cases, **hidden** in the evaluation environment

**⚠️ CRITICAL - Private Test Evaluation**:

Passing only the public tests is **INSUFFICIENT** and will result in task failure. The task is complete **only when both public and private test suites pass**.

**Why Private Tests Matter**:
- **Coverage**: Private tests represent 90% of the total evaluation - they are the primary measure of success
- **Comprehensiveness**: Validate full INI parsing behavior for this suite’s dialect, including edge cases and corner cases not exposed in public tests
- **Real-world scenarios**: Test combinations and patterns that occur in real INI files but may not be obvious from the spec
- **Anti-cheating**: Prevent solutions that merely memorize or hardcode responses to public test cases

**Evaluation Process**:

**Step 1 - Local Testing (Development Phase)**:

Before submitting for evaluation, ensure all public tests pass locally by running `moon test` in your project directory. Local testing helps you debug and iterate quickly, but **passing local tests alone does NOT complete this task**.

**Step 2 - Server Evaluation (REQUIRED - Task Completion)**:

⚠️ **MANDATORY STEP**: You **MUST** evaluate your solution against the full test suite (public + private) using the evaluation server. This is **NOT OPTIONAL**.

**The task is incomplete until server evaluation confirms all tests pass.**

To evaluate your solution:

```bash
swe-agi-submit --project ini --request-id eval-001
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
- Solutions must be real parsers, not test-specific lookup tables
- No hardcoded mappings derived from test fixtures
- Implementation should work for arbitrary INI inputs within the supported dialect

### 3. Software Engineering Standards

**Modularity and Organization**:
- **Use subdirectories** to organize code by functional area:
  - `lexer/` - Line/token scanning helpers
  - `parser/` - Section/key/value parsing and validation
  - `json/` - JSON encoding for test output
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
- Logical separation of concerns (scanning → parsing → output)
- Minimize coupling between modules
- Use appropriate abstractions (types, enums, structs)
- Avoid global mutable state

**Example directory structure**:
```
ini/
├── moon.mod.json
├── moon.pkg.json
├── ini_spec.mbt           # API declarations (do not modify)
├── ini.mbt                # Main entry point
├── lexer/
│   └── lexer.mbt
├── parser/
│   └── parser.mbt
├── json/
│   └── encoder.mbt
└── types/
    ├── ini.mbt
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

This environment has public network access. You may consult INI dialect
references online, but treat the vendored spec files in `specs/` as the
authoritative baseline for behavior in this task.
