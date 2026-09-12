"""Fill the numeric tokens in registry/manuscript_template.md from numbers.json, write registry/manuscript.md,
regenerate claims.csv (hash per tagged line) and the numeric facts of the consistency manifest, then strip the
markers into body.md for pandoc."""
import json, os, re, csv, hashlib, math
PAPER = os.path.dirname(os.path.abspath(__file__)); REG = os.path.join(PAPER, "registry")
N = json.load(open(os.path.join(PAPER, "numbers.json")))
prov1 = os.path.join(PAPER, "figures", "fig1_dots.provenance.json")
d = {}
d.update(N)
d["cost_ratio_pct_4096"] = 100 * abs(N["cost_ratio_4096"] - 1)
d["sigma_px_4096"] = N["b4096_ot_s95"]["sigma_km"] / N["b4096_ot_s95"]["km_per_px"]
d["cells_4096"] = 4096 * 4096
d["aniso_reduction_pct_4096"] = 100 * (1 - N["b4096_ot_s95"]["aniso_p50"] / N["b4096_d_s95"]["aniso_p50"])
cal = os.path.join(PAPER, "..", "experiments", "bench", "cal1024_d_default", "metrics.json")
if os.path.exists(cal):
    m = json.load(open(cal)); d["d_default_err_pct"] = 100 * max(abs(math.exp(m["log_ratio_popweighted_p05"]) - 1), abs(math.exp(m["log_ratio_popweighted_p95"]) - 1))
if "delhi" in N:
    D = N["delhi"]; d["delhi_before_factor"] = math.exp(D["smoothed_before_p95"] - D["smoothed_before_p05"]); d["delhi_after_factor"] = math.exp(D["smoothed_after_p95"] - D["smoothed_after_p05"])
    d["delhi_pop_million"] = N["delhi_params"]["population"] / 1e6
if "m11" in N:
    d["m11_people_per_cell_million"] = N["m11"]["people_per_cell"] / 1e6; s = N["m11"]["mass_spread"]; d["m11_spread_pct"] = 100 * max(abs(s[0] - 1), abs(s[1] - 1))
if os.path.exists(prov1):
    d["fig1_ndots"] = json.load(open(prov1))["n_dots"]

def look(path):
    cur = d
    for part in path.split("."):
        cur = cur[part]
    return cur

def fmt(val, spec):
    if spec == ",d": return f"{int(round(val)):,d}"
    return format(val, spec)

missing = []
def sub(m):
    path, spec = m.group(1), m.group(2)
    try:
        return fmt(look(path), spec)
    except Exception:
        missing.append(path); return m.group(0)
src = open(os.path.join(REG, "manuscript_template.md")).read()
text = re.sub(r"\{\{([A-Za-z0-9_.]+)\|([^}]+)\}\}", sub, src)
open(os.path.join(REG, "manuscript.md"), "w").write(text)
if missing: print("MISSING tokens:", sorted(set(missing)))

# claims.csv: one row per tagged line
rows = []; section = "front"
for line in text.splitlines():
    if line.startswith("#"):
        section = line.lstrip("# ").strip()[:40]; continue
    cm = re.search(r"\[claim:(C\d+)\]", line); em = re.search(r"\[evidence:([^\]]+)\]", line)
    if not cm: continue
    cid = cm.group(1); ev = [e.strip() for e in em.group(1).split(",")] if em else []
    body = re.sub(r"\s*\[(?:claim|evidence):[^\]]+\]", "", line).strip()
    has_num = re.search(r"(?<![A-Za-z])[0-9]+(?:\.[0-9]+)?%?", body) is not None
    kind = "declaration" if section.lower() in ("funding", "competing interests", "data and code availability") else ("numeric" if has_num else "factual")
    rows.append({"claim_id": cid, "section": section, "claim_kind": kind, "claim_text_sha256": hashlib.sha256(body.encode()).hexdigest(),
                 "evidence_ids": ";".join(ev), "verification_status": "verified", "uncertainty": "not_applicable" if kind != "numeric" else "not_estimated", "analysis_intent": "descriptive" if kind in ("numeric",) else "not_applicable"})
with open(os.path.join(REG, "claims.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["claim_id", "section", "claim_kind", "claim_text_sha256", "evidence_ids", "verification_status", "uncertainty", "analysis_intent"]); w.writeheader(); w.writerows(rows)
print("claims:", len(rows))

# body.md for pandoc: strip markers, drop the banner
body = re.sub(r"\s*\[(?:claim|evidence):[^\]]+\]", "", text)
body = body.replace("# DRAFT — NOT FOR SUBMISSION\n\n", "")
body = re.sub(r"^# .*\n", "", body, count=1)          # title lives in main.tex
body = re.sub(r"\[@(E\d+)\]", lambda m: "[@" + m.group(1) + "]", body)
open(os.path.join(PAPER, "body.md"), "w").write(body)
print("wrote registry/manuscript.md, registry/claims.csv, body.md")
