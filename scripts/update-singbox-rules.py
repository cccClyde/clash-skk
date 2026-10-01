#!/usr/bin/env python3
"""Mirror SukkaW sing-box rule-sets (source JSON) and compile them to binary .srs.

Output layout (mirrors https://ruleset.skk.moe/sing-box/):
  SingBox/source/<group>/<name>.json   upstream source JSON, unchanged
  SingBox/srs/<group>/<name>.srs       `sing-box rule-set compile` output

Every upstream file is compiled: sing-box headless rules support domain,
domain_suffix, domain_keyword, domain_regex, ip_cidr and process fields, so the
.srs is lossless (unlike MRS, which only supports domain / ipcidr behaviours).
The compiler downgrades the srs version to the lowest one the rules need.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT_URL = os.environ.get("ROOT_URL", "https://ruleset.skk.moe").rstrip("/")
OUT_DIR = Path(os.environ.get("OUT_DIR", "."))
SING_BOX = os.environ.get("SING_BOX_BIN", "sing-box")
UA = {"User-Agent": "Mozilla/5.0 (compatible; clash-skk-srs/1.0)"}
GROUPS = ("domainset", "non_ip", "ip")


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def list_sources() -> list:
    html = fetch(ROOT_URL + "/").decode("utf-8", errors="ignore")
    links = sorted(set(re.findall(r'href="(/sing-box/(?:%s)/[^"/]+\.json)"' % "|".join(GROUPS), html)))
    if not links:
        raise SystemExit("no sing-box rule-set links found on %s" % ROOT_URL)
    return links


def validate(data: bytes, url: str) -> None:
    doc = json.loads(data)
    if not isinstance(doc.get("version"), int) or not isinstance(doc.get("rules"), list):
        raise ValueError("%s is not a sing-box rule-set source" % url)


def compile_srs(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix=".srs", dir=dst.parent)
    os.close(fd)
    try:
        subprocess.run([SING_BOX, "rule-set", "compile", "-o", tmp, str(src)], check=True)
        if os.path.getsize(tmp) == 0:
            raise RuntimeError("empty srs for %s" % src)
        os.replace(tmp, dst)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main() -> int:
    links = list_sources()
    print("found %d sing-box rule-sets" % len(links), file=sys.stderr)
    seen_src, seen_srs = set(), set()
    failed = []
    for path in links:
        rel = path[len("/sing-box/"):]               # e.g. non_ip/global.json
        url = ROOT_URL + path
        src = OUT_DIR / "SingBox" / "source" / rel
        srs = (OUT_DIR / "SingBox" / "srs" / rel).with_suffix(".srs")
        try:
            data = fetch(url)
            validate(data, url)
            src.parent.mkdir(parents=True, exist_ok=True)
            if not src.exists() or src.read_bytes() != data:
                src.write_bytes(data)
            compile_srs(src, srs)
            seen_src.add(src.resolve())
            seen_srs.add(srs.resolve())
            print(rel, file=sys.stderr)
        except Exception as exc:  # keep the previous good files for this entry
            failed.append("%s: %s" % (rel, exc))
            if src.exists():
                seen_src.add(src.resolve())
            if srs.exists():
                seen_srs.add(srs.resolve())

    # drop files whose upstream source disappeared
    for base, seen, pattern in ((OUT_DIR / "SingBox" / "source", seen_src, "*.json"),
                                (OUT_DIR / "SingBox" / "srs", seen_srs, "*.srs")):
        if base.exists():
            for f in base.rglob(pattern):
                if f.resolve() not in seen:
                    f.unlink()

    if failed:
        print("FAILED:\n  " + "\n  ".join(failed), file=sys.stderr)
        # fail the job only if most of the run failed (likely upstream outage)
        return 1 if len(failed) > len(links) // 2 else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
