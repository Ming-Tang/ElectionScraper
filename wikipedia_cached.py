import shelve
from wikipedia import page as page_1

filename = 'pages_cache.shelve'
pages = shelve.open(filename)

for k in pages.keys(): test = pages[k]

class Page:
    def __init__(self, html, links):
        self._html, self.links = html, links

    def html(self):
        return self._html


def page(title, auto_suggest=True):
    if title in pages:
        return Page(*pages[title])

    page = page_1(title, auto_suggest=auto_suggest)
    pages[title] = (page.html(), page.links)
    return Page(*pages[title])