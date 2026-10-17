#!/usr/bin/env python3
"""Validate every YAML config in this folder against anaglyph_profile.schema.json.

Checks
------
1. JSON Schema (Draft 2020-12) validation of config/profiles/*.yaml and config/*.yaml.
2. The schema itself is a valid Draft 2020-12 schema.
3. For each profile: recomputes rowsum(M_left) + rowsum(M_right) per output channel and
   compares it with the declared `matrices.row_sum_check` (tolerance 0.0015).
4. Negative self-tests: a few deliberately broken documents must FAIL validation
   (so the schema is not vacuously permissive).

Usage:  python validate_configs.py      (needs pyyaml + jsonschema; exit code 0 = all good)
"""
from __future__ import annotations

import copy
import glob
import json
import os
import sys

import jsonschema
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(HERE, "anaglyph_profile.schema.json")


def load_yaml(path):
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def row_sums(m_left, m_right):
    return [sum(m_left[i]) + sum(m_right[i]) for i in range(3)]


def main() -> int:
    with open(SCHEMA_PATH, encoding="utf-8") as fh:
        schema = json.load(fh)
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)
    print("schema: valid Draft 2020-12 schema")

    files = sorted(glob.glob(os.path.join(HERE, "profiles", "*.yaml")) +
                   glob.glob(os.path.join(HERE, "*.yaml")))
    failures = 0
    profiles = []
    for path in files:
        doc = load_yaml(path)
        errs = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
        rel = os.path.relpath(path, HERE)
        if errs:
            failures += 1
            print(f"FAIL  {rel}")
            for e in errs[:20]:
                print(f"      at /{'/'.join(map(str, e.path))}: {e.message}")
        else:
            print(f"PASS  {rel}  (kind={doc['kind']})")
        prof = doc.get("profile") if doc.get("kind") == "anaglyph_experiment" else doc
        if prof:
            profiles.append((rel, prof))

    for rel, prof in profiles:
        m = prof["matrices"]
        rs = row_sums(m["M_left"], m["M_right"])
        declared = m.get("row_sum_check")
        ok = declared is None or all(abs(a - b) <= 0.0015 for a, b in zip(rs, declared))
        tag = "PASS" if ok else "FAIL"
        failures += 0 if ok else 1
        print(f"{tag}  row sums {rel}: computed {[round(x, 4) for x in rs]} declared {declared}")

    # negative self-tests on a copy of the first profile
    base = copy.deepcopy(load_yaml(os.path.join(HERE, "profiles", "red_cyan_channel_mask.yaml")))
    broken = []
    b1 = copy.deepcopy(base); b1["matrices"]["M_left"] = [[1, 0], [0, 0], [0, 0]]; broken.append(("2x3 matrix row", b1))
    b2 = copy.deepcopy(base); b2["filters"]["left"]["transmission"]["data_type"] = "guessed"; broken.append(("bad data_type", b2))
    b3 = copy.deepcopy(base); b3["calibration"]["status"] = "measured"; broken.append(("measured w/o numbers", b3))
    b4 = copy.deepcopy(base); b4["filters"]["left"]["eye"] = "right"; broken.append(("left filter marked right", b4))
    b5 = copy.deepcopy(base); del b5["stereo"]["off_axis"]; broken.append(("missing off_axis", b5))
    b6 = copy.deepcopy(base); b6["matrices"]["math_domain"] = "gamma"; broken.append(("bad math_domain", b6))
    for label, doc in broken:
        if validator.is_valid(doc):
            failures += 1
            print(f"FAIL  negative test accepted invalid doc: {label}")
        else:
            print(f"PASS  negative test rejected: {label}")

    print("ALL OK" if failures == 0 else f"{failures} FAILURE(S)")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
