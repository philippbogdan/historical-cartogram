"""body.md -> body.tex: pandoc with natbib, evidence IDs mapped to bibliography keys, abstract environment,
section numbers stripped (LaTeX numbers them)."""
import re, subprocess, os, sys
PAPER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PAPER, "registry"))
src = open(os.path.join(PAPER, "body.md")).read()
# abstract: turn the first section into a raw abstract environment
src = re.sub(r"## Abstract\n\n(.*?)\n\n## ", lambda m: "\\begin{abstract}\n\n" + m.group(1) + "\n\n\\end{abstract}\n\n## ", src, count=1, flags=re.S)
src = re.sub(r"^(#{2,3}) \d+(?:\.\d+)*\.? ", r"\1 ", src, flags=re.M)     # drop manual numbers
open(os.path.join(PAPER, "body_pandoc.md"), "w").write(src)
subprocess.run(["pandoc", "-f", "markdown+raw_tex", "-t", "latex", "--natbib", "--shift-heading-level-by=-1", "-o", os.path.join(PAPER, "body.tex"), os.path.join(PAPER, "body_pandoc.md")], check=True)
tex = open(os.path.join(PAPER, "body.tex")).read()
# evidence id -> bib key (same table as build_registries.lit)
import importlib.util
spec = importlib.util.spec_from_file_location("br", os.path.join(PAPER, "registry", "build_registries.py"))
table = re.findall(r'\("(E\d+)", "([a-z0-9]+)", "', open(os.path.join(PAPER, "registry", "build_registries.py")).read())
keys = dict(table)
keys.update({"E101": "repo", "E102": "repo", "E103": "repo", "E104": "repo", "E105": "repo"})
def fix(m):
    ids = [i.strip() for i in m.group(2).split(",")]
    return "\\" + m.group(1) + "{" + ",".join(dict.fromkeys(keys[i] for i in ids)) + "}"
tex = re.sub(r"\\(citep|citet|cite)\{([^}]*)\}", fix, tex)
tex = tex.replace("\\tightlist", "")
tex = tex.replace("\\section{Discussion}", "\\FloatBarrier\n\\section{Discussion}")
open(os.path.join(PAPER, "body.tex"), "w").write(tex)
print("body.tex written;", len(re.findall(r"\\cite", tex)), "citations")
