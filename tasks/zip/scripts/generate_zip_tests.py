#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_INDEX = ROOT / "fixtures" / "expected" / "index.json"


def main() -> int:
  if not EXPECTED_INDEX.exists():
    raise SystemExit("Missing fixtures/expected/index.json; run parse_zipinfo.py first.")
  expected_index = json.loads(EXPECTED_INDEX.read_text(encoding="utf-8"))
  entries = expected_index.get("entries", [])
  valid_entries: list[dict] = []
  invalid_entries: list[dict] = []
  for item in entries:
    expected_path = ROOT / item["expected"]
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    if expected.get("invalid", False):
      invalid_entries.append(item)
    else:
      valid_entries.append(item)

  helper_block = [
    "///|",
    "async fn load_expected_json(path : String) -> Json raise {",
    "  let data = @fs.read_file(path)",
    "  @json.parse(data.text())",
    "}",
    "",
    "///|",
    "async fn parse_seekable_fixture(path : String) -> ZipReport raise {",
    "  let file = @fs.open(path, mode=@fs.Mode::ReadOnly)",
    "  defer file.close()",
    "  parse_file(file, name=path)",
    "}",
    "",
    "///|",
    "async fn parse_stream_fixture(path : String) -> ZipReport raise {",
    "  @async.with_task_group(fn(group) {",
    "    let (reader, writer) = @io.pipe()",
    "    defer reader.close()",
    "    group.spawn_bg(fn() {",
    "      defer writer.close()",
    "      let file = @fs.open(path, mode=@fs.Mode::ReadOnly)",
    "      defer file.close()",
    "      writer.write_reader(file)",
    "    })",
    "    parse_stream(reader, name=path)",
    "  })",
    "}",
    "",
  ]

  def emit_tests(path: Path, label: str, items: list[dict], include_helpers: bool) -> None:
    lines: list[str] = []
    if include_helpers:
      lines.extend(helper_block)
    for idx, item in enumerate(items):
      fixture = item["fixture"]
      expected = item["expected"]
      test_name = f"zip {label} {idx:04d} {Path(fixture).name}"
      lines.append("///|")
      lines.append(f"async test {json.dumps(test_name)} {{")
      lines.append(f"  let expected = load_expected_json({json.dumps(expected)})")
      lines.append(f"  let report_seek = parse_seekable_fixture({json.dumps(fixture)})")
      lines.append("  json_inspect(report_seek.to_json(), content=expected)")
      lines.append(f"  let report_stream = parse_stream_fixture({json.dumps(fixture)})")
      lines.append("  json_inspect(report_stream.to_json(), content=expected)")
      lines.append("}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {path} with {len(items)} tests.")

  emit_tests(ROOT / "zip_valid_test.mbt", "valid", valid_entries, True)
  emit_tests(ROOT / "zip_invalid_test.mbt", "invalid", invalid_entries, False)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
