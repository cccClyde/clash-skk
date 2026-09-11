#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).parents[1] / "update-blackmatrix7-rules.py"
spec = importlib.util.spec_from_file_location("blackmatrix7", SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load {}".format(SCRIPT))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Blackmatrix7ConversionTests(unittest.TestCase):
    def test_classify_splits_supported_and_classical_rules(self):
        domains, cidrs, unsupported = module.classify(
            [
                "DOMAIN,wechat.com",
                "DOMAIN-SUFFIX,youtube.com",
                "IP-CIDR,216.73.80.0/20",
                "IP-CIDR6,2620:120:e000::/40",
                "DOMAIN-KEYWORD,youtube",
                "IP-ASN,132203",
            ]
        )
        self.assertEqual(domains, ["wechat.com", "+.youtube.com"])
        self.assertEqual(cidrs, ["216.73.80.0/20", "2620:120:e000::/40"])
        self.assertEqual(unsupported, ["DOMAIN-KEYWORD,youtube", "IP-ASN,132203"])

    def test_provider_yaml_quotes_payload(self):
        self.assertEqual(module.provider_yaml(["+.example.com"]), "payload:\n- '+.example.com'\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
