## Goal

Implement a MoonBit **WHATWG URL parser** compatible with the WHATWG URL
Standard and this repository’s WPT-based test suite (including setter
semantics). The authoritative references are vendored in:

- `url/specs/url.md`
- `url/specs/whatwg/`
- `url/specs/wpt/`

## What This Task Is Really About

This is an exercise in implementing the **WHATWG URL parsing algorithm** (a
state machine with many special cases), not an RFC 3986 URI splitter.

You must implement:

- canonical parsing + serialization
- host parsing (domain/IPv4/IPv6/opaque)
- relative resolution against a base URL
- the WHATWG-defined setter behaviors (WPT “setters” tests)

Avoid hardcoding WPT vectors: implement the algorithm.

## Approach

Build incrementally:

1. URL record model (scheme, credentials, host, port, path, query, fragment).
2. Parser state machine for common special schemes and basic hosts.
3. Canonical serialization and basic getters.
4. Relative URL parsing with base URL.
5. Full host parsing and `file:` handling as required by tests.
6. Setters (`set_*`) matching the standard and WPT fixtures.
7. Validation error collection when requested.

Run tests frequently while adding features.

Important: The core logic must be implemented in MoonBit.

## Scope

In scope for this suite (as required by `url_spec.mbt` and tests):

- `Url::parse(input, base?, validation_errors?) -> Url?`
- Serialization and getters: `to_string`, `href`, `protocol`, `username`,
  `password`, `host`, `hostname`, `port`, `pathname`, `search`, `hash`, `origin`
- Setters: `set_href`, `set_protocol`, `set_username`, `set_password`,
  `set_host`, `set_hostname`, `set_port`, `set_pathname`, `set_search`, `set_hash`

Repo-specific note (important):

- WPT fixtures are the canonical expected results; match them exactly.

Out of scope (not required by current tests):

- Networking, DNS, or fetch behavior

## Required API

Complete the declarations in `url_spec.mbt`.

Implementation notes:

- You can **freely decide** the project structure (modules/files/directories),
  the parsing strategy, and any internal data structures.
- Do **not** modify the following files:
  - `url_spec.mbt` - API specification
  - `specs/` folder - Reference documents and WPT fixtures
  - `*_pub_test.mbt` - Public test files (`url_valid_pub_test.mbt`, `url_invalid_pub_test.mbt`, `url_wpt_pub_test.mbt`, `url_wpt_setters_pub_test.mbt`)
  - `*_priv_test.mbt` - Private test files (`url_valid_priv_test.mbt`, `url_wpt_priv_test.mbt`, `url_wpt_setters_priv_test.mbt`)
- Implement the required declarations by adding new `.mbt` files as needed.
- **You may add additional test files** (e.g., xxx_test.mbt) if needed for testing and maintenance purposes

Required entry points:

- All `declare` declarations in `url_spec.mbt` (parsing, getters, serialization, setters, and validation error collection)

## Behavioral rules

- Follow the WHATWG algorithm; WPT fixtures are the canonical expected results.
- Serialization must be canonical and deterministic.
- Setters must match WPT setter semantics.
- When `validation_errors` is provided, collect non-fatal validation issues as required by fixtures.

## Test execution

```bash
cd url
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
- **Comprehensiveness**: Validate full WHATWG URL parsing/serialization/setter behavior, including edge cases, corner cases, and subtle algorithmic rules not exposed in public tests
- **Real-world scenarios**: Test combinations and patterns that occur in real web URLs but may not be obvious from the standard
- **Anti-cheating**: Prevent solutions that merely memorize or hardcode responses to public test cases

**Evaluation Process**:

**Step 1 - Local Testing (Development Phase)**:

Before submitting for evaluation, ensure all public tests pass locally by running `moon test` in your project directory. Local testing helps you debug and iterate quickly, but **passing local tests alone does NOT complete this task**.

**Step 2 - Server Evaluation (REQUIRED - Task Completion)**:

⚠️ **MANDATORY STEP**: You **MUST** evaluate your solution against the full test suite (public + private) using the evaluation server. This is **NOT OPTIONAL**.

**The task is incomplete until server evaluation confirms all tests pass.**

To evaluate your solution:

```bash
swe-agi-submit --project url --request-id eval-001
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
- Solutions must be real algorithm implementations, not test-specific lookup tables
- No hardcoded mappings derived from WPT fixtures
- Implementation should work for arbitrary URLs within the supported subset

### 3. Software Engineering Standards

**Modularity and Organization**:
- **Use subdirectories** to organize code by functional area:
  - `model/` - URL record model
  - `parser/` - Parser state machine
  - `host/` - Host parsing and normalization
  - `serialize/` - Canonical serialization
  - `setters/` - Setter semantics
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
- Logical separation of concerns (model → parsing → serialization → setters)
- Minimize coupling between modules
- Use appropriate abstractions (types, enums, structs)
- Avoid global mutable state

**Example directory structure**:
```
url/
├── moon.mod.json
├── moon.pkg.json
├── url_spec.mbt           # API declarations (do not modify)
├── url.mbt                # Main entry point
├── model/
│   └── url.mbt
├── parser/
│   └── parser.mbt
├── host/
│   └── host.mbt
├── serialize/
│   └── serialize.mbt
├── setters/
│   └── setters.mbt
└── types/
    ├── error.mbt
    └── validation.mbt
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

This environment has public network access. You may consult the WHATWG URL
Standard online, but treat the vendored spec files in `specs/` as the
authoritative baseline for behavior in this task.
