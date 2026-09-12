"""Build source_manifest.json, consistency_manifest.json, authorship.json and reporting_coverage.json for
the paper from refs.bib, numbers.json and the repository state. Verification entries record who opened
what and when; the accountable author must re-verify before submission (manuscript_manifest.json)."""
import json, os, re, subprocess, datetime
REG = os.path.dirname(os.path.abspath(__file__)); PAPER = os.path.dirname(REG); ROOT = os.path.dirname(PAPER)
TODAY = "2026-09-12"
VERIFIER = "Claude Fable 5.1 (assistant): DOI or arXiv record opened; paper text opened where quoted. Author re-verification pending"
commit = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()

bib = open(os.path.join(PAPER, "refs.bib")).read()
def field(key, name):
    m = re.search(r"@\w+\{" + key + r",(.*?)\n\}", bib, re.S) or re.search(r"@\w+\{" + key + r",(.*?)\}\s*\n\n", bib, re.S)
    block = m.group(1) if m else ""
    f = re.search(name + r"\s*=\s*\{(.*?)\}", block, re.S | re.I)
    return f.group(1).replace("\n", " ").strip() if f else ""

lit = [  # evidence_id, bib key, source_type, locator (what supports the claims)
 ("E001", "gastner2004", "journal_article", "abstract and method section: diffusion process, velocity field; no stated objective"),
 ("E002", "gastner2018", "journal_article", "abstract: 'a flow-based algorithm whose equations of motion are numerically easier to solve'; eq. 5"),
 ("E003", "brenier1991", "journal_article", "main theorem: polar factorisation, gradient of a convex function, uniqueness"),
 ("E004", "caffarelli1992", "journal_article", "regularity of maps with convex potential for densities bounded away from zero and infinity"),
 ("E005", "villani2009", "book", "chapters on Brenier's theorem and Monge-Ampere"),
 ("E006", "benamou2010", "journal_article", "method 1: Laplacian fixed point Delta u = sqrt(|D^2 u|^2 + 2f)"),
 ("E007", "loeper2005", "journal_article", "Newton method for periodic Monge-Ampere"),
 ("E008", "saumier2015", "journal_article", "damped Newton with FFT Poisson solves for periodic L2 OT (arXiv 1009.6039 abstract)"),
 ("E009", "jacobs2020", "journal_article", "abstract: grids as large as 4096 x 4096 in a matter of minutes; Table 1: 4096 x 4096, 56.46 s, single 1.6 GHz core (arXiv 1905.12154v2)"),
 ("E010", "budd2009", "journal_article", "parabolic Monge-Ampere for moving meshes"),
 ("E011", "budd2015", "journal_article", "geometry of OT-generated r-adaptive meshes"),
 ("E012", "weller2016", "journal_article", "sphere: OT meshes do not tangle (arXiv 1512.02935)"),
 ("E013", "mcrae2018", "journal_article", "map closest to the identity, gradient of a scalar potential, immune to tangling (arXiv 1612.08077)"),
 ("E014", "zhao2013", "journal_article", "area-preserving surface flattening by optimal mass transport"),
 ("E015", "hennig2013", "book", "gridded population cartograms by diffusion; pale ocean and gaps between continents as the legibility device (ch. 4, pp. 111-147)"),
 ("E016", "nusrat2016", "journal_article", "survey of cartogram methods and metrics; no rotation metric"),
 ("E017", "alam2015", "journal_article", "quantitative cartogram measures: statistical, topology, orientation/shape, complexity"),
 ("E018", "dougenik1985", "journal_article", "rubber-sheet algorithm"),
 ("E019", "tobler2004", "journal_article", "history of computer cartograms"),
 ("E020", "choi2018", "journal_article", "density-equalising maps by diffusion for surfaces"),
 ("E021", "sargent2024", "preprint", "abstract: numerically optimised meshes minimising cartographic error and distortion; sphere variant"),
 ("E022", "molchanov2026", "preprint", "abstract: integral-image deformation, GPU, time-varying cartograms"),
 ("E023", "miaji2025", "preprint", "abstract: topology-preserving line densification with a flow-based generator"),
 ("E024", "carroll2008", "chapter", "nested multi-scale cartograms driven by user focus"),
 ("E025", "cohenaddad2018", "conference_paper", "balanced centroidal power diagrams with equal-population districts"),
 ("E026", "merigot2011", "journal_article", "semi-discrete optimal transport, Laguerre cells, multiscale Newton"),
 ("E027", "pysdot", "software", "semi-discrete OT library used for the power diagram"),
 ("E028", "ghspop2023", "dataset", "GHS-POP R2023A, epoch 2025, 30 arcsec and 3 arcsec tiles; census counts disaggregated onto built-up area"),
 ("E029", "naturalearth", "dataset", "1:50m coastline and admin-0 countries (POP_EST field), 1:110m coastline"),
 ("E030", "benamoubrenier2000", "journal_article", "fluid formulation of optimal transport"),
 ("E031", "sulman2011", "journal_article", "parabolic Monge-Ampere solver"),
 ("E032", "duncan2020", "preprint", "interactive contiguous area cartograms, task-based evaluation"),
 ("E033", "hennig2009", "chapter", "The Human Shape of the Planet: gridded world population cartogram chapter"),
]
own = [
 ("E101", "Benchmark records: experiments/bench/*/{params,metrics}.json in the repository", "dataset", f"commit {commit}; produced by src/bench_methods.py on 2026-09-12"),
 ("E102", "Local refinement record: experiments/nested/delhi/{params,metrics}.json", "dataset", f"commit {commit}; produced by src/nested_solve.py on 2026-09-12"),
 ("E103", "Semi-discrete record: experiments/M11_power_8192_2048/metrics.json", "dataset", f"commit {commit}; produced by src/m11_powerdiagram.py on 2026-09-12"),
 ("E104", "The historical-cartogram repository (code, records, figure provenance, manuscript source)", "software", f"https://github.com/philippbogdan/historical-cartogram commit {commit}"),
 ("E105", "arXiv API listing of all records matching all:cartogram, retrieved 2026-09-12", "registry", "paper/registry/refs/arxiv_cartogram_2026-09-12.xml: 37 entries, none with optimal transport, Monge-Ampere, Brenier or Wasserstein in title or abstract"),
]
sources = []
for eid, key, st, loc in lit:
    authors = [a.strip() for a in field(key, "author").split(" and ") if a.strip()]
    year = field(key, "year"); doi = field(key, "DOI") or field(key, "doi"); url = field(key, "url")
    sources.append({"evidence_id": eid, "title": field(key, "title"), "authors": authors, "year": int(year) if year.isdigit() else None, "source_type": st,
                    "identifiers": {"doi": doi, "isbn": field(key, "ISBN") if st == "book" else "", "pmid": "", "pmcid": "", "url": url}, "locator": loc, "confidentiality": "public",
                    "verification": {"status": "verified", "source_opened": True, "verified_by": VERIFIER, "verified_on": TODAY}})
for eid, title, st, loc in own:
    sources.append({"evidence_id": eid, "title": title, "authors": ["Philipp Bogdan"], "year": 2026, "source_type": st,
                    "identifiers": {"doi": "", "isbn": "", "pmid": "", "pmcid": "", "url": "https://github.com/philippbogdan/historical-cartogram"}, "locator": loc, "confidentiality": "public",
                    "verification": {"status": "verified", "source_opened": True, "verified_by": VERIFIER, "verified_on": TODAY}})
json.dump({"schema_version": "1.0", "sources": sources}, open(os.path.join(REG, "source_manifest.json"), "w"), indent=2)

# numeric facts from numbers.json
N = json.load(open(os.path.join(PAPER, "numbers.json")))
facts = []; k = 0
def fact(concept, value, unit, section, ev, analysis_set):
    global k; k += 1
    facts.append({"fact_id": f"N{k:03d}", "concept": concept, "value": value, "unit": unit, "section": section, "evidence_ids": [ev], "analysis_set": analysis_set, "numerator": None, "denominator": None, "sample_size": None})
for tag, rec in N.items():
    if not tag.startswith("b"): continue
    for key in ("err_p05_pct", "err_p95_pct", "aniso_p50", "aniso_p95", "twist_p50", "twist_p95", "cost_frame2", "disp_popmean_frame", "shape", "folds", "seconds"):
        fact(f"{tag}.{key}", rec[key], "percent" if key.startswith("err") else ("degrees" if key.startswith("twist") else ("seconds" if key == "seconds" else "ratio" if key != "folds" else "count")), "Results", "E101", tag)
for w in (1024, 2048, 4096):
    if f"cost_ratio_{w}" in N: fact(f"cost_ratio_{w}", N[f"cost_ratio_{w}"], "ratio", "Results", "E101", f"b{w}")
if "hero" in N:
    for key, v in N["hero"].items():
        if isinstance(v, (int, float)): fact(f"hero.{key}", v, "mixed", "Results", "E101", "b4096_ot_hero")
if "delhi" in N:
    for key in ("smoothed_before_p05", "smoothed_before_p95", "smoothed_after_p05", "smoothed_after_p95", "local_residual", "local_folds", "seconds"):
        fact(f"delhi.{key}", N["delhi"][key], "log-ratio" if "p" in key else "mixed", "Results", "E102", "delhi")
    fact("delhi.population", N["delhi_params"]["population"], "people", "Results", "E102", "delhi")
if "m11" in N:
    fact("m11.N", N["m11"]["N"], "count", "Results", "E103", "m11"); fact("m11.people_per_cell", N["m11"]["people_per_cell"], "people", "Results", "E103", "m11")
    fact("m11.mass_spread_min", N["m11"]["mass_spread"][0], "ratio", "Results", "E103", "m11"); fact("m11.mass_spread_max", N["m11"]["mass_spread"][1], "ratio", "Results", "E103", "m11")
methods = [
 {"method_id": "M001", "name": "Spectral fixed-point Monge-Ampere solve (BFO method 1) with continuation in the share", "analysis_intent": "descriptive", "protocol_status": "prespecified", "outcome_ids": ["O001", "O002", "O003", "O004", "O005"]},
 {"method_id": "M002", "name": "Gastner-Newman diffusion cartogram, own implementation, t0 = 0.01", "analysis_intent": "descriptive", "protocol_status": "prespecified", "outcome_ids": ["O001", "O002", "O003", "O004", "O005"]},
 {"method_id": "M003", "name": "Nested transport to the global map's area measure (Delhi window)", "analysis_intent": "descriptive", "protocol_status": "prespecified", "outcome_ids": ["O006"]},
 {"method_id": "M004", "name": "Semi-discrete transport to 8192 equal masses (pysdot)", "analysis_intent": "descriptive", "protocol_status": "prespecified", "outcome_ids": ["O007"]},
]
results = []; r = 0
for mid, tags in (("M001", ["b1024_ot_s95", "b2048_ot_s95", "b4096_ot_s95", "b4096_ot_hero"]), ("M002", ["b1024_d_s95", "b2048_d_s95", "b4096_d_s95"])):
    for tag in tags:
        w = int(tag[1:5])
        for oid in ("O001", "O002", "O003", "O004", "O005"):
            r += 1; results.append({"result_id": f"R{r:03d}", "method_id": mid, "outcome_id": oid, "analysis_intent": "descriptive", "evidence_ids": ["E101"], "reported_sections": ["Results"], "sample_size": w * w})
n_win = int(N["delhi_params"]["cells"]) if "delhi_params" in N else 2400
r += 1; results.append({"result_id": f"R{r:03d}", "method_id": "M003", "outcome_id": "O006", "analysis_intent": "descriptive", "evidence_ids": ["E102"], "reported_sections": ["Results"], "sample_size": n_win * n_win})
r += 1; results.append({"result_id": f"R{r:03d}", "method_id": "M004", "outcome_id": "O007", "analysis_intent": "descriptive", "evidence_ids": ["E103"], "reported_sections": ["Results"], "sample_size": int(N["m11"]["N"]) if "m11" in N else 8192})
json.dump({"schema_version": "1.0", "methods": methods, "numeric_facts": facts, "results": results}, open(os.path.join(REG, "consistency_manifest.json"), "w"), indent=2)

authorship = {"schema_version": "1.0",
  "authors": [{"author_id": "A001", "name": "Philipp Bogdan", "is_human": True, "credit_roles": ["conceptualization", "methodology", "software", "investigation", "visualization", "writing – original draft", "writing – review & editing"],
               "authorship_criteria": {"substantial_contribution": True, "drafted_or_critically_revised": True, "final_approval": False, "accountable_for_work": True}}],
  "contributors": [], "corresponding_author_id": "A001",
  "accountability": {"all_authors_approved": False, "guarantor_author_ids": ["A001"]},
  "ai_use": {"used": True, "tools": [{"name": "Claude Code (Claude Fable 5.1)", "version": "CLI 2.1.x, model claude-fable-5-1, 2026-09-12", "provider": "Anthropic", "purpose": "code, benchmark runs, figures and manuscript drafting under the author's direction; author decision 2026-09-12: no AI-use statement in the arXiv version, record kept here", "materials_sent": "public_text", "external_service": True}], "disclosed_in": [], "human_verification_complete": False, "journal_policy_checked": False},
  "declarations": {"ai_use": {"status": "not_applicable", "content_sha256": "", "verified_by": "", "verified_on": ""},
                   "author_contributions": {"status": "not_applicable", "content_sha256": "", "verified_by": "", "verified_on": ""},
                   "conflicts": {"status": "draft", "content_sha256": "", "verified_by": "", "verified_on": ""},
                   "funding": {"status": "draft", "content_sha256": "", "verified_by": "", "verified_on": ""}}}
json.dump(authorship, open(os.path.join(REG, "authorship.json"), "w"), indent=2)
json.dump({"schema_version": "1.0", "guideline_id": "none-applicable", "disclaimer": "Non-scoring coverage aid only; not a quality appraisal or compliance certificate.",
           "items": [{"topic": "reporting guideline", "status": "not_applicable", "rationale": "computational methods note; no clinical or observational reporting guideline applies"}]},
          open(os.path.join(REG, "reporting_coverage.json"), "w"), indent=2)
print("registries written:", len(sources), "sources,", len(facts), "facts,", len(results), "results; commit", commit)
