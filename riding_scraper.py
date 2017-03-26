from __future__ import division, print_function
from bs4 import BeautifulSoup
from bs4.element import Tag
from collections import defaultdict
from wiki_scraper import *
import sys
import schema
import pprint
import itertools as it
import wikipedia_cached as wiki
import pandas as pd
import re
import multiprocessing as mp
import logging

def setup_logging():
    logger = logging.getLogger()

    ch = logging.StreamHandler(sys.stderr)
    logger.addHandler(ch)
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s | %(message)s')
    ch.setFormatter(formatter)

    return logger

logger = setup_logging()

deltaPercent = '\u2206%'

re_province = re.compile(r"^([^-]+)(\s*-\s*\d+\s+seats?)?$")
re_years = re.compile(r"^\s*List.*Canadian.*,?\s+(\d+)\W(\d+)\s*$")
re_year = re.compile(r', (\d\d\d\d)')
re_federal_election = re.compile(r'Canad(?:a|ian)\s+federal\D+(\d\d\d\d)')

db = schema.make_standard_database()

def process_page(tup):
    link, i0, nn = tup
    output = []
    #print = lambda x: output.append(str(x))

    party_candidates = defaultdict(lambda: defaultdict(lambda: None))
    listing_page = wiki.page(title=link)
    outline = DocumentOutline(BeautifulSoup(listing_page.html(), 'html.parser'))
    print("")
    print("# " + repr(link))

    #year_matches = re_years.match(link)
    #if year_matches is None:
    #    start_year, end_year = last_year, 2017
    #else:
    #    start_year, end_year = year_matches.group(1), year_matches.group(2)
    #    start_year, end_year = int(start_year), int(end_year)
    #    assert start_year >= 1867 and end_year >= 1867
    #    assert end_year >= start_year
    #    last_year = end_year

    logger.info("[{:3}/{:3}] {}".format(i0, nn, link))
    items = outline.headings.items()
    for idx, (i, h) in enumerate(items):
        print("")
        if "References" in h.title or "External" in h.title or "See also" in h.title:
            continue

        province = re_province.match(h.title)
        if province: province = province.group(1)
        if province is None: print("## " + str(h.title))
        print("## " + province)
        logger.info("    [{:3}/{:3}]: {}".format(idx, len(items), province))

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

        # TODO process_province
        subitems = list(gen())
        for subidx, a in enumerate(subitems):
            link_title, text = a.attrs.get('title', a.text), a.text
            logger.info("      [{:3}/{:3}]: {}".format(subidx, len(subitems), link_title))

            riding_page = wiki.page(title=link_title, auto_suggest=False)
            doc = BeautifulSoup(riding_page.html(), 'html.parser')
            page_outline = DocumentOutline(doc)
            print("### {} -> {!r}".format(text, link_title))
            try:
                pass
                #tbl = Table(doc.select('table.infobox')[0], header_all=True)
                #print("    {}".format(tbl.transpose(to_s=True, indexed=False, transpose=True)))
            except IndexError:
                pass

            tables = list(page_outline.soup.select('table'))
            # TODO get heading multi-level
            #print("    ", {page_outline.get_heading(t) for t in tables})
            result_tbls = [
                t for t in tables
                #if t and page_outline.get_heading(t) and
                #"result" in page_outline.get_heading(t).title.lower()
            ]

            header = lambda xs: (
                xs[-1].text
                if len(xs) > 1 and xs[-1]
                else ": ".join(x.text for x in xs if x))

            for result_tbl in result_tbls:
                tbl = Table(result_tbl, header_all=True)
                transposed = tbl.transpose(to_s=False, header=header)
                first_cell = tbl[0, 0]
                title = None
                caption = tbl.caption
                if first_cell is not None and first_cell.colspan > 1:
                    title = first_cell.text
                else:
                    title = caption.text if caption else None

                riding_id = link_title
                election_id = None
                if title is None:
                    print("")
                    print("```")
                    print(pprint.pformat(tbl))
                    print(pprint.pformat(tbl.to_dict()))
                    print("```")
                    print("")
                else:
                    print("<h4>Title: {}</h4>".format(title))
                    print("")
                    match = re_federal_election.match(title)
                    if match is not None:
                        year = int(match.groups(1)[0])
                        print(" - Year: {}".format(year))
                        election_id = schema.make_election_id(year)
                        re_id = schema.make_re_id(election_id, riding_id)

                party_colours = transposed.get((0, 'Party'))
                parties = transposed.get((1, 'Party'))
                if parties is None: continue

                indices = [
                    i for i, (pc, p) in enumerate(zip(party_colours, parties))
                    if pc.colspan == 1 and pc.rowspan == 1
                ]

                transposed = {k: v for (i, k), v in transposed.items()}
                candidates = transposed.get("Candidate")
                votes = transposed.get("Votes")
                if votes is None or candidates is None: continue

                percents = transposed.get("%")
                deltaPercents = transposed.get(deltaPercent)
                if False and tbl[0, 0] and tbl[0, 0].colspan > 1:
                    print("<h4>{}</h4>".format(tbl[0, 0]))
                    print("")

                df = pd.DataFrame({
                    k: [x[i] for i in indices] if x is not None else None
                    for k, x in (
                        ("Colour", party_colours),
                        ("Party", parties),
                        ("Candidate", candidates),
                        ("Votes", votes),
                        ("%", percents),
                        (deltaPercent, deltaPercents))
                })
                if True:
                    print("")
                    print("```")
                    print(df)
                    print("```")
                    print("")

                for tup in df[["Colour","Party","Candidate","Votes","%"]].values:
                    colour, party, candidate, votes, percent = [
                        x.text if x else None
                        for x in tup
                    ]
                    db.declare(
                        "CandidateRidingElection",
                        source=link_title,
                        cre_id=schema.make_cre_id(
                            re_id=re_id,
                            candidate_name=candidate,
                            party_name=party
                        ),
                        party_name=party,
                        candidate_name=candidate,
                        re_id=re_id,
                        votes=votes,
                        votes_percent=percent)

                #for p, c in zip(df.Party, df.Candidate):
                #    party_candidates[p.text][c.text] = a.text

            #for year in range(start_year, end_year + 1):
            #    ridings[text].add(year)

    #return {k: dict(v) for k, v in party_candidates.items()}
    output.append("")
    return "\n".join(output)

if __name__ == "__main__":
    pd.set_option('display.width', 700)

    parent_page = wiki.page(title="Historical federal electoral districts of Canada")
    links = [(p, i, len(parent_page.links))
             for i, p in enumerate(parent_page.links)
             if "List of Canadian" in p and "electoral districts" in p]
    links = links[::-1]

    ridings = defaultdict(lambda: set())

    party_candidates = defaultdict(lambda: defaultdict(lambda: None))

    results = []
    try:
        if False:
            with mp.Pool(processes=mp.cpu_count()) as pool:
                results = pool.map(process_page, links)
                pool.terminate()
                pool.join()
        else:
            results = list(map(process_page, links))

    finally:
        print("<hr />")
        results1 = "\n".join(results)
        if results1: print(results1)
        import pickle
        with open("db.pickle", "wb") as f: pickle.dump(db, file=f)


    #party_candidates = defaultdict(lambda: defaultdict(lambda: set()))
    #for d in results:
    #    for k, v in d.items():
    #        party_candidates[k].update(v)

    #print(party_candidates)

    #pprint.pprint(list(party_candidates.keys()))
    #pprint.pprint({k: dict(v) for k, v in party_candidates.items()})
