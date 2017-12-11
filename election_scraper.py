from __future__ import division, print_function
from bs4 import BeautifulSoup
from bs4.element import Tag
from collections import defaultdict
from wiki_scraper import *
import schema
import pprint
import itertools as it
import wikipedia_cached as wiki
import pandas as pd
import re

pd.set_option('display.width', 640)

def get_provincial_results(province_table, election_id):
    def translate(x):
        if "vote" in x.lower():
            return "vote"
        elif "seats" in x.lower():
            return "seats"
        else:
            return x

    by_province = Table(province_table)
    by_province_cells = by_province.to_dict()
    province_indices = {
        v.text: k for k, v in by_province_cells[0].items()
        if v is not None and len(v.text) < 3
    }
    party_indices = {}
    for k, v in list(by_province_cells.items())[1:]:
        if v[1] and v[2]:
            party_indices[(v[1].text, v[2].text)] = k

    provincial_results = defaultdict(lambda: defaultdict(defaultdict))
    for (party, attr), irow in party_indices.items():
        if 'no seats' in party.lower() or 'total seats' in party.lower(): continue
        for prov, icol in province_indices.items():
            provincial_results[prov][party][translate(attr)] = by_province_cells[irow][icol].text

    return {
        k: {kk: (vv.get('vote'), vv.get('seats')) for kk, vv in v.items()}
        for k, v in provincial_results.items()
    }


def main():
    db = schema.make_standard_database()

    year = '2015'
    while True:
        election_id = schema.make_election_id(int(year))
        page = wiki.page('Canadian federal election, ' + str(year), auto_suggest=False)
        html = page.html()

        soup = BeautifulSoup(html, 'html.parser')
        info = soup.find(class_='infobox vevent')
        caption = info.caption.text
        children = [c for c in info.find_all('tr', recursive=False) if isinstance(c, Tag)]

        tables = soup.select('table') # .wikitable

        try:
            province_table = [
                t for t in tables
                if "BC" in t.text and "AB" in t.text and "SK" in t.text
            ][0]
        except IndexError:
            province_table = None

        if province_table is not None:
            provincial_results = get_provincial_results(province_table, election_id=election_id)
            #pprint.pprint(provincial_results)
            #print(pd.DataFrame(provincial_results))
            for province, v in provincial_results.items():
                for party, (pv, seats) in v.items():
                    db.declare(
                        "ProvincialBreakdown",
                        pb_id=schema.make_pb_id(election_id, province=province, party_id=party),
                        province=province,
                        party_name=party,
                        election_id=election_id,
                        popular_vote_percent=pv,
                        seats=seats
                    )

        summary_table = [
            t for t in tables
            if isinstance(t.caption, Tag) and (
                t.caption and "Summary of" in t.caption.text) or (
                    not t.caption and ("party leader" in t.text.lower() and "candidates" in t.text.lower()))
        ][0]
        summary = Table(summary_table)

        res = summary.transpose(to_s=False, indexed=True)

        for k in res.keys():
            res[k] = res[k][0:-2]

        if (1, 'Party') not in res:
            #pprint.pprint(res)
            year = [a.text for a in info.select('td.noprint > a') if len(a.text) == 4][0]
            if year == '1867': break
            continue

        names = res[(1, 'Party')]
        colours = res[(0, 'Party')]
        keys = list(res.keys())[2:]

        parties = defaultdict(dict)
        for k in keys:
            for name, value in zip(names, res[k]):
                parties[k[1]][name.text] = (None if value is None else value.text)

        for name, colour in zip(names, colours):
            parties['Colour'][name.text] = colour.colour

        df = pd.DataFrame(parties)

        def find(xs):
            xs = list(xs)
            return None if not xs else xs[0]

        keys = df.columns
        key_candidates = find(k for k in keys if 'candidates' in k.lower())
        key_leader = find(k for k in keys if 'leader' in k.lower())
        key_pv_percent = find(k for k in keys if 'popular vote' in k.lower() and '%' in k)
        key_pv_count = find(k for k in keys if 'popular vote' in k.lower() and '%' not in k)
        key_delta_percent = find(k for k in keys if 'pp change' in k.lower())
        key_seats_dissolved = find(
            k for k in keys
            if re.match(r'seats\:.*(dissol.+)', k.lower()))
        key_seats_elected = find(
            k for k in keys
            if re.match(r'seats\:.*(' + str(year) + '|elected)', k.lower()))

        for party, row in df.iterrows():
            db.declare(
                "Party",
                party_name=party,
                colour=row.get("Colour"))
            db.declare(
                "PartyElection",
                pe_id=schema.make_pe_id(election_id, party_id=party),
                party_name=party,
                election_id=election_id,
                candidates=row.get(key_candidates),
                leader=row.get(key_leader),
                popular_vote=row.get(key_pv_count),
                popular_vote_percent=row.get(key_pv_percent),
                popular_vote_delta_percent=row.get(key_delta_percent),
                seats_dissolution=row.get(key_seats_dissolved),
                seats_elected=row.get(key_seats_elected))

        try:
            year = [a.text for a in info.select('td.noprint > a') if len(a.text) == 4][0]
            if year == '1867': break
        except IndexError:
            break

    return db

