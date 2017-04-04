import pickle
import pprint
from collections import defaultdict, Counter

def key(i):
    assert isinstance(i, tuple), i
    assert isinstance(i[1], dict), i[1]
    if 'acc' in (i[1].get('votes', '') or '').lower():
        return 1e100

    if (i[1].get('candidate_name') or '').lower() in ('swing', 'hold'):
        return -1

    if not (i[1].get('votes') or '').strip():
        return -1

    try:
        if '|' in i[1]['votes']:
            raise ValueError("TODO handle '|' in scraper: {!r}".format(i[1]['votes']))

        return float(i[1]['votes'].replace(',', '').replace('%', '').replace(' ', ''))
    except (ValueError, AttributeError) as ex:
        print(ex, i[1])
        return -1

data = pickle.load(open('db.pickle', 'rb')).data
assert isinstance(data, dict)

elections = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))

for (k,), v in data["CandidateRidingElection"].items():
    election, riding, candidate, party = k.split(':')
    elections[election][riding][party] = v.data

for e, v in sorted(elections.items()):
    print("[{}]".format(e))

    def get_winner(riding):
        v1 = v[riding]
        if data["RidingElection"][(list(v1.values())[0].get('re_id'),)].data.get('is_by_election'):
            return None

        values = [(key(x), x) for x in v1.items()]
        #print(values)
        set_keys = {k for k, v in values}
        if tuple(set_keys) == (-1,):
            return None

        winner = max(v1.items(), key=key)[1]
        winner = dict(winner)
        winner.pop('re_id')
        winner.pop('cre_id')
        return winner

    winners = {
        riding: get_winner(riding) for riding in v.keys()
    }
    #print("\n".join(sorted(winners.keys())))

    parties = Counter((None if w is None else w['party_name']) for w in winners.values())
    parties1 = defaultdict(lambda: 0)

    winners1 = {
        riding: #sorted(
            [(key((k, v)), k) for k, v in v[riding].items()]#,
            #key=lambda y: -1 if y is None else y
        #)
        for riding in v.keys()
    }
    def key1(i):
        if i[1] is None: return -1
        k = key(i)
        if k == -1: return 0
        else: return k

    if False:
        for k, v in sorted(winners.items(), key=key1, reverse=True):
            print("{:45}: {!r}".format(k, v))

    pprint.pprint(parties)

    if False:
        for riding, v1 in v.items():
            print("  - {} : {}".format(
                riding,
                winners[riding]["party_name"] if isinstance(winner, dict)
                else None))

            for p, v2 in v1.items():
                d1 = dict(v2)
                d1.pop('re_id')
                d1.pop('cre_id')
                d1.pop('party_name')
                print("    - {:40} {}".format(p, d1))

    print("")
