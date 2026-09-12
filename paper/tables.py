"""Table 1 and the numbers used in the text, straight from experiments/bench/*/metrics.json.
Writes paper/table1.tex, paper/numbers.json and refreshes the numeric facts in the registry."""
import json, os, sys, hashlib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCH = os.path.join(ROOT, "experiments", "bench")
PAPER = os.path.join(ROOT, "paper")

def load(tag):
    d = os.path.join(BENCH, tag)
    return json.load(open(os.path.join(d, "params.json"))), json.load(open(os.path.join(d, "metrics.json")))

rows = [("b1024_ot_s95", "OT", 1024), ("b1024_d_s95", "diffusion", 1024), ("b2048_ot_s95", "OT", 2048), ("b2048_d_s95", "diffusion", 2048), ("b4096_ot_s95", "OT", 4096), ("b4096_d_s95", "diffusion", 4096)]
numbers = {}
lines = []
for tag, meth, w in rows:
    if not os.path.exists(os.path.join(BENCH, tag, "metrics.json")):
        print("missing", tag); continue
    p, m = load(tag)
    e05, e95 = 100 * (__import__("math").exp(m["log_ratio_popweighted_p05"]) - 1), 100 * (__import__("math").exp(m["log_ratio_popweighted_p95"]) - 1)
    cost = m["transport_cost_popweighted_mean_sq_px"] / p["W"] ** 2
    rec = {"width": w, "method": meth, "err_p05_pct": e05, "err_p95_pct": e95, "aniso_p50": m["anisotropy_popweighted_p50"], "aniso_p95": m["anisotropy_popweighted_p95"],
           "twist_p50": m["twist_popweighted_p50_deg"], "twist_p95": m["twist_popweighted_p95_deg"], "cost_frame2": cost, "disp_popmean_frame": m["displacement_popweighted_mean_px"] / p["W"],
           "shape": m["shape_error_popweighted"], "folds": m["folds"], "seconds": m["seconds"], "sigma_km": p["sigma_km"], "km_per_px": m["km_per_px_equator"]}
    numbers[tag] = rec
    lines.append(f"{w} & {meth} & {e05:+.1f} / {e95:+.1f} & {rec['aniso_p50']:.2f} / {rec['aniso_p95']:.1f} & {rec['twist_p50']:.1f} / {rec['twist_p95']:.1f} & {1000*cost:.2f} & {rec['shape']:.3f} & {rec['seconds']:.0f} \\\\")
# relative cost OT vs diffusion at each width
for w in (1024, 2048, 4096):
    a, b = numbers.get(f"b{w}_ot_s95"), numbers.get(f"b{w}_d_s95")
    if a and b: numbers[f"cost_ratio_{w}"] = a["cost_frame2"] / b["cost_frame2"]
for tag in ("cal1024_otdirect", "cal1024_otcont", "cal2048_otdirect", "cal2048_otcont"):
    f = os.path.join(BENCH, tag, "metrics.json")
    if os.path.exists(f):
        p, m = load(tag)
        numbers[tag] = {"residual": m["stages"][-1]["residual"], "err_p05_pct": 100 * (__import__("math").exp(m["log_ratio_popweighted_p05"]) - 1), "err_p95_pct": 100 * (__import__("math").exp(m["log_ratio_popweighted_p95"]) - 1), "seconds": m["seconds"], "folds": m["folds"]}
hero = os.path.join(BENCH, "b4096_ot_hero", "metrics.json")
if os.path.exists(hero):
    p, m = load("b4096_ot_hero")
    numbers["hero"] = {"err_p05_pct": 100 * (__import__("math").exp(m["log_ratio_popweighted_p05"]) - 1), "err_p95_pct": 100 * (__import__("math").exp(m["log_ratio_popweighted_p95"]) - 1),
                       "aniso_p50": m["anisotropy_popweighted_p50"], "twist_p50": m["twist_popweighted_p50_deg"], "folds": m["folds"], "seconds": m["seconds"], "residual": m.get("stages", [{}])[-1].get("residual"), "shape": m["shape_error_popweighted"]}
nested = os.path.join(ROOT, "experiments", "nested", "delhi", "metrics.json")
if os.path.exists(nested):
    numbers["delhi"] = json.load(open(nested)); numbers["delhi_params"] = json.load(open(os.path.join(ROOT, "experiments", "nested", "delhi", "params.json")))
m11 = os.path.join(ROOT, "experiments", "M11_power_8192_2048", "metrics.json")
if os.path.exists(m11):
    numbers["m11"] = json.load(open(m11))
tex = ["\\small\\resizebox{\\textwidth}{!}{\\begin{tabular}{rlccccrr}", "\\toprule",
       "grid & method & error p05 / p95 (\\%) & anisotropy p50 / p95 & rotation p50 / p95 (deg) & cost ($10^{-3}$) & shape & time (s) \\\\", "\\midrule"] + lines + ["\\bottomrule", "\\end{tabular}}"]
open(os.path.join(PAPER, "table1.tex"), "w").write("\n".join(tex) + "\n")
json.dump(numbers, open(os.path.join(PAPER, "numbers.json"), "w"), indent=1)
print(json.dumps(numbers, indent=1)[:4000])
