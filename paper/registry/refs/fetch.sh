#!/bin/zsh
# DOI -> bibtex via content negotiation; arXiv -> API. One file per key. Prints title lines for checking.
fetch_doi() { curl -sL -H "Accept: application/x-bibtex" "https://doi.org/$2" -o "$1.bib"; printf "%-22s %s\n" "$1" "$(grep -i -E '^\s*title' $1.bib | head -1 | cut -c1-110)"; }
fetch_arxiv() { curl -s "https://export.arxiv.org/api/query?id_list=$2" -o "$1.xml"; printf "%-22s %s\n" "$1" "$(grep -o '<title>[^<]*</title>' $1.xml | sed -n 2p | cut -c1-110)"; }
fetch_doi brenier1991      10.1002/cpa.3160440402
fetch_doi gastner2004      10.1073/pnas.0400280101
fetch_doi gastner2018      10.1073/pnas.1712674115
fetch_doi benamou2010      10.1051/m2an/2010017
fetch_doi loeper2005       10.1016/j.crma.2004.12.018
fetch_doi saumier2015      10.1093/imamat/hxt032
fetch_doi jacobs2020       10.1007/s00211-020-01154-8
fetch_doi mcrae2018        10.1137/16M1109515
fetch_doi budd2009         10.1137/080716773
fetch_doi weller2016       10.1016/j.jcp.2015.12.018
fetch_doi zhao2013         10.1109/TVCG.2013.135
fetch_doi hennig2013       10.1007/978-3-642-34848-8
fetch_doi nusrat2016       10.1111/cgf.12932
fetch_doi alam2015         10.1111/cgf.12647
fetch_doi carroll2008      10.1007/978-3-540-70970-1_5
fetch_doi cohenaddad2018   10.1145/3274895.3274979
fetch_doi merigot2011      10.1111/j.1467-8659.2011.02032.x
fetch_doi caffarelli1992   10.1090/S0894-0347-1992-1124980-8
fetch_doi benamoubrenier2000 10.1007/s002110050002
fetch_doi dougenik1985     10.1111/j.0033-0124.1985.00075.x
fetch_doi tobler2004       10.1111/j.1467-8306.2004.09401004.x
fetch_doi choi2018         10.1137/17M1124796
fetch_doi ghspop2023       10.2905/2FF68A52-5B5B-4A22-8F40-C41DA8332CFE
fetch_doi hennig2009       10.1007/978-3-642-34848-8_4
fetch_doi budd2015         10.1016/j.jcp.2014.11.007
fetch_doi sulman2011       10.1016/j.apnum.2010.10.006
fetch_doi villani2009      10.1007/978-3-540-71050-9
fetch_doi duncan2020       10.1111/cgf.14184
fetch_arxiv sargent2024    2411.17129
fetch_arxiv molchanov2026  2604.13880
fetch_arxiv miaji2025      2511.08121
fetch_arxiv saumier2010    1009.6039
fetch_arxiv jacobs2019     1905.12154
fetch_arxiv weller2015     1512.02935
fetch_arxiv mcrae2016      1612.08077
