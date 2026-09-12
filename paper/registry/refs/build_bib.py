"""Assemble paper/refs.bib from the fetched DOI/arXiv records (one file per key). Keys are renamed;
fields are kept as fetched so a reader can diff them against the source records."""
import re, os, html, glob
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "refs.bib")
entries = []
def fix_key(txt, key):
    return re.sub(r'^\s*@(\w+)\{[^,]*,', lambda m: f"@{m.group(1)}{{{key},", txt.strip(), count=1)
for f in sorted(glob.glob("*.bib")):
    key = f[:-4]
    txt = open(f).read().strip()
    if not txt.startswith("@") or "DOI Not Found" in txt: continue
    txt = fix_key(txt, key)
    txt = re.sub(r"title=\{(.*?)\},", lambda m: "title={{" + m.group(1) + "}},", txt, count=1)   # keep title case
    txt = txt.replace("∗", "").replace("month=June", "month=jun").replace("month=Feb", "month=feb").replace("month=Jan", "month=jan").replace("month=Mar", "month=mar").replace("month=May", "month=may").replace("month=Aug", "month=aug").replace("month=Oct", "month=oct").replace("month=Nov", "month=nov").replace("month=Dec", "month=dec")
    txt = txt.replace("AN ALGORITHM TO CONSTRUCT CONTINUOUS AREA CARTOGRAMS", "An algorithm to construct continuous area cartograms")
    if key == "carroll2008": txt = txt.replace("author={Carroll, Grant and Moore, Antoni},", "author={Carroll, Grant and Moore, Antoni},\n  year={2008},")
    txt = txt.replace("},", "},\n  ").replace("{", "{", 1)
    entries.append(txt)
for f in sorted(glob.glob("*.xml")):
    key = f[:-4]; x = open(f).read()
    es = re.findall(r"<entry>(.*?)</entry>", x, re.S)
    if not es: continue
    e = es[0]
    title = html.unescape(re.search(r"<title>(.*?)</title>", e, re.S).group(1)).replace("\n", " ").strip()
    title = re.sub(r"\s+", " ", title)
    authors = " and ".join(html.unescape(a) for a in re.findall(r"<name>(.*?)</name>", e))
    year = re.search(r"<published>(\d{4})", e).group(1)
    aid = re.search(r"<id>http://arxiv.org/abs/(.*?)</id>", e).group(1)
    aid_nov = re.sub(r"v\d+$", "", aid)
    cat = re.search(r'<arxiv:primary_category[^>]*term="([^"]+)"', e)
    entries.append(f"@misc{{{key},\n  title={{{{{title}}}}},\n  author={{{authors}}},\n  year={{{year}}},\n  eprint={{{aid_nov}}},\n  archivePrefix={{arXiv}},\n  primaryClass={{{cat.group(1) if cat else ''}}},\n  url={{https://arxiv.org/abs/{aid_nov}}}\n}}")
entries.append("@misc{naturalearth,\n  title={Natural Earth, free vector and raster map data, version 5.1.1},\n  author={{Natural Earth}},\n  year={2022},\n  url={https://www.naturalearthdata.com/},\n  note={Public domain; 1:50m coastline and admin-0 boundaries, 1:110m coastline. Accessed 2026-09-12 via github.com/nvkelso/natural-earth-vector}\n}")
entries.append("@misc{pysdot,\n  title={pysdot: semi-discrete optimal transport in Python},\n  author={Leclerc, Hugo and M{\\'e}rigot, Quentin},\n  year={2019},\n  url={https://github.com/sd-ot/pysdot},\n  note={Version 0.2.39. Accessed 2026-09-12}\n}")
entries.append("@misc{repo,\n  title={historical-cartogram: code, experiments and figures for this paper},\n  author={Bogdan, Philipp},\n  year={2026},\n  url={https://github.com/philippbogdan/historical-cartogram}\n}")
open(OUT, "w").write("\n\n".join(entries) + "\n")
print("wrote", os.path.abspath(OUT), len(entries), "entries")
