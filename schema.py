from collections import defaultdict
import itertools as it

#TODO handle by-elections

standard_schema = {
    "Election": [
        ("election_id", "str", "id"),
        ("kind", "kind"),
        ("province", "province"),
        ("voter_turnout", "count"),
        ("voter_turnout_percent", "percent")
    ],

    "Riding": [
        ("riding_id", "str", "id"),
        ("riding_name", "str"),
        ("start_year", "year"),
        ("end_year", "year"),
        ("population", "count"),
        ("electors", "count"),
        ("area", "area"),
        ("population_year", "year"),
        ("electors_year", "year")
    ],

    "Party": [
        ("party_name", "str", "id")
    ],

    "Candidate": [
        ("candidate_name", "str", "id")
    ],

    # Relationship between riding and election
    "RidingElection": [
        ("re_id", "str", "id"),
        ("election_id", "str", "Election"),
        ("riding_id", "str", "Riding"),
        ("rejected_ballots", "count"),
        ("valid_ballots", "number"),
        ("turnout", "count"),
        ("turnout_percent", "percent"),
        ("expense_limit", "number"),
        ("is_by_election", "bool"),
        ("by_election_date", "str")
    ],

    # Relationship between party and election
    "PartyElection":  [
        ("pe_id", "str", "id"),
        ("party_name", "str", "Party"),
        ("election_id", "str", "Election")
    ],

    "CandidateRidingElection": [
        ("cre_id", "str", "id"),
        ("re_id", "str", "RidingElection"),
        ("candidate_name", "str", "Candidate"),
        ("party_name", "str", "Party"),
        ("votes", "count"),
        ("votes_percent", "percent"),
        ("delta_percent", "percent"),
        ("expenditures", "number")
    ]
}

key_id = "id"


def make_election_id(year):
    assert isinstance(year, int), year
    return "F{}".format(year)


def make_riding_id(riding_name, start_year=None, end_year=None):
    assert isinstance(riding_name, str)
    if not start_year and not end_year:
        return riding_name
    elif start_year is not None and end_year is not None:
        return "{}: {}-{}".format(riding_name, start_year, end_year)
    else:
        assert start_year is not None
        return "{}: {}".format(riding_name, start_year)


def make_re_id(election_id, riding_id):
    assert isinstance(election_id, str), election_id
    assert isinstance(riding_id, str), riding_id
    return "{}:{}".format(election_id, riding_id)


def make_cre_id(re_id, candidate_name, party_name):
    assert isinstance(re_id, str), re_id
    assert (candidate_name is None or isinstance(candidate_name, str)), candidate_name
    assert (party_name is None or isinstance(party_name, str)), party_name
    return "{}:{}:{}".format(re_id, candidate_name, party_name)


class Row:
    def __init__(self):
        self.items = []
        self.data = {}
        self.sources = {}

    def add(self, vals, source):
        assert isinstance(vals, dict)
        self.items.append((vals, source))
        self.data.update(vals)
        self.sources.update((k, source) for k in vals.keys())

    def __repr__(self):
        return "Row({})".format(self.data)


def _make_item(): return defaultdict(Row)


class Database:
    def __init__(self, schema):
        assert isinstance(schema, dict)
        self.data = defaultdict(_make_item)
        self.schema = schema

        def classify(t):
            i, c = t
            if len(c) == 2:
                return ""
            elif len(c) == 3:
                return c[2]
            else:
                assert False, "Invalid column: {!r}".format(c)

        def make_schema_group(s):
            s1 = list(enumerate(s))
            s1.sort(key=classify)
            return {(k or None): list(g) for k, g in it.groupby(s1, classify)}

        self.schema_groups = {
            k: make_schema_group(v) for k, v in schema.items()
        }

        for k, g in self.schema_groups.items():
            assert key_id in g, k
            assert len(g[key_id]) == 1, k

    def _add(self, schema_name, key, vals, source):
        self.data[schema_name][key].add(vals, source)

    def declare(self, schema_name, source=None, **kwargs):
        print("declare({!r}, source={!r}, **{!r})".format(schema_name, source, kwargs))
        assert schema_name in self.schema, "Schema not found: {}".format(schema_name)

        key, vals = self._validate(schema_name, kwargs)
        self._add(schema_name, key, vals, source=source)
        self._declare_relations(schema_name, source=source, kwargs=kwargs)

    def _declare_relations(self, schema_name, source, kwargs):
        schema_group = self.schema_groups[schema_name]
        for gk, gl in schema_group.items():
            if gk in self.schema:
                for i, (gkey, gtype, grel) in gl:
                    #assert gkey in kwargs, "{}: _declare_relations: Missing mandatory field: {!r} not in {!r}".format(schema_name, gkey, kwargs)
                    if gkey not in kwargs: continue

                    ref_id_value = kwargs[gkey]
                    assert grel == gk
                    declare_keys = self.schema_groups[grel][key_id]
                    #print("_declare_relations {}: {}:{}".format(schema_name, gkey, grel))
                    #print("  declare_keys = {}".format(declare_keys))
                    #print("    declare({}, **{})".format(grel, {ref_id_key: ref_id_value}))
                    assert len(declare_keys[0][1]) == 3, declare_keys[0][1]
                    [(_, (ref_id_key, _, _))] = declare_keys
                    self.declare(grel, source=source, **{ref_id_key: ref_id_value})

    def _validate(self, schema_name, kwargs):
        schema_group = self.schema_groups[schema_name]
        key = []
        remaining = set(kwargs.keys())
        for gk, gl in schema_group.items():
            if gk == key_id:
                for i, k in gl:
                    assert k[0] in kwargs, "ID {}.{} is required but not found.".format(
                        schema_name, k[0])
                    key.append((i, kwargs[k[0]]))

            for i, k in gl:
                if k in remaining:
                    remaining.remove(k)

        assert remaining, "Invalid columns for {!r}: {!r}".format(schema_name, remaining)
        return tuple(v for i, v in sorted(key)), kwargs


def make_standard_database():
    return Database(standard_schema)


if __name__ == "__main__":
    import pprint
    db = Database(standard_schema)
    db.declare("Riding", riding_id="R1", riding_name="X")
    db.declare("RidingElection", re_id="RE1", riding_id="R2", election_id="E1")
    pprint.pprint(dict(db.data))
