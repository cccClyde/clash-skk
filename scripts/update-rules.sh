#!/usr/bin/env bash
set -euo pipefail

ROOT_URL="${ROOT_URL:-https://ruleset.skk.moe}"
OUT_DIR="${OUT_DIR:-.}"
BIN_PATH="${BIN_PATH:-./bin/clash-skk}"
MIHOMO_BIN="${MIHOMO_BIN:-mihomo}"

if [[ ! -x "$MIHOMO_BIN" ]] && ! command -v "$MIHOMO_BIN" >/dev/null 2>&1; then
  echo "mihomo executable not found: $MIHOMO_BIN" >&2
  exit 1
fi

links=$(python3 - "$ROOT_URL" <<'PY'
import sys
import urllib.request
from html.parser import HTMLParser

if len(sys.argv) < 2:
    raise SystemExit("missing base url")
base = sys.argv[1]
print(f"Fetching links from {base}...", file=sys.stderr)
req = urllib.request.Request(
    base,
    headers={
        "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "Accept": "text/html,application/xhtml+xml",
    },
)
html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", errors="ignore")
links = []

class Parser(HTMLParser):
    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href", "")
        if href.startswith("/Clash/") and href.endswith(".txt"):
            links.append(href)

Parser().feed(html)
for href in sorted(set(links)):
    print(href)
PY
)

while IFS= read -r path; do
  make_domain_classical_copy=0
  case "$path" in
    /Clash/domainset/*)
      rule_type="domain"
      mrs_behavior="domain"
      make_domain_classical_copy=1
      ;;
    /Clash/non_ip/*)
      rule_type="classic"
      mrs_behavior=""
      ;;
    /Clash/ip/*)
      rule_type="ipcidr"
      mrs_behavior="ipcidr"
      ;;
    *)
      continue
      ;;
  esac

  source_url="${ROOT_URL}${path}"
  yaml_path="${OUT_DIR%/}${path%.txt}.yaml"
  echo "$source_url"
  echo "$yaml_path"
  mkdir -p "$(dirname "$yaml_path")"
  "$BIN_PATH" -t "$rule_type" -u "$source_url" -o "$yaml_path"

  # MRS supports only domain and ipcidr behaviors; classical rules remain YAML-only.
  if [[ -n "$mrs_behavior" ]]; then
    mrs_path="${OUT_DIR%/}/MRS/${path#/Clash/}"
    mrs_path="${mrs_path%.txt}.mrs"
    mkdir -p "$(dirname "$mrs_path")"
    mrs_input="$yaml_path"

    # ip/ sources may also contain DOMAIN and classical IP-CIDR entries.
    # An ipcidr MRS can contain only bare, valid CIDRs.
    if [[ "$mrs_behavior" == "ipcidr" ]]; then
      mrs_input="$(mktemp)"
      if ! python3 ./scripts/make-mrs-ipcidr-yaml.py "$yaml_path" "$mrs_input"; then
        echo "Skip MRS with no valid CIDR: $yaml_path" >&2
        rm -f "$mrs_input" "$mrs_path"
        continue
      fi
    fi

    if python3 - "$mrs_input" <<'PY'
import sys
with open(sys.argv[1], encoding="utf-8") as f:
    raise SystemExit(0 if any(line.startswith("- ") for line in f) else 1)
PY
    then
      echo "$mrs_path"
      "$MIHOMO_BIN" convert-ruleset "$mrs_behavior" yaml "$mrs_input" "$mrs_path"
      test -s "$mrs_path"
    else
      echo "Skip empty ruleset: $yaml_path" >&2
      rm -f "$mrs_path"
    fi
    if [[ "$mrs_input" != "$yaml_path" ]]; then
      rm -f "$mrs_input"
    fi
  fi

  # For Shadowrocket compatibility, domainset rules need an extra classical YAML copy.
  if [[ "$make_domain_classical_copy" == "1" ]]; then
    name="$(basename "${path%.txt}")"
    classical_output_path="${OUT_DIR%/}/Clash/non_ip/${name}_classical.yaml"
    echo "$classical_output_path"
    mkdir -p "$(dirname "$classical_output_path")"
    "$BIN_PATH" -t "domain-classical" -u "$source_url" -o "$classical_output_path"
  fi
done <<< "$links"
