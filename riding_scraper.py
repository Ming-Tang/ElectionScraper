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
    formatter = logging.Formatter('%(asctime)s %(processName)s | %(message)s')
    ch.setFormatter(formatter)

    return logger

logger = setup_logging()

deltaPercent = '\u2206%'

re_province = re.compile(r"^([^-]+)(\s*-\s*\d+\s+seats?)?$")
re_year = re.compile(r', (\d\d\d\d)')
re_federal_election = re.compile(r'.*Canad(?:a|ian)\s+federal.*?((?:by-?)?)election.*?(?:(\w+)\s+([\w\d]+),?\s+)?(\d\d\d\d).*')

def process_page(tup):
    db = schema.make_standard_database()

    link, i0, nn = tup

    listing_page = wiki.page(title=link)
    outline = DocumentOutline(BeautifulSoup(listing_page.html(), 'html.parser'))
    print("")
    print("# " + repr(link))

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
            riding_page = wiki.page(title=link_title, auto_suggest=False)
            del link_title

            page_title = riding_page.title
            logger.info("      [{:3}/{:3}]: {}".format(subidx, len(subitems), page_title))
            page_title = riding_page.title
            doc = BeautifulSoup(riding_page.html(), 'html.parser')
            page_outline = DocumentOutline(doc)
            print("### {} -> {!r}".format(text, page_title))
            try:
                pass
                #tbl = Table(doc.select('table.infobox')[0], header_all=True)
                #print("    {}".format(tbl.transpose(to_s=True, indexed=False, transpose=True)))
            except IndexError:
                pass

            tables = list(page_outline.soup.select('table'))
            header = lambda xs: (
                xs[-1].text
                if len(xs) > 1 and xs[-1]
                else ": ".join(x.text for x in xs if x))

            for result_tbl in tables:
                tbl = Table(result_tbl, header_all=True)
                transposed = tbl.transpose(to_s=False, header=header)
                first_cell = tbl[0, 0]
                title = None
                caption = tbl.caption
                if first_cell is not None and first_cell.colspan > 1:
                    title = first_cell.text
                else:
                    title = caption.text if caption else None

                riding_id = page_title
                election_id = None
                if title is None:
                    print("")
                    print("```")
                    print("# No Title")
                    print(pprint.pformat(tbl))
                    print(pprint.pformat(tbl.to_dict()))
                    print("```")
                    print("")
                else:
                    print("<h4>Title: {}</h4>".format(title))
                    print("")
                    match = re_federal_election.match(title)
                    if match is not None:
                        is_by_election = bool(match.groups(1)[0])
                        year = int(match.groups(1)[3])
                        if is_by_election:
                            month, day = match.groups(1)[1], match.groups(1)[2]
                            if month == 1 or day == 1:
                                by_election_date = year
                            else:
                                by_election_date = "{} {}, {}".format(month, day, year)
                        else:
                            by_election_date = None

                        print(" - Year: {}".format(year))
                        print("")
                        election_id = schema.make_election_id(year)
                        re_id = schema.make_re_id(election_id, riding_id)
                    else:
                        is_by_election, by_election_date, year, re_id = None, None, None, None
                        print(" - *Year is not determined*: `{}`".format(title))
                        print("")

                if year is None: continue

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
                    if any(not (x.rowspan == 1 and x.colspan == 1)
                           for x in tup if x is not None):
                        continue

                    colour, party, candidate, votes, percent = [
                        x.text if x else None
                        for x in tup
                    ]

                    if votes and '|' in votes:
                        xs = votes.split('|')
                        votes, percent = xs[0], xs[1]

                    if isinstance(candidate, str) and (
                        ('swing' in candidate.lower() or 'hold' in candidate.lower())):
                        print("Filter out:")
                        print("```")
                        print(tup)
                        print("```")
                        pass

                    # print("```")
                    db.declare(
                        "RidingElection",
                        re_id=re_id,
                        by_election_date=by_election_date,
                        is_by_election=is_by_election)
                    db.declare(
                        "CandidateRidingElection",
                        source=page_title,
                        cre_id=schema.make_cre_id(
                            re_id=re_id,
                            candidate_name=candidate,
                            party_name=party),
                        party_name=party,
                        candidate_name=candidate,
                        re_id=re_id,
                        votes=votes,
                        votes_percent=percent)
                    # print("```")

    return db


if __name__ == "__main__":
    pd.set_option('display.width', 700)

    parent_page = wiki.page(title="Historical federal electoral districts of Canada")
    links = [p for p in parent_page.links
             if "List of Canadian" in p and "electoral districts" in p][::-1]
    links = [(p, i, len(links)) for i, p in enumerate(links)]

    try:
        db = schema.make_standard_database()
        results = []
        if True:
            with mp.Pool(processes=mp.cpu_count()) as pool:
                results = pool.map(process_page, links)
                pool.terminate()
                pool.join()
        else:
            results = list(map(process_page, links))

        for db1 in results:
            db.update_from(db1)
    finally:
        print("<hr />")
        import pickle
        with open("db.pickle", "wb") as f: pickle.dump(db, file=f)

