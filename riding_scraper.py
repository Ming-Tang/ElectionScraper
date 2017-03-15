from __future__ import division, print_function
from bs4 import BeautifulSoup
from bs4.element import Tag
from collections import defaultdict
from wiki_scraper import *
import pprint
import itertools as it
import wikipedia
import pandas as pd
import re

re_province = re.compile(r"^([^-]+)(\s*-\s*\d+\s+seats?)?$")
re_years = re.compile(r"^\s*List.*Canadian.*,?\s+(\d+)\W(\d+)\s*$")

pd.set_option('display.width', 640)

#page = wikipedia.page('1918 New Year Honours')
#bs = BeautifulSoup(page.html(), 'html.parser')
#raise SystemExit()

parent_page = wikipedia.page(title="Historical federal electoral districts of Canada")
links = [p for p in parent_page.links if "List of Canadian" in p and "electoral districts" in p]

ridings = defaultdict(lambda: set())

last_year = 0
for link in links:
    page = wikipedia.page(title=link)
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
            #print(" - {} -> {!r}".format(text, title))
            for year in range(start_year, end_year + 1):
                ridings[text].add(year)

print(ridings)
