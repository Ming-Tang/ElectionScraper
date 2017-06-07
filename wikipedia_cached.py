import json
import os
import logging
import atexit
from wikipedia import page as page_1, PageError

logger = logging.getLogger()
filename = 'pages_cache.json'
pages = None

def save_pages():
    try:
        open(filename, 'w').close()  # clear file
        with open(filename, 'w') as f: json.dump(pages.copy(), f, indent=2, sort_keys=True)
        logging.info("wiki.save_pages: Saved pages to {!r}".format(filename))
    except KeyboardInterrupt:
        save_pages()


def initialize_main(dict_object):
    global pages
    pages = dict_object

    try:
        with open(filename, 'r') as f: pages.update(json.load(f))
        logger.info("wiki.initialize_main(): Loaded pages from {!r}".format(filename))
        atexit.register(save_pages)
    except FileNotFoundError:
        logger.info("wiki.initialize_main(): File not found.")
    except json.JSONDecodeError:
        logger.exception("JSONDecodeError")


def initialize_sub(dict_object):
    global pages
    pages = dict_object
    logger.debug("wiki.initialize_sub() called.")


class Page:
    def __init__(self, html, links, title):
        self._html, self.links, self.title = html, links, title

    def html(self):
        return self._html


def page(title, auto_suggest=True):
    global pages
    assert pages is not None, "Not initialized."
    assert isinstance(title, str)
    title1 = json.dumps([title, auto_suggest])

    if pages.get(title1, None) != None:
        return Page(*pages[title1])

    logging.debug("wiki.page: Cache miss: {!r}".format(title))
    page = page_1(title, auto_suggest=auto_suggest)
    pages[title1] = (page.html(), page.links, page.title)
    return Page(*pages[title1])

