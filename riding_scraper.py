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

province_pages = {
    'Ontario': 'ON',
    'Quebec': 'QC',
    'Nova Scotia': 'NS',
    'New Brunswick': 'NB',
    'Manitoba': 'MB',
    'British Columbia': 'BC',
    'Prince Edward Island': 'PE',
    'Saskatchewan': 'SK',
    'Alberta': 'AB',
    'Newfoundland and Labrador': 'NL',
    'Northwest Territories': 'NT',
    'Yukon': 'YK',
    'Nunavut': 'NU'
}

deltaPercent = '\u2206%'

re_province = re.compile("({})".format("|".join(province_pages.keys())))
re_year = re.compile(r', (\d\d\d\d)')
re_federal_election = re.compile(r'.*Canad(?:a|ian)\s+federal.*?((?:by-?)?)election.*?(?:(\w+)\s+([\w\d]+),?\s+)?(\d\d\d\d).*')
re_electoral_district = re.compile(r'\(([a-zA-Z0-9\s]*)?electoral district\)')


def filter_dash(s):
    dash, dash1 = '\u2014', '\u2015'
    return s.replace(dash, "-").replace(dash1, "-")

def filter_riding_page_title(page_title):
    return re_electoral_district.sub("", filter_dash(page_title)).strip()


def process_mps_table(db, result_tbl, riding_id, source=None):
    tbl = Table(result_tbl, header_all=True)

    if not tbl or not (tbl[0, 0] and 'Parliament' in tbl[0, 0].text):
        return False

    prev_years = None
    items = []
    prev_item = None

    for i in range(1, tbl.n_rows):
        text = tbl[i, 0].text.lower()

        if tbl[i, 0].colspan > 1:
            dissolved = 'dissolved' in text
            links = list(a.attrs.get('title') for a in tbl[i, 0].elem.select('a'))
            prev_item = [prev_years, None, dissolved, links]
        else:
            prev_years = tbl[i, 1].text
            if prev_item:
                prev_item[1] = tbl[i, 1].text
                items.append(prev_item)

    for item in items:
        for linked_riding_id in item[3]:
            args = dict(
                riding_id=riding_id,
                linked_riding_id=filter_riding_page_title(linked_riding_id),
                prev_years=filter_dash(item[0]) if item[0] else None,
                next_years=filter_dash(item[1]) if item[1] else None,
                is_dissolved=item[2])
            rc_id = schema.make_rc_id(**args)
            db.declare("RidingChange", rc_id=rc_id, **args)

    return True


def process_election_table(db, result_tbl, riding_id, source=None):
    header = lambda xs: (
        xs[-1].text
        if len(xs) > 1 and xs[-1]
        else ": ".join(x.text for x in xs if x is not None))

    tbl = Table(result_tbl, header_all=True)
    transposed = tbl.transpose(to_s=False, header=header)
    first_cell = tbl[0, 0]
    title = None
    caption = tbl.caption
    if first_cell is not None and first_cell.colspan > 1:
        title = first_cell.text
    else:
        title = caption.text if caption else None

    election_id, year, re_id = None, None, None
    if title is not None:
        assert isinstance(title, str), title
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

            election_id = schema.make_election_id(year)
            re_id = schema.make_re_id(election_id, riding_id)
        else:
            is_by_election, by_election_date, year, re_id = None, None, None, None

    if year is None: return

    party_colours = transposed.get((0, 'Party'))
    parties = transposed.get((1, 'Party'))
    if parties is None: return

    indices = [
        i for i, (pc, p) in enumerate(zip(party_colours, parties))
        if pc.colspan == 1 and pc.rowspan == 1
    ]

    transposed = {k: v for (i, k), v in transposed.items()}
    candidates = transposed.get("Candidate")
    votes = transposed.get("Votes")
    if votes is None or candidates is None: return

    percents = transposed.get("%")
    delta_percents = transposed.get(deltaPercent)
    expenditures = transposed.get("Expenditures")
    elected = transposed.get("Elected")

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

    summaries = {k: to_dict(find_row(k)) for k in ("total valid vote", "rejected ballot", "turnout")}

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
            ("Expenditures", expenditures),
            ("Elected", elected),
            (deltaPercent, delta_percents))
    })

    for order, row in df.iterrows():
        if any(not (x.rowspan == 1 and x.colspan == 1)
                for x in row if x is not None):
            return

        def get(x):
            c = row.get(x)
            return None if c is None else c.text

        keys = ("Colour", "Party", "Candidate", "Votes", "%", deltaPercent, "Expenditures")
        colour, party, candidate, votes, percent, delta_percent, expenditures = list(map(get, keys))
        elected = row.get("Elected")
        elected = (order == 0) if elected is None else bool(elected.text.strip())

        if votes and '|' in votes:
            xs = votes.split('|')
            votes, percent = xs[0], xs[1]

        if colour:
            db.declare(
                "Party",
                party_name=party,
                colour=colour)

        db.declare(
            "RidingElection",
            source=source.title,
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
            source=source.title,
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
            votes_percent=percent,
            delta_percent=delta_percent,
            expenditures=expenditures,
            elected=elected)


def find_province(links):
    province_links = [(link, province_pages[link]) for link in links if link in province_pages]
    if len(province_links) > 1:
        logging.debug("Multiple provinces: {} {}".format(province_links, province_links[0][1]))

    if len(province_links): return province_links[0][1]

    for p in province_pages:
        for l in links:
            if l in p or p in l:
                return province_pages[p]


def find_geo(doc):
    def process(x):
        if not x: return None
        return x[0].text

    assert isinstance(doc, BeautifulSoup)
    lat, lon = doc.select('span.geo-dms span.latitude'), doc.select('span.geo-dms span.longitude')
    lat, lon = process(lat), process(lon)
    if lat is None or lon is None: return None
    else: return lat, lon


def find_geos(riding_page):
    doc = BeautifulSoup(riding_page.html(), 'html.parser')
    print(find_geo(doc))
    subdivs = [tr for tr in doc.select('table tr') if "Census subdivisions" in str(tr.find("th"))]
    if not subdivs: return None

    subdivs = [a.get("title") for a in subdivs[0].select('a[title]')]
    subdiv_geos = {}
    for subdiv in subdivs:
        doc = BeautifulSoup(wiki.page(title=subdiv, auto_suggest=False).html(), 'html.parser')
        geo = find_geo(doc)
        if geo is not None: subdiv_geos[subdiv] = geo

    return subdiv_geos


def process_page(tup):
    link_title, text, lock, counter, length, dict1 = tup
    db = schema.make_standard_database()
    riding_page = wiki.page(title=link_title, auto_suggest=False)
    del link_title

    with lock:
        logger.info("[{:4}/{:4}]: {}".format(counter.value, length, riding_page.title))
        counter.value += 1

    doc = BeautifulSoup(riding_page.html(), 'html.parser')
    # page_outline = DocumentOutline(doc)

    tables = list(doc.select('table'))
    riding_id = filter_riding_page_title(riding_page.title)

    for result_tbl in tables:
        ret = process_mps_table(
            db=db,
            result_tbl=result_tbl,
            source=riding_page,
            riding_id=riding_id)

        if ret: continue

        process_election_table(
            db=db,
            result_tbl=result_tbl,
            source=riding_page,
            riding_id=riding_id)

    province = find_province(riding_page.links)
    geo = find_geo(doc)
    db.declare(
        "Riding",
        riding_id=riding_id,
        riding_name=riding_id,
        province=province)

    return db


def page_titles(link):
    listing_page = wiki.page(title=link)
    doc = BeautifulSoup(listing_page.html(), 'html.parser')
    outline = DocumentOutline(doc)
    logger.info(" - " + repr(link))

    items = outline.headings.items()
    for idx, (i, h) in enumerate(items):
        if "References" in h.title or "External" in h.title or "See also" in h.title:
            continue

        province = re_province.match(h.title)
        if province: province = province.group(1)
        if province is not None:
            logger.info("    - {}".format(province))

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
    link_title, text, lock, counter, length, dict1 = tup
    y, res = 0, None
    wiki.initialize_sub(dict1)

    with lock: y = counter.value

    if y == 42:
        logger.info("Running profiler.")
        cProfile.runctx('process_page(tup)', globals(), locals(), 'output/profile.prof')
        counter.value -= 1

    res = process_page(tup)
    assert res is not None, tup
    return res


def main():
    pd.set_option('display.width', 700)
    m = mp.Manager()
    dict1 = m.dict()
    wiki.initialize_main(dict1)

    parent_page = wiki.page(title="Historical federal electoral districts of Canada")
    links = [p for p in parent_page.links
             if "list of canadian" in p.lower() and "electoral districts" in p.lower()][::-1]

    links = list(set(it.chain.from_iterable(map(lambda link: list(page_titles(link)), links))))
    links.sort()
    with mp.Pool(processes=mp.cpu_count()) as pool:
        lock = m.Lock()
        counter = m.Value('i', 0)

        results = pool.map(
            process_page_profiled,
            [(l, t, lock, counter, len(links), dict1) for l, t in links])
        #pool.terminate()
        #pool.join()

    db = schema.make_standard_database()
    for db1 in results:
        db.update_from(db1)

    return db
