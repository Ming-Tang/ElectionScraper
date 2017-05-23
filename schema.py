from collections import defaultdict
import itertools as it

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
        ("party_name", "str", "id"),
        ("colour", "str")
    ],

    "Candidate": [
        ("candidate_name", "str", "id")
    ],

    "ProvincialBreakdown": [
        ("pb_id", "str", "id"),
        ("election_id", "str", "Election"),
        ("province", "province"),
        ("party_name", "str", "Party"),
        ("popular_vote_percent", "percent"),
        ("seats", "count")
    ],

    # Relationship between riding and election
    "RidingElection": [
        ("re_id", "str", "id"),
        ("election_id", "str", "Election"),
        ("riding_id", "str", "Riding"),
        ("rejected_ballot", "count"),
        ("rejected_ballot_percent", "percent"),
        ("total_valid_vote", "count"),
        ("voter_turnout", "count"),
        ("voter_turnout_percent", "percent"),
        ("expense_limit", "number"),
        ("is_by_election", "bool"),
        ("by_election_date", "str")
    ],

    # Relationship between party and election
    "PartyElection":  [
        ("pe_id", "str", "id"),
        ("party_name", "str", "Party"),
        ("election_id", "str", "Election"),
        ("candidates", "count"),
        ("leader", "str"),
        ("popular_vote", "count"),
        ("popular_vote_percent", "percent"),
        ("popular_vote_delta_percent", "delta_percent"),
        ("seats_dissolution", "count"),
        ("seats_elected", "count")
    ],

    "CandidateRidingElection": [
        ("cre_id", "str", "id"),
        ("re_id", "str", "RidingElection"),
        ("election_id", "str", "Election"),
        ("riding_id", "str", "Riding"),
        ("order", "order"),
        ("candidate_name", "str", "Candidate"),
        ("party_name", "str", "Party"),
        ("votes", "count"),
        ("votes_percent", "percent"),
        ("delta_percent", "delta_percent"),
        ("expenditures", "number"),
        ("elected", "bool")
    ]
}


key_id = "id"


def _make_item():
    """For pickle backward compatibility."""
    raise NotImplementedError()


def make_pe_id(election_id, party_id):
    assert isinstance(election_id, str), election_id
    assert isinstance(party_id, str), party_id
    return "{}:{}".format(election_id, party_id)


def make_election_id(year):
    assert isinstance(year, int), year
    return "F{}".format(year)


def make_pb_id(election_id, province, party_id):
    assert isinstance(election_id, str), election_id
    assert isinstance(province, str), province
    assert isinstance(party_id, str), party_id
    return "{}:{}:{}".format(election_id, province, party_id)

def make_riding_id(riding_name, start_year=None, end_year=None):
    assert isinstance(riding_name, str)
    if not start_year and not end_year:
        return riding_name
    elif start_year is not None and end_year is not None:
        return "{}: {}-{}".format(riding_name, start_year, end_year)
    else:
        assert start_year is not None
        return "{}: {}".format(riding_name, start_year)


# TODO by-election ids
def make_re_id(election_id, riding_id):
    assert isinstance(election_id, str), election_id
    assert isinstance(riding_id, str), riding_id
    return "{}:{}".format(election_id, riding_id)


def make_cre_id(re_id, candidate_name, party_name):
    assert isinstance(re_id, str), re_id
    assert (candidate_name is None or isinstance(candidate_name, str)), candidate_name
    assert (party_name is None or isinstance(party_name, str)), party_name
    return "{}:{}:{}".format(re_id, candidate_name, party_name)


report_exception = False

def _convert_number_func(func):
    def is_none(x):
        x = x.lower()
        return 'n/a' in x or 'vacant' in x

    def is_acclaimed(x):
        return 'acc' in x.lower()

    def clean_number(x):
        chars = ' ,%b$\u2013\u2014-'
        for c in chars: x = x.replace(c, '')
        x = x.replace('pp', '')
        return x

    def convert_func(x):
        if x is None:
            return None

        x = str(x)

        if is_none(x):
            return None

        if is_acclaimed(x):
            return None # "acclaimed"

        try:
            is_negative = len(x) and x[0] == '-'
            x1 = clean_number(x)
            if not x1:
                return None
            return [1, -1][is_negative] * func(x1)
        except ValueError as ex:
            if report_exception:
                return '!! ' + repr(x) + " " + repr(ex)
            else:
                return None

    return convert_func


conversions = {
    "bool": bool,
    "str": str,
    "province": str,
    "year": str,
    "order": int,
    "percent": _convert_number_func(float),
    "delta_percent": _convert_number_func(float),
    "number": _convert_number_func(float),
    "count": _convert_number_func(lambda x: int(x.replace('.', ''))),
}


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

    def update(self, row1):
        assert isinstance(row1, Row)
        for vals1, source1 in row1.items:
            self.add(vals1, source1)

    def __bool__(self):
        return bool(self.items)

    def _as_tuple(self):
        return (self.items, self.data, self.sources)

    def __eq__(self, other):
        return type(self) is type(other) and self._as_tuple() == other._as_tuple()

    def __hash__(self):
        raise TypeError("unhashable type: '{}'".format(type(self)))


class Database:
    def __init__(self, schema):
        assert isinstance(schema, dict)

        self.schema = schema
        self.data = {k: defaultdict(Row) for k in self.schema.keys()}

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

    def _check_row(self, row_schema, vals):
        return {
            k: None if v is None else conversions[row_schema.get(k, "str")](v)
            for k, v in vals.items()
        }

    def _add(self, schema_name, key, vals, source):
        schema = dict((tup[0], tup[1]) for tup in self.schema[schema_name])
        vals1 = self._check_row(schema, vals)
        self.data[schema_name][key].add(vals1, source)

    def declare(self, schema_name, source=None, **kwargs):
        #print("declare({!r}, source={!r}, **{!r})".format(schema_name, source, kwargs))
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

    def update_from(self, db):
        assert self.schema == db.schema
        assert self.schema_groups == db.schema_groups
        for s, d1 in db.data.items():
            d = self.data[s]
            for key, row in d1.items():
                if key in d:
                    d[key].update(row)
                else:
                    d[key] = row

    def _as_tuple(self):
        return (self.schema, self.schema_groups, self.data)

    def __eq__(self, other):
        return type(self) is type(other) and self._as_tuple() == other._as_tuple()

    def __hash__(self):
        raise TypeError("unhashable type: '{}'".format(type(self)))

def make_standard_database():
    return Database(standard_schema)

