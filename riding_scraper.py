from __future__ import division, print_function
from bs4 import BeautifulSoup
from bs4.element import Tag
from collections import defaultdict
from wiki_scraper import *
import pprint
import itertools as it
import wikipedia_cached as wiki
import pandas as pd
import re

deltaPercent = '\u2206%'

re_province = re.compile(r"^([^-]+)(\s*-\s*\d+\s+seats?)?$")
re_years = re.compile(r"^\s*List.*Canadian.*,?\s+(\d+)\W(\d+)\s*$")

pd.set_option('display.width', 640)

#page = wiki.page('1918 New Year Honours')
#bs = BeautifulSoup(page.html(), 'html.parser')
#raise SystemExit()

parent_page = wiki.page(title="Historical federal electoral districts of Canada")
links = [p for p in parent_page.links if "List of Canadian" in p and "electoral districts" in p]

ridings = defaultdict(lambda: set())

party_candidates = defaultdict(lambda: defaultdict(lambda: None))

last_year = 0
for link in links[::-1][0:1]:
    page = wiki.page(title=link)
    outline = DocumentOutline(BeautifulSoup(page.html(), 'html.parser'))
    print("")
    print("# " + repr(link))

    year_matches = re_years.match(link)
    if year_matches is None:
        start_year, end_year = last_year, 2017
    else:
        start_year, end_year = year_matches.group(1), year_matches.group(2)
        start_year, end_year = int(start_year), int(end_year)
        assert start_year >= 1867 and end_year >= 1867
        assert end_year >= start_year
        last_year = end_year

    for i, h in outline.headings.items():
        print("")
        if "References" in h.title or "External" in h.title or "See also" in h.title:
            continue

        province = re_province.match(h.title)
        if province: province = province.group(1)
        if province is None: print(h.title)
        print("## " + province)
        def gen():
            for c in outline.get_children(i):
                if not isinstance(c, Tag): continue
                try:
                    if c.name != "ul": c = c.select('ul')[0]
                except IndexError:
                    continue

                if c.name == "ul":
                    for li in c.select("li"):
                        yield li.a

        for a in gen():
            title, text = a.attrs.get('title', a.text), a.text

            page = wiki.page(title=title, auto_suggest=False)
            doc = BeautifulSoup(page.html(), 'html.parser')
            page_outline = DocumentOutline(doc)
            print(" - {} -> {!r}".format(text, title))
            try:
                pass
                #tbl = Table(doc.select('table.infobox')[0], header_all=True)
                #print("    {}".format(tbl.transpose(to_s=True, indexed=False, transpose=True)))
            except IndexError:
                pass

            tables = list(page_outline.soup.select('table'))
            #print("    ", {page_outline.get_heading(t) for t in tables})
            result_tbls = [
                t for t in tables
                if t and page_outline.get_heading(t) and
                "results" in page_outline.get_heading(t).title.lower()
            ]

            header = lambda xs: (
                xs[-1].text
                if len(xs) > 1 and xs[-1]
                else ": ".join(x.text for x in xs if x))

            for b in result_tbls:
                tbl = Table(b, header_all=True)
                transposed = tbl.transpose(to_s=False, header=header)
                #pprint.pprint(transposed)

                party_colours = transposed.get((0, 'Party'))
                parties = transposed.get((1, 'Party'))
                if parties is None: continue

                indices = [
                    i for i, (pc, p) in enumerate(zip(party_colours, parties))
                    if pc.colspan == 1 and p.colspan == 1
                ]

                transposed = {k: v for (i, k), v in transposed.items()}
                candidates = transposed.get("Candidate")
                votes = transposed.get("Votes")
                if votes is None: continue

                percents = transposed.get("%")
                deltaPercents = transposed.get(deltaPercent)
                if False and tbl[0, 0] and tbl[0, 0].colspan > 1:
                    print("### {}".format(tbl[0, 0]))

                df = pd.DataFrame({
                    k: [x[i] for i in indices]
                    for k, x in (
                        ("Colour", party_colours),
                        ("Party", parties),
                        ("Candidate", candidates),
                        ("Votes", votes),
                        ("%", percents),
                        (deltaPercent, deltaPercents))
                    if x is not None
                })
                if False: print(df)

                for p, c in zip(df.Party, df.Candidate):
                    party_candidates[p.text][c.text] = a.text

                if False: print("----------")

            #for year in range(start_year, end_year + 1):
            #    ridings[text].add(year)

pprint.pprint(list(party_candidates.keys()))
pprint.pprint({k: dict(v) for k, v in party_candidates.items()})
