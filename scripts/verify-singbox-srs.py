#!/usr/bin/env python3
"""Check that every SingBox/srs/*.srs decompiles back to the same rules as its source JSON."""
import ipaddress
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SING_BOX = os.environ.get("SING_BOX_BIN", "sing-box")
ROOT = Path(os.environ.get("OUT_DIR", ".")) / "SingBox"


def covered(domain, suffixes):
    """True if `domain` is already matched by one of the domain_suffix entries."""
    for s in suffixes:
        s = s.lstrip(".")
        if domain == s or domain.endswith("." + s):
            return True
    return False


def cidr_set(items):
    """Collapse CIDRs so adjacent prefixes merged by the compiler compare equal
    (e.g. 2001:b28:f23c::/48 + 2001:b28:f23d::/48 == 2001:b28:f23c::/47)."""
    nets = [ipaddress.ip_network(x, strict=False) for x in items]
    v4 = ipaddress.collapse_addresses(n for n in nets if n.version == 4)
    v6 = ipaddress.collapse_addresses(n for n in nets if n.version == 6)
    return (tuple(v4), tuple(v6))


def canon(rule):
    """Normalise sing-box listable fields: str -> [str], drop empty lists.

    `rule-set decompile` writes single-item lists as plain strings and omits empty
    fields, while upstream sources always use lists (sometimes empty)."""
    out = {}
    for k, v in rule.items():
        if isinstance(v, str):
            v = [v]
        if isinstance(v, list) and not v:
            continue
        out[k] = v
    return out


def diff(src_rules, dec_rules):
    """Compare rule-sets by match semantics.

    The srs compiler builds a succinct domain set and drops `domain` entries that a
    `domain_suffix` already covers (e.g. Sukka's watermark host under skk.moe), so
    exact equality is too strict. Everything else must match exactly.
    """
    if len(src_rules) != len(dec_rules):
        return "rule count %d != %d" % (len(src_rules), len(dec_rules))
    for i, (a, b) in enumerate(zip(src_rules, dec_rules)):
        a, b = canon(a), canon(b)
        if set(a) - {"domain"} != set(b) - {"domain"}:
            return "rule %d keys %s != %s" % (i, sorted(a), sorted(b))
        for k in a:
            if k == "domain":
                continue
            va, vb = a[k], b[k]
            if isinstance(va, list):
                if k in ("ip_cidr", "source_ip_cidr"):
                    if cidr_set(va) != cidr_set(vb):
                        return "rule %d %s covers different addresses" % (i, k)
                elif set(va) != set(vb):
                    return "rule %d %s differs (%d vs %d)" % (i, k, len(va), len(vb))
            elif va != vb:
                return "rule %d %s: %r != %r" % (i, k, va, vb)
        da, db = set(a.get("domain", [])), set(b.get("domain", []))
        if db - da:
            return "rule %d domain gained %s" % (i, sorted(db - da)[:3])
        lost = [d for d in da - db if not covered(d, a.get("domain_suffix", []))]
        if lost:
            return "rule %d domain lost %s" % (i, sorted(lost)[:3])
        if da - db and not db and "domain_suffix" not in a:
            return "rule %d domain list emptied" % i
    return None


def main() -> int:
    bad = []
    srcs = sorted((ROOT / "source").rglob("*.json"))
    for src in srcs:
        srs = (ROOT / "srs" / src.relative_to(ROOT / "source")).with_suffix(".srs")
        if not srs.exists():
            bad.append("%s: missing srs" % srs)
            continue
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "d.json"
            subprocess.run([SING_BOX, "rule-set", "decompile", "-o", str(out), str(srs)], check=True,
                           stdout=subprocess.DEVNULL)
            reason = diff(json.loads(src.read_text())["rules"], json.loads(out.read_text())["rules"])
        if reason:
            bad.append("%s: %s" % (srs, reason))
    print("checked %d rule-sets, %d mismatches" % (len(srcs), len(bad)))
    for line in bad:
        print("  " + line)
    return 1 if bad or not srcs else 0


if __name__ == "__main__":
    sys.exit(main())
