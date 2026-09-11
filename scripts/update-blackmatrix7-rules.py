#!/usr/bin/env python3
"""Mirror selected blackmatrix7 Clash rules and build supported MRS subsets."""

import ipaddress
import os
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

SOURCES = {
    "WeChat": "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/WeChat/WeChat.yaml",
    "YouTube": "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/YouTube/YouTube.yaml",
}


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "clash-skk-mrs/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def payload_rules(text: str) -> List[str]:
    rules = []
    in_payload = False
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped == "payload:":
            in_payload = True
            continue
        if not in_payload:
            continue
        if stripped.startswith("- "):
            rules.append(stripped[2:].strip())
    return rules


def classify(rules: Iterable[str]) -> Tuple[List[str], List[str], List[str]]:
    domains: List[str] = []
    cidrs: List[str] = []
    unsupported: List[str] = []
    domain_seen = set()
    cidr_seen = set()

    for rule in rules:
        kind, separator, value = rule.partition(",")
        if not separator:
            unsupported.append(rule)
            continue
        if kind == "DOMAIN":
            converted = value
            if converted not in domain_seen:
                domains.append(converted)
                domain_seen.add(converted)
            continue
        if kind == "DOMAIN-SUFFIX":
            converted = "+." + value
            if converted not in domain_seen:
                domains.append(converted)
                domain_seen.add(converted)
            continue
        if kind in {"IP-CIDR", "IP-CIDR6"}:
            try:
                converted = str(ipaddress.ip_network(value, strict=False))
            except ValueError:
                unsupported.append(rule)
                continue
            if converted not in cidr_seen:
                cidrs.append(converted)
                cidr_seen.add(converted)
            continue
        unsupported.append(rule)
    return domains, cidrs, unsupported


def provider_yaml(items: Iterable[str]) -> str:
    return "payload:\n" + "".join("- '{}'\n".format(item.replace("'", "''")) for item in items)


def convert(mihomo: str, behavior: str, items: List[str], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not items:
        destination.unlink(missing_ok=True)
        return
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "source.yaml"
        source.write_text(provider_yaml(items), encoding="utf-8")
        subprocess.run([mihomo, "convert-ruleset", behavior, "yaml", str(source), str(destination)], check=True)
    if destination.stat().st_size == 0:
        raise RuntimeError("Mihomo produced an empty MRS: {}".format(destination))


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    mihomo = os.environ.get("MIHOMO_BIN", "mihomo")
    mirror_dir = root / "Clash" / "blackmatrix7"
    mrs_dir = root / "MRS" / "blackmatrix7"
    reports: Dict[str, Tuple[int, int, List[str]]] = {}

    for name, url in SOURCES.items():
        print("Fetching {}".format(url), file=sys.stderr)
        text = fetch(url)
        mirror_dir.mkdir(parents=True, exist_ok=True)
        (mirror_dir / "{}.yaml".format(name)).write_text(text, encoding="utf-8")
        domains, cidrs, unsupported = classify(payload_rules(text))
        convert(mihomo, "domain", domains, mrs_dir / "{}-domain.mrs".format(name))
        convert(mihomo, "ipcidr", cidrs, mrs_dir / "{}-ip.mrs".format(name))
        reports[name] = (len(domains), len(cidrs), unsupported)
        print("{}: domain={} ipcidr={} unsupported={}".format(name, len(domains), len(cidrs), len(unsupported)))

    lines = [
        "# blackmatrix7 MRS subsets",
        "",
        "Sources are mirrored under `Clash/blackmatrix7/`. MRS supports only domain and ipcidr behaviors, so unsupported classical entries remain available in those original YAML files.",
        "",
    ]
    for name, (domains, cidrs, unsupported) in reports.items():
        lines.append("## {}".format(name))
        lines.append("")
        lines.append("- domain MRS entries: {}".format(domains))
        lines.append("- ipcidr MRS entries: {}".format(cidrs))
        if unsupported:
            lines.append("- retained only in YAML: {}".format(", ".join(unsupported)))
        else:
            lines.append("- retained only in YAML: none")
        lines.append("")
    mrs_dir.mkdir(parents=True, exist_ok=True)
    (mrs_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
