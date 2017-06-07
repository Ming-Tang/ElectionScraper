from __future__ import division, print_function
from bs4 import BeautifulSoup
from bs4.element import Tag
from collections import defaultdict
import copy as _copy
import itertools as it
import re

__all__ = [
    'strip_citations', 'cleanup_text', 'Cell', 'Table', 'InfoBox',
    'Heading', 'DocumentOutline'
]

re_background = re.compile(r'background:\s*([^;]+);')

def strip_citations(elem, copy=False):
    """Strip citation links from element."""
    if copy: elem = _copy.copy(elem)

    for r in elem.select('.reference'):
        r.extract()

    for r in elem.find_all('sup'):
        r.extract()

    return elem



def cleanup_text(text):
    return text.strip().replace('\xa0', ' ').replace('\n', ' ')


class Cell:
    def __init__(self, elem):
        assert isinstance(elem, Tag)
        anchor = elem.a
        self.href, self.link_title = (
            (anchor.attrs.get('href'), anchor.attrs.get('title'))
            if anchor is not None else (None, None))

        def int1(x):
            try:
                return int(x)
            except:
                return int(re.sub(r'[^0-9]', "", x))

        elem = strip_citations(elem)
        self.elem, self.text, self.colspan, self.rowspan, self.is_header = (
            elem, cleanup_text(strip_citations(elem).text),
            int1(elem.attrs.get('colspan', '1')), int1(elem.attrs.get('rowspan', '1')),
            elem.name == 'th')
        self.colour = None
        style = elem.attrs.get('style')
        if style:
            match = re_background.match(style)
            if match:
                self.colour = match.groups(1)[0]

    def __repr__(self):
        return "|{!r}{}{}{}{}{}|".format(
            self.text,
            "({})".format(self.colour) if self.colour else "",
            repr((self.colspan, self.rowspan))
            if self.colspan > 1 or self.rowspan > 1 else "",
            ["", "*"][bool(self.is_header)],
            " -> " + self.href if self.href is not None else "",
            " : " + repr(self.link_title) if self.link_title is not None else "")


class Table:
    class _Headers:
        def __init__(self, table, transpose):
            assert isinstance(table, Table)
            assert isinstance(transpose, bool)
            self.table = table
            self.transpose = transpose

            i = 1
            n = table.n_cols if self.transpose else table.n_rows
            m = table.n_rows if self.transpose else table.n_cols
            while self._is_header(i) and i < n: i += 1
            self.header_count = i
            self.count = n

            def f7(seq):
                seen = set()
                return tuple([x for x in seq if not (x in seen or seen.add(x))])

            self.headers = [f7([self.index(i, j) for i in range(self.header_count)]) for j in range(m)]

        def _is_header(self, i):
            return self.table.is_header_col(i) if self.transpose else self.table.is_header_row(i)

        def index(self, i, j):
            return self.table._cells[j][i] if self.transpose else self.table._cells[i][j]

        def __repr__(self):
            return "<_Headers transpose={} header_count={} headers={}>".format(self.transpose, self.header_count, self.headers)


    def __init__(self, elem, header_all=False):
        assert isinstance(elem, Tag)
        assert elem.name == 'table'
        self.elem = elem
        self.header_check = [any, all][header_all]
        self.caption = elem.caption
        self._table_cells = [
            [td for td in tr.children if isinstance(td, Tag) and td.name in ('td', 'th')]
            for tr in elem.children if isinstance(tr, Tag)]

        self._build()

    def _build(self):
        cells = defaultdict(lambda: defaultdict(lambda: None))
        for y, row in enumerate(self._table_cells):
            x = 0
            for cell_tag in row:
                cell = Cell(cell_tag)
                while x in cells[y]: x += 1
                for y1 in range(y, y + cell.rowspan):
                    for i in range(x, x + cell.colspan):
                        assert cells[y1][i] is None
                        cells[y1][i] = cell
                x += cell.colspan

        self._cells = cells
        self.n_rows = max(cells.keys()) + 1
        self.n_cols = max(max(row.keys()) for row in cells.values()) + 1

        self.rows = Table._Headers(self, False)
        self.cols = Table._Headers(self, True)

    def to_dict(self, func=None):
        if func is None: func = lambda x: x
        return {k: {k1: func(v1) for k1, v1 in v.items()} for k, v in self._cells.items()}

    def is_header_row(self, r):
        return self.header_check(c is not None and c.is_header for c in self._cells[r].values())

    def is_header_col(self, r):
        return self.header_check(row[r] is not None and row[r].is_header for row in self._cells.values())

    def __repr__(self):
        return "<Table n_rows={}, n_cols={}>".format(self.n_rows, self.n_cols)

    def transpose(self, to_s=True, indexed=True, transpose=False, header=None):
        f = (lambda x: x.text if x is not None else None) if to_s else (lambda x: x)
        d = {}
        view = self.cols if transpose else self.rows
        if header is None:
            header = lambda h: ": ".join(y.text for y in h if y is not None)

        for j, h in enumerate(view.headers):
            data = []
            for i in range(view.header_count, view.count):
                data.append(f(view.index(i, j)))

            d[(j, header(h)) if indexed else header(h)] = data

        return d

    def __getitem__(self, p): return self._cells[p[0]][p[1]]


class InfoBox:
    def __init__(self, elem):
        assert isinstance(elem, Tag)
        assert elem.name == 'table'
        assert 'infobox' in set(elem.attrs.get('class'))
        tables = list(map(Table, elem.select('table')))

        self.tables = tables


class Heading:
    def __init__(self, elem, level):
        assert isinstance(elem, Tag)
        assert isinstance(level, int)
        self.elem = elem
        self.level = level
        try:
            self.title = elem.select('span.mw-headline')[0].text
            self.id = elem.select('span.mw-headline')[0].id
        except:
            self.title = self.elem.text

    def __repr__(self):
        return "|{} {}|".format("#" * self.level, self.title)


class DocumentOutline:
    def __init__(self, doc):
        assert isinstance(doc, BeautifulSoup)
        self.soup = doc

        root = doc
        root = doc.select('span.mw-headline')[0].parent.parent

        self.children = list(root.children)
        self.children_hashes = [self._h(c) for c in self.children]

        self.descendants_list = [
            (tuple(c.descendants) if isinstance(c, Tag) else ()) for c in self.children]
        self.descendants_hashes = [[self._h(d) for d in dl] for dl in self.descendants_list]

        heading_by_index = [None for i in range(len(self.children))]
        headings = {}
        cur_heading = None
        for i, child in enumerate(root.children):
            if isinstance(child, Tag) and child.name[0] == 'h':
                try:
                    level = int(child.name[1:])
                    assert level > 0

                    heading_by_index[i] = cur_heading
                    cur_heading = Heading(child, level)
                    headings[i] = cur_heading
                except ValueError:
                    pass
            else:
                heading_by_index[i] = cur_heading

        self.heading_by_index = heading_by_index
        self.headings = headings

    def get_children(self, i):
        assert i in self.headings
        level = self.headings[i].level
        for j in range(i + 1, len(self.children)):
            if j in self.headings and self.headings[j].level == level:
                break
            yield self.children[j]

    def get_heading(self, elem, level=None):
        assert elem is not None
        if level is not None: raise NotImplementedError()
        he = self._h(elem)
        res = [
            (i, child) for i, (child, hc) in enumerate(zip(self.children, self.children_hashes))
            if elem is child or (
                he == hc and elem == child) or (isinstance(child, Tag) and (
                elem in child or ( he in self.descendants_hashes[i] and elem in self.descendants_list[i])))
        ]
        if len(res) == 0: return None

        index, _ = res[0]
        #return index
        return self.heading_by_index[index]

    def _h(self, x):
        if isinstance(x, Tag):
            return self._hash_tag(x)
        else:
            return hash(x)

    def _hash_tag(self, x):
        return hash((x.name, len(x), hash(x.attrs.values())))

test_table = """
<table>
<tr>
  <td rowspan="2" colspan="2">0,0; 0,1;<br/> 1,0; 1,1</td>
  <td>0,2</td>
  <td>0,3</td>
  <td rowspan="3" colspan="2">0,4; 0,5;<br/> 1,4; 1,5;<br/> 2,4; 2,5</td>
  <td>0,6</td>
  <td>0,7</td>
</tr>
<tr>
  <td>1,2</td>
  <td>1,3</td>
  <td>1,6</td>
  <td>1,7</td>
  <td>1,8</td>
  <td>1,9</td>
</tr>
<tr>
  <td>2,0</td>
  <td>2,1</td>
  <td>2,2</td>
  <td>2,3</td>
  <td>2,6</td>
  <td>2,7</td>
</tr>
<tr>
  <td>3,0</td>
  <td>3,1</td>
  <td colspan="2">3,2; 3,3</td>
  <td rowspan="2">3,4;<br /> 4,4</td>
  <td colspan="2">3,5; 3,6</td>
  <td>3,7</td>
</tr>
<tr>
  <td>4,0</td>
  <td>4,1</td>
  <td>4,2</td>
  <td>4,3</td>
  <td>4,5</td>
  <td>4,6</td>
  <td>4,7</td>
  <td>4,8</td>
  <td>4,9</td>
</tr>
</table>
"""

#test = Table(BeautifulSoup(test_table, 'html.parser').table)
#print(test)
#pprint.pprint(test.to_dict())
#raise SystemExit()
