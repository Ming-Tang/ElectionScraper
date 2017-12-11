import ujson as json
import os
import logging
import atexit
import time
import functools
import sys
from wikipedia import page as page_1, PageError

logger = logging.getLogger()
filename = 'output/pages_cache.json'
pages = None

if not os.path.exists('output/'):
    os.makedirs('output/')

def save_pages():
    try:
        logging.info("wiki.save_pages(): Starting... number of pages = {!r}".format(len(pages)))
        open(filename, 'w').close()  # clear file
        with open(filename, 'w') as f:
            json.dump(pages.copy(), f, indent=2, sort_keys=True)
        logging.info("wiki.save_pages(): Saved pages to {!r}".format(filename))
    except (BrokenPipeError, IOError):
        logging.exception('wiki.save_pages(): BrokenPipeError')

        time.sleep(0.5)
        logging.exception("wiki.save_pages(): Failed")
        save_pages()
    except KeyboardInterrupt:
        sys.stdout.flush()
        save_pages()
    except:
        time.sleep(0.5)
        logging.exception("wiki.save_pages(): Failed")
        save_pages()


def ensure_save_pages(f):
    @functools.wraps(f)
    def g(*a, **ka):
        try:
            return f()
        finally:
            save_pages()

    return g



def initialize_main(dict_object):
    global pages
    pages = dict_object

    try:
        if os.stat(filename).st_size == 0: os.unlink(filename)
        with open(filename, 'r') as f: pages.update(json.load(f))
        logger.info("wiki.initialize_main(): Loaded pages from {!r}".format(filename))
    except FileNotFoundError as e:
        logger.info("wiki.initialize_main(): Cache is not present: {!r}".format(filename))
    except json.JSONDecodeError:
        logger.exception("JSONDecodeError")
    finally:
        atexit.register(save_pages)


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

