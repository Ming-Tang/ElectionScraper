from __future__ import division, print_function
from bs4 import BeautifulSoup
from bs4.element import Tag
from collections import defaultdict
from wiki_scraper import *
import pprint
import itertools as it
import wikipedia
import pandas as pd

pd.set_option('display.width', 640)

#for year in [
#    '2015', '2011', '2008', '2006', '2004', '2000',
#    '1997', '1993', '1988', '1984', '1980']:
year = '2015'
while True:
    page = wikipedia.page('Canadian Federal Election, ' + str(year))
    html = page.html()
    #r = requests.get('https://en.wikipedia.org/wiki/British_Columbia_general_election,_' + year)

    soup = BeautifulSoup(html, 'html.parser')
    info = soup.find(class_='infobox vevent')
    caption = info.caption.text
    children = [c for c in info.find_all('tr', recursive=False) if isinstance(c, Tag)]

    tables = soup.select('table') # .wikitable
    summary_table = [
        t for t in tables
        if isinstance(t.caption, Tag) and (
            t.caption and "Summary of" in t.caption.text) or (
                not t.caption and ("party leader" in t.text.lower() and "candidates" in t.text.lower()))
    ][0]
    summary = Table(summary_table)
    #print(summary)
    #pprint.pprint(summary.to_dict())
    #pprint.pprint(summary.transpose(True))

    res = summary.transpose(to_s=True, indexed=True)

    for k in res.keys():
        res[k] = res[k][0:-2]

    names = res[(1, 'Party')]
    colours = res[(0, 'Party')]
    keys = list(res.keys())[2:]

    parties = defaultdict(dict)
    for k in keys:
        for name, value in zip(names, res[k]):
            parties[k[1]][name] = value


    for name, colour in zip(names, colours):
        parties['Colour'][name] = colour


    #print(parties)
    print("--------------")
    print("[{}]".format(year))
    df = pd.DataFrame(parties)
    print(df)

    try:
        break
        year = [a.text for a in info.select('td.noprint > a') if len(a.text) == 4][0]
    except IndexError:
        break

    #tables_ = [Table(t) for t in tables]
    #for t in tables_:
    #    print("------------------------")
    #    print(t.caption.text if t.caption else "")
    #    #pprint.pprint(t.to_dict(func=lambda x: x.text if x is not None else None))
    #    pprint.pprint(t.transpose())

    #jinfobox = InfoBox(info)
    #jtbl1 = infobox.tables[1]
    #jpprint.pprint(tbl1.transpose(False, transpose=True))
