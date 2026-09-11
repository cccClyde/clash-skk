#!/usr/bin/env python3
"""Extract valid CIDRs from a clash-skk YAML provider for Mihomo MRS."""

import ipaddress
import sys
from pathlib import Path
from typing import Optional


def decode_yaml_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    return value


def cidr_from_rule(rule: str) -> Optional[str]:
    fields = [field.strip() for field in rule.split(",")]
    if fields[0] in {"IP-CIDR", "IP-CIDR6"} and len(fields) >= 2:
        candidate = fields[1]
    elif len(fields) == 1:
        candidate = fields[0]
    else:
        return None
    try:
        return str(ipaddress.ip_network(candidate, strict=False))
    except ValueError:
        return None


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: make-mrs-ipcidr-yaml.py <input.yaml> <output.yaml>", file=sys.stderr)
        return 2

    source = Path(sys.argv[1])
    destination = Path(sys.argv[2])
    cidrs: list[str] = []
    seen: set[str] = set()
    for line in source.read_text(encoding="utf-8").splitlines():
        if not line.startswith("- "):
            continue
        cidr = cidr_from_rule(decode_yaml_scalar(line[2:]))
        if cidr and cidr not in seen:
            cidrs.append(cidr)
            seen.add(cidr)

    destination.write_text(
        "payload:\n" + "".join(f"- '{cidr}'\n" for cidr in cidrs), encoding="utf-8"
    )
    if not cidrs:
        print(f"no valid CIDRs in {source}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
