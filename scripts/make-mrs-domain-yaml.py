#!/usr/bin/env python3
"""Turn a clash-skk classical YAML provider into a Mihomo domain-behavior YAML for MRS.

Only lossless conversions are made: the source must consist solely of DOMAIN and
DOMAIN-SUFFIX rules. Any other rule type (DOMAIN-KEYWORD, DOMAIN-WILDCARD,
PROCESS-NAME, IP-CIDR, ...) cannot be expressed in a domain MRS, so the file is
skipped (exit 1) instead of silently dropping those rules.
"""

import sys
from pathlib import Path


def decode_yaml_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    return value


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: make-mrs-domain-yaml.py <input.yaml> <output.yaml>", file=sys.stderr)
        return 2

    source = Path(sys.argv[1])
    destination = Path(sys.argv[2])
    entries: list[str] = []
    seen: set[str] = set()
    for line in source.read_text(encoding="utf-8").splitlines():
        if not line.startswith("- "):
            continue
        fields = [f.strip() for f in decode_yaml_scalar(line[2:]).split(",")]
        if len(fields) < 2:
            print(f"skip {source}: unexpected rule {line[2:]!r}", file=sys.stderr)
            return 1
        kind, value = fields[0], fields[1].lower()
        if kind == "DOMAIN":
            entry = value
        elif kind == "DOMAIN-SUFFIX":
            entry = "+." + value
        else:
            print(f"skip {source}: contains {kind}, not expressible as domain MRS", file=sys.stderr)
            return 1
        if entry not in seen:
            entries.append(entry)
            seen.add(entry)

    if not entries:
        print(f"skip {source}: no rules", file=sys.stderr)
        return 1
    destination.write_text("payload:\n" + "".join(f"- '{e}'\n" for e in entries), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
