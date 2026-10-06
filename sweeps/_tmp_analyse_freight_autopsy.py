import re
from pathlib import Path


ROOT = Path("results/rail_origin_reuse_onepass_autopsy_4x5_20261005_r9_engine")
SEEDS = (999, 802204, 983759, 230185)
EVENT_RE = re.compile(r"OPEX (\d{4}-\d+-\d+) ([A-Z0-9_]+)\s*(.*)$")


def fields(rest):
    return dict(token.split("=", 1) for token in rest.split() if "=" in token)


def events(path):
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = EVENT_RE.search(line)
        if not match:
            continue
        date, kind, rest = match.groups()
        if kind not in {"PROJECT_CHOSEN", "RAIL_ATTEMPT", "RAIL_BUILD", "AIR_BUILD",
                        "RAIL_ORIGIN_REUSE_DEFER", "RAIL_ORIGIN_REUSE_FALLBACK",
                        "RAIL_ORIGIN_REUSE_FINALIZE"}:
            continue
        f = fields(rest)
        if kind == "PROJECT_CHOSEN":
            sig = (kind, f.get("mode"), f.get("kind"), f.get("cargo"), f.get("src"), f.get("dst"))
        elif kind == "AIR_BUILD":
            sig = (kind, f.get("src"), f.get("dst"))
        elif kind in {"RAIL_ORIGIN_REUSE_DEFER", "RAIL_ORIGIN_REUSE_FALLBACK",
                      "RAIL_ORIGIN_REUSE_FINALIZE"}:
            sig = (kind, f.get("queued"), f.get("reuse_total"), f.get("admitted"))
        else:
            sig = (kind, f.get("kind"), f.get("cargo"), f.get("src"), f.get("dst"), f.get("reuse"))
        out.append((date, sig, rest))
    return out


for seed in SEEDS:
    ref = events(ROOT / f"reference_seed{seed}_r0.log")
    var = events(ROOT / f"origin_reuse_freight_onepass_seed{seed}_r0.log")
    # PROJECT_CHOSEN is the portfolio decision; compare that sequence first.
    rp = [e for e in ref if e[1][0] == "PROJECT_CHOSEN"]
    vp = [e for e in var if e[1][0] == "PROJECT_CHOSEN"]
    n = min(len(rp), len(vp))
    idx = next((i for i in range(n) if rp[i][1] != vp[i][1]), n if len(rp) != len(vp) else None)
    print(f"SEED {seed} ref_projects={len(rp)} var_projects={len(vp)} first_div={idx}")
    if idx is not None:
        lo = max(0, idx - 2)
        hi = min(max(len(rp), len(vp)), idx + 4)
        for i in range(lo, hi):
            r = rp[i] if i < len(rp) else None
            v = vp[i] if i < len(vp) else None
            print("  ", i, "REF", r)
            print("  ", i, "VAR", v)
    reuse = [e for e in var if e[1][0] in {"RAIL_ATTEMPT", "RAIL_BUILD"} and "reuse=1" in e[2]]
    deferred = [e for e in var if e[1][0] == "RAIL_ORIGIN_REUSE_DEFER"]
    queued = [e for e in var if e[1][0] == "RAIL_ORIGIN_REUSE_FALLBACK"]
    finalized = [e for e in var if e[1][0] == "RAIL_ORIGIN_REUSE_FINALIZE"]
    print("  first defer:", deferred[0] if deferred else None)
    print("  first fallback:", queued[0] if queued else None)
    print("  first finalize:", finalized[0] if finalized else None)
    print("  first reuse events:")
    for e in reuse[:8]:
        print("   ", e)
