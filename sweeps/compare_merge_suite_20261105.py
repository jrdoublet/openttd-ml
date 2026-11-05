"""Compare unittest failure cases, not just aggregate counts.

Read two captured `unittest discover` logs (origin/master and merged tree).
Subtest names, test classes and errors are normalized without depending on the
absolute worktree path shown in traceback lines.  Baseline failures count as
allowed only when the same complete incident heading occurs on the merge.
"""

import argparse
from collections import Counter
import json
from pathlib import Path
import re


START = re.compile(r"^(FAIL|ERROR):\s*(.*)$")
DASHES = re.compile(r"^-{20,}\s*$")
RESULT = re.compile(r"Ran\s+(\d+)\s+tests")
SUMMARY = re.compile(r"(?:FAILED\s*\((.*?)\)|^OK\s*$)", re.MULTILINE)


def failures(log):
    lines = log.splitlines()
    cases = Counter()
    index = 0
    while index < len(lines):
        match = START.match(lines[index])
        if match is None:
            index += 1
            continue
        header = [match.group(2)]
        index += 1
        while index < len(lines) and DASHES.match(lines[index]) is None:
            header.append(lines[index])
            index += 1
        # Unittest may line-wrap a very long test class or parameter name.
        # Whitespace normalization does not collapse distinct modules/params.
        case = re.sub(r"\s+", "", "".join(header))
        cases[(match.group(1), case)] += 1
    return cases


def compare(baseline_log, merged_log):
    baseline = failures(baseline_log)
    merged = failures(merged_log)
    newly_failing = merged - baseline
    disappeared = baseline - merged

    def rows(cases):
        return [
            {"kind": kind, "test_case": case, "count": amount}
            for (kind, case), amount in sorted(cases.items())
        ]

    def total(cases):
        return sum(cases.values())

    return {
        "baseline_run_count": int(RESULT.findall(baseline_log)[-1]),
        "merged_run_count": int(RESULT.findall(merged_log)[-1]),
        "baseline_incidents": total(baseline),
        "merged_incidents": total(merged),
        "shared_incidents": total(baseline & merged),
        "new_incidents": total(newly_failing),
        "disappeared_incidents": total(disappeared),
        "new_cases": rows(newly_failing),
        "disappeared_cases": rows(disappeared),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--merged", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    def captured_log(path):
        raw = path.read_bytes()
        # Windows PowerShell 5.1 redirection and `Out-File` produce UTF-16LE.
        if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
            return raw.decode("utf-16", errors="replace")
        return raw.decode("utf-8-sig", errors="replace")

    evidence = compare(captured_log(args.baseline), captured_log(args.merged))
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")


if __name__ == "__main__":
    main()
