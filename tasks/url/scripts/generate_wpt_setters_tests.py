#!/usr/bin/env python3
"""Generate MoonBit tests from WPT setters_tests.json for url package."""

import json
import sys
import urllib.request

URL = "https://raw.githubusercontent.com/web-platform-tests/wpt/master/url/resources/setters_tests.json"


def escape_moonbit_string(value):
    if value is None:
        return None
    result = []
    for c in value:
        code = ord(c)
        if c == "\\":
            result.append("\\\\")
        elif c == '"':
            result.append('\\"')
        elif c == "\n":
            result.append("\\n")
        elif c == "\r":
            result.append("\\r")
        elif c == "\t":
            result.append("\\t")
        elif code < 32 or code == 127 or code > 126:
            result.append(f"\\u{{{code:X}}}")
        else:
            result.append(c)
    return "".join(result)


FIELD_ORDER = [
    "href",
    "protocol",
    "username",
    "password",
    "host",
    "hostname",
    "port",
    "pathname",
    "search",
    "hash",
]


def setter_method(name):
    if name == "href":
        return "set_href"
    return f"set_{name}"


def getter_method(name):
    if name == "href":
        return "href"
    return name


def generate_single_test(setter, index, item):
    href = escape_moonbit_string(item["href"])
    new_value = escape_moonbit_string(item["new_value"])
    expected = item["expected"]

    lines = []
    lines.append("///|")
    lines.append(f'test "WPT setters {setter} #{index}" {{')
    lines.append(f'  let url = @url.Url::parse("{href}")')
    lines.append('  guard url is Some(url) else { fail("parse failed") }')
    lines.append(f'  url.{setter_method(setter)}("{new_value}")')

    for field in FIELD_ORDER:
        if field not in expected:
            continue
        expected_value = escape_moonbit_string(expected[field])
        lines.append(
            f'  assert_eq(url.{getter_method(field)}(), "{expected_value}")'
        )

    lines.append("}")
    return "\n".join(lines)


def main():
    print("Fetching WPT setters_tests.json...", file=sys.stderr)
    with urllib.request.urlopen(URL) as response:
        data = json.loads(response.read())

    output = []
    output.append("// Auto-generated from WPT setters_tests.json")
    output.append("// https://github.com/web-platform-tests/wpt/blob/master/url/resources/setters_tests.json")
    output.append("// Do not edit manually")
    output.append("//")
    output.append("// To regenerate: python3 scripts/generate_wpt_setters_tests.py > url_wpt_setters_test.mbt")
    output.append("")

    for setter in FIELD_ORDER:
        if setter not in data:
            continue
        tests = data[setter]
        for index, item in enumerate(tests):
            output.append(generate_single_test(setter, index, item))
            output.append("")

    print("\n".join(output))


if __name__ == "__main__":
    main()
