# ZIP Fixture + Test Generation

This directory contains the scripts used to build the fixture corpus and
generate MoonBit tests.

## Pipeline

1. **Download fixtures** (ZIP/JAR files) from official sources:

```bash
python3 scripts/fetch_fixtures.py
```

2. **Run zipinfo** against every fixture:

```bash
python3 scripts/run_zipinfo.py
```

3. **Parse zipinfo output** into structured JSON:

```bash
python3 scripts/parse_zipinfo.py
```

4. **Generate MoonBit tests**:

```bash
python3 scripts/generate_zip_tests.py
```

Outputs:

- `fixtures/manifest.json`: fixture list + checksums
- `fixtures/zipinfo_raw/`: raw `zipinfo -l` output per fixture
- `fixtures/expected/`: structured JSON expected outputs
- `zip_valid_test.mbt` and `zip_invalid_test.mbt`: generated test files
