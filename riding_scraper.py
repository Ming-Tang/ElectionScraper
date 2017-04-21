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
import cProfile
import pickle

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
re_electoral_district = re.compile(r'\(([a-zA-Z0-9\s]*)?electoral district\)')

def filter_page_title(page_title):
    dash, dash1 = '\u2014', '\u2015'
    page_title = page_title.replace(dash, "-").replace(dash1, "-")
    return re_electoral_district.sub("", page_title).strip()


def process_page(tup):
    link_title, text, lock, counter, length = tup
    db = schema.make_standard_database()
    riding_page = wiki.page(title=link_title, auto_suggest=False)
    del link_title

    page_title = riding_page.title
    with lock:
        logger.info("[{:4}/{:4}]: {}".format(counter.value, length, page_title))
        counter.value += 1

    page_title = riding_page.title
    doc = BeautifulSoup(riding_page.html(), 'html.parser')
    page_outline = DocumentOutline(doc)
    print = lambda *args, **kwargs: None
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

        riding_id = filter_page_title(page_title)
        election_id = None
        year = None
        re_id = None
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

        get_text = lambda x: None if x is None else x.text
        d = tbl.to_dict()
        keys0, keys1 = d[0], d[1]
        keys = keys1 if len(keys0) <= 1 else keys1
        rows = {
            k: [(k1, get_text(keys[k1]), get_text(v1)) for k1, v1 in v.items()]
            for k, v in tbl.to_dict().items()
        }

        def find_row(name):
            for k, row in rows.items():
                found = False
                for i, (ii, key, value) in enumerate(row):
                    matches = value and name in value.lower()
                    if not found:
                        if matches:
                            found = True
                    else:
                        if not matches:
                            return row[ii:]
            return None

        def to_dict(items):
            if items is None: return {}
            return {
                (None if key is None else key.lower()): value
                for ii, key, value in items
            }

        #pprint.pprint('--------------------------------')
        #pprint.pprint(keys)
        #pprint.pprint(rows)
        #pprint.pprint(re_id)

        summaries = {k: to_dict(find_row(k)) for k in ("total valid vote", "rejected ballot", "turnout")}
        #pprint.pprint(summaries)

        expense_limit = summaries['total valid vote'].get('expenditures')
        total_valid_vote = summaries['total valid vote'].get('votes')
        voter_turnout_percent = summaries['turnout'].get('%')
        voter_turnout_count = summaries['turnout'].get('votes')
        rejected_ballot = summaries['rejected ballot'].get('votes')
        rejected_ballot_percent = summaries['rejected ballot'].get('%')

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

        for order, tup in enumerate(df[["Colour","Party","Candidate","Votes","%"]].values):
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

            if colour:
                db.declare(
                    "Party",
                    party_name=party,
                    colour=colour)

            # print("```")
            db.declare(
                "RidingElection",
                source=page_title,
                re_id=re_id,
                election_id=election_id,
                riding_id=riding_id,
                by_election_date=by_election_date,
                is_by_election=is_by_election,
                total_valid_vote=total_valid_vote,
                voter_turnout=voter_turnout_count,
                voter_turnout_percent=voter_turnout_percent,
                rejected_ballot=rejected_ballot,
                rejected_ballot_percent=rejected_ballot_percent,
                expense_limit=expense_limit)
            db.declare(
                "CandidateRidingElection",
                source=page_title,
                riding_id=riding_id,
                election_id=election_id,
                order=order,
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


def page_titles(link):
    #logger.info(link)
    listing_page = wiki.page(title=link)
    outline = DocumentOutline(BeautifulSoup(listing_page.html(), 'html.parser'))
    #print("")
    print(" - " + repr(link))

    items = outline.headings.items()
    for idx, (i, h) in enumerate(items):
        #print("")
        if "References" in h.title or "External" in h.title or "See also" in h.title:
            continue

        province = re_province.match(h.title)
        if province: province = province.group(1)
        if province is None: print("    - " + str(h.title))
        print("    - " + province)
        #logger.info("    [{:3}/{:3}]: {}".format(idx, len(items), province))

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

        subitems = list(gen())
        for subidx, a in enumerate(subitems):
            link_title, text = a.attrs.get('title', a.text), a.text
            yield link_title, text


def process_page_profiled(tup):
    link_title, text, lock, counter, length = tup
    y = 0
    res = None
    with lock: y = counter.value

    if y == 42:
        logger.info("Running profiler.")
        cProfile.runctx('process_page(tup)', globals(), locals(), 'output/profile.prof')

    res = process_page(tup)
    assert res is not None, tup
    return res


def f1(link): return list(page_titles(link))


def main():
    pd.set_option('display.width', 700)

    parent_page = wiki.page(title="Historical federal electoral districts of Canada")
    links = [p for p in parent_page.links
             if "List of Canadian" in p and "electoral districts" in p][::-1]

    links = list(set(it.chain.from_iterable(map(f1, links))))
    links.sort()
    with mp.Pool(processes=mp.cpu_count()) as pool:
        m = mp.Manager()
        lock = m.Lock()
        counter = m.Value('i', 0)
        results = pool.map(
            process_page_profiled,
            [(l, t, lock, counter, len(links)) for l, t in links])
        pool.terminate()
        pool.join()

    db = schema.make_standard_database()
    for db1 in results:
        db.update_from(db1)

    return db
