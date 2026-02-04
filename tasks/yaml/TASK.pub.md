## Goal

Implement a MoonBit **YAML parser** compatible with YAML 1.2.2 and this
repository’s test suite, including a large set of generated YAML test vectors.
The authoritative references are vendored in:

- `yaml/specs/1.2.2/spec.md`
- `yaml/specs/yaml.md`

## What This Task Is Really About

This is an exercise in building a **real indentation-sensitive parser** with a
well-defined data model:

- Tokenize YAML (scalars, indicators, indentation, flow punctuation, comments)
- Parse YAML into a document representation (`Yaml`)
- Implement deterministic YAML→JSON mapping (`Yaml::to_json`) used by tests
- Implement `Yaml::to_string` such that parse→to_string→parse preserves JSON

Avoid hardcoding against specific fixtures; the generated suite exists to prevent that.

## Approach

Build incrementally:

1. Parse scalars and comments.
2. Parse block mappings and sequences with indentation handling.
3. Parse flow mappings/sequences (`{}` and `[]`).
4. Implement scalar resolution to JSON types as required by tests.
5. Implement block scalars (`|` and `>`).
6. Implement anchors/aliases and required tag behaviors.
7. Implement `Yaml::to_string` that roundtrips through `Yaml::to_json`.

Run tests frequently while adding features.

## Scope

In scope for this YAML implementation (as exercised by tests):

- Scalars: null, booleans, numbers, strings (plain/single/double quoted)
- Mappings: block and flow
- Sequences: block and flow
- Comments in common positions
- Block scalars, anchors/aliases, and required tags
- Multiple documents: tests expect returning the **first** document

Repo-specific note (important):

- `Yaml::to_json` and `Yaml::to_string` define observable semantics; match test expectations exactly.

Out of scope (not required by current tests):

- Full YAML schema resolution beyond what vectors cover
- Preserving original formatting/comments in `to_string`

## Required API

Complete the declarations in `yaml_spec.mbt`.

Implementation notes:

- You can **freely decide** the project structure (modules/files/directories),
  the parsing strategy, and any internal data structures.
- Do **not** modify the following files:
  - `yaml_spec.mbt` - API specification
  - `specs/` folder - Reference documents and vectors
  - `*_pub_test.mbt` - Public test files (`yaml_valid_pub_test.mbt`, `yaml_invalid_pub_test.mbt`, `yaml_generated_pub_test.mbt`)
  - `*_priv_test.mbt` - Private test files (intended for private testing, but available here in a full-public test setting)
- Implement the required declarations by adding new `.mbt` files as needed.
- **You may add additional test files** (e.g., xxx_test.mbt) if needed for testing and maintenance purposes

Required entry points:

- `@yaml.parse(input : String) -> Result[Yaml, ParseError]`
- `@yaml.ParseError::to_string(self) -> String`
- `@yaml.Yaml::to_json(yaml : Yaml) -> Json`
- `@yaml.Yaml::to_string(yaml : Yaml) -> String`

## Behavioral rules

- Duplicate mapping keys must be rejected where tests require it.
- `Yaml::to_json` defines observable semantics for many inputs; match test expectations exactly.
- `Yaml::to_string` must emit YAML that, when parsed again, yields the same JSON value.

## Test execution

```bash
cd yaml
moon test
```

Use `moon test --update` only if you intentionally change snapshots.

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

- Solutions must be real parsers, not test-specific lookup tables
- No hardcoded mappings derived from test fixtures
- Implementation should work for arbitrary YAML inputs within the supported subset

### 3. Software Engineering Standards

**Modularity and Organization**:

- **Use subdirectories** to organize code by functional area:
  - `lexer/` - Tokenization and indentation tracking
  - `parser/` - Syntax parsing and AST construction
  - `resolve/` - YAML-to-JSON mapping and scalar resolution
  - `print/` - `to_string` implementation
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

- Logical separation of concerns (lexing → parsing → resolution → printing)
- Minimize coupling between modules
- Use appropriate abstractions (types, enums, structs)
- Avoid global mutable state

**Example directory structure**:

```
yaml/
├── moon.mod.json
├── moon.pkg.json
├── yaml_spec.mbt          # API declarations (do not modify)
├── yaml.mbt               # Main entry point
├── lexer/
│   └── lexer.mbt
├── parser/
│   └── parser.mbt
├── resolve/
│   └── to_json.mbt
├── print/
│   └── to_string.mbt
└── types/
    ├── yaml.mbt
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

This environment has public network access. You may consult YAML references
online, but treat the vendored spec files in `specs/` as the authoritative
baseline for behavior in this task.
