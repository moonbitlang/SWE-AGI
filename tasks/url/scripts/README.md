# URL Spec Test Scripts

## generate_wpt_tests.py

Generates MoonBit test cases from the official WHATWG WPT (Web Platform Tests) URL test data.

### Usage

```bash
python3 scripts/generate_wpt_tests.py > url_wpt_test.mbt
```

### Data Source

Tests are generated from the official WPT URL test data:
https://raw.githubusercontent.com/web-platform-tests/wpt/master/url/resources/urltestdata.json

### Output

The script generates:
- A `WptTestVector` struct definition
- Test blocks grouped by section comments from the WPT data
- Approximately 3,700+ test cases covering:
  - Basic URL parsing
  - Relative URL resolution
  - IPv4 and IPv6 addresses
  - Special schemes (http, https, ftp, file, ws, wss)
  - IDNA/Punycode domains
  - Percent encoding
  - Edge cases and error conditions

### Test Structure

Each generated test block follows this pattern:

```moonbit
test "WPT: Section Name" {
  let test_cases : Array[WptTestVector] = [
    { input: "...", base: Some("..."), expected: Some("...") },
    // ...
  ]
  for test_case in test_cases {
    // Parse and validate
  }
}
```

## generate_wpt_setters_tests.py

Generates MoonBit test cases from the WPT URL setters test data.

### Usage

```bash
python3 scripts/generate_wpt_setters_tests.py > url_wpt_setters_test.mbt
```

### Data Source

Tests are generated from:
https://github.com/web-platform-tests/wpt/blob/master/url/resources/setters_tests.json
