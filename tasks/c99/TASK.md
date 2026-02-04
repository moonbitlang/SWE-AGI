## Goal

Implement a MoonBit **C99 parser** (subset) that produces a correct AST and a
stable JSON encoding that matches this repository’s test suite. The authoritative
repo reference is vendored in:

- `c99/specs/c99.md`

## What This Task Is Really About

This is an exercise in building a **real parser** for a real programming
language. The goal is to parse C99 source text into a structured AST with type
information — not to pattern-match test strings.

A proper implementation will have:

- A **lexer** that tokenizes keywords, identifiers, literals, and punctuation
- A **parser** that builds an AST for a translation unit
- A **type/declaration pass** that tracks scopes, typedef names, and computes
  expression `ctype`/`repr` fields as required by tests
- A **serializer** that encodes the AST into the exact JSON schema used in tests

**Important mindset**: If the test suite were regenerated with different
literals or identifier names (but still within the supported grammar), your
implementation should still pass. If it wouldn’t, you haven’t built a parser —
you’ve built a lookup table.

## Approach

Build incrementally:

1. **Lexing**: identifiers, keywords, numeric/char/string literals, operators,
   punctuation, and whitespace/comments.
2. **Parsing expressions**: precedence/associativity, postfix/unary/cast.
3. **Parsing declarations**: declarators, pointers/arrays/functions, structs/enums.
4. **Parsing statements**: blocks, control flow, labels/goto, switch/case.
5. **Semantic checks + typing**: typedef disambiguation, scopes, and required
   `ctype`/`repr` computation.
6. **JSON encoding**: implement `CProgram::to_test_json()` to match snapshots.

Run tests frequently while adding features.

Important: The core logic must be implemented in MoonBit.

## Scope

In scope for this parser implementation (as exercised by tests):

- Translation unit parsing and AST construction
- Declarations/definitions and statement parsing needed by the suite
- Expression parsing with correct C precedence and associativity
- Typedef/tag name tracking sufficient to disambiguate declarations vs expressions
- Deterministic JSON encoding via `CProgram::to_test_json()`

Repo-specific note (important):

- Tests assert a **specific JSON schema** and require expression nodes to carry
  expected typing/representation fields; match that schema exactly.

Out of scope (not required by current tests):

- Preprocessor directives, macro expansion, includes, and pragmas
- Code generation or execution

## Required API

Complete the declarations in `c99_spec.mbt`.

Implementation notes:

- You can **freely decide** the project structure (modules/files/directories),
  the parsing strategy, and any internal data structures.
- Do **not** modify the following files:
  - `c99_spec.mbt` - API specification
  - `specs/` folder - Reference documents
  - `*_pub_test.mbt` - Public test files (`c99_valid_pub_test.mbt`)
  - `*_priv_test.mbt` - Private test files (`c99_valid_priv_test.mbt`)
- Implement the required declarations by adding new `.mbt` files as needed.
- **You may add additional test files** (e.g., xxx_test.mbt) if needed for testing and maintenance purposes
  - Create additional test files (e.g., `xxx_test.mbt`) to validate edge cases
  - Derive test scenarios from `specs/c99.md`
  - All added tests must remain faithful to the behaviors used by this repo

Required entry points:

- `@c99.parse(code : StringView) -> CProgram raise ParseError`
- `@c99.CProgram::to_test_json(self : CProgram) -> Json`

## Behavioral rules

- Follow the covered C99 grammar and precedence rules.
- Typedef name resolution is required to disambiguate declarations vs expressions.
- `to_test_json()` must match the explicit JSON schema used by tests exactly.
- On invalid input, raise `ParseError` (message text is not the oracle; structure is).

## Test execution

```bash
cd c99
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
- **Comprehensiveness**: Validate full C99 subset compliance, including edge cases, corner cases, and subtle semantic rules not exposed in public tests
- **Real-world scenarios**: Test combinations and patterns that occur in actual C code but may not be obvious from the spec
- **Anti-cheating**: Prevent solutions that merely memorize or hardcode responses to public test cases

**Evaluation Process**:

**Step 1 - Local Testing (Development Phase)**:

Before submitting for evaluation, ensure all public tests pass locally by running `moon test` in your project directory. Local testing helps you debug and iterate quickly, but **passing local tests alone does NOT complete this task**.

**Step 2 - Server Evaluation (REQUIRED - Task Completion)**:

⚠️ **MANDATORY STEP**: You **MUST** evaluate your solution against the full test suite (public + private) using the evaluation server. This is **NOT OPTIONAL**.

**The task is incomplete until server evaluation confirms all tests pass.**

To evaluate your solution:

```bash
swe-agi-submit --project c99 --request-id eval-001
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
- Implementation should work for arbitrary inputs within the supported grammar

### 3. Software Engineering Standards

**Modularity and Organization**:
- **Use subdirectories** to organize code by functional area:
  - `lexer/` - Tokenization and lexical analysis
  - `parser/` - Syntax parsing and AST construction
  - `semantic/` - Scope tracking and typing rules
  - `json/` - JSON encoding for test output
  - `types/` - Core AST/type definitions
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
- Logical separation of concerns (lexing → parsing → semantic analysis → output)
- Minimize coupling between modules
- Use appropriate abstractions (types, enums, structs)
- Avoid global mutable state

**Example directory structure**:
```
c99/
├── moon.mod.json
├── moon.pkg.json
├── c99_spec.mbt           # API declarations (do not modify)
├── c99.mbt                # Main entry point
├── lexer/
│   ├── token.mbt
│   └── lexer.mbt
├── parser/
│   ├── ast.mbt
│   └── parser.mbt
├── semantic/
│   ├── scope.mbt
│   └── typing.mbt
├── json/
│   └── encoder.mbt
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

This environment has public network access. You may consult C99 documentation,
discussions, and other references online, but treat the vendored spec files in
`specs/` as the authoritative baseline for behavior in this task.

You must not consult any MoonBit implementations online; the task should be completed using only your own knowledge.