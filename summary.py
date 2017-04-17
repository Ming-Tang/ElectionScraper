import pickle
import pprint
from collections import defaultdict, Counter

data = pickle.load(open('db.pickle', 'rb')).data
assert isinstance(data, dict)

elections = defaultdict(lambda: defaultdict(list))

for (k,), v in data["CandidateRidingElection"].items():
    election, riding, candidate, party = k.split(':')
    elections[election][riding].append(v.data)

for e, v in sorted(elections.items()):
    print("[{}]".format(e))

    def get_winner(riding):
        v1 = v[riding]
        if data["RidingElection"][(v1[0].get('re_id'),)].data.get('is_by_election'):
            return None

        winner = min(v1, key=lambda x: float("inf") if x.get("order") is None else x["order"])
        winner = dict(winner)
        winner.pop('re_id')
        winner.pop('cre_id')
        return winner

    winners = { riding: get_winner(riding) for riding in v.keys() }
    #print("\n".join(sorted(winners.keys())))

    parties = Counter((None if w is None else w['party_name']) for w in winners.values())
    pprint.pprint(parties)
    print(sum(v for v in parties.values() if v is not None))
    print("")

top2s = defaultdict(dict)
for (k,), v in data["CandidateRidingElection"].items():
    v = v.data
    if v.get("order") < 2:
        top2s[v.get("re_id")][v.get("order")] = (v.get("party_name"), v.get("votes_percent"))

raise SystemExit()
top2s = {k: tuple(j for i, j in sorted(v.items())) for k, v in top2s.items()}
pprint.pprint(top2s)
vs = [v for v in top2s.values() if len(v) > 1 and all(b is not None for a, b in v)]
pprint.pprint(sorted(vs, key=lambda x: (x[0][0], x[1][0])))
vs1 = [tuple(x for x, y in v) for v in vs]
pprint.pprint(Counter(vs1))
