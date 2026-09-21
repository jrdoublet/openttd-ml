"""Helpers de parsing partages par les diagnostics sweeps vivants."""

import re


_LINE_RE = re.compile(r"\[script:\d+\] \[(\d+)\] \[(\w)\] (.*)")
_OPEX_RE = re.compile(r"^OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+)\s*(.*)$")


def parse_fields(rest):
    fields = {}
    for token in (rest or "").split():
        if "=" in token:
            key, _, value = token.partition("=")
            fields[key] = value
    return fields


def parse_opex_decisions(output):
    events = []
    for line in (output or "").splitlines():
        m = _LINE_RE.search(line)
        if not m:
            continue
        _company, _level, text = m.groups()
        m2 = _OPEX_RE.match(text.strip())
        if not m2:
            continue
        _y, _mo, _d, kind, rest = m2.groups()
        fields = {}
        for token in rest.split():
            if "=" in token:
                key, _, value = token.partition("=")
                fields[key] = value
        events.append({"kind": kind, "fields": fields})
    return events