import json
import os
import logging
from wikipedia import page as page_1, PageError

filename = 'pages_cache.json'
version_filename = 'cache_version.json'

pages = {}
version = -1


class empty:
    def __enter__(*args): logging.debug("empty.__enter__")
    def __exit__(*args): logging.debug("empty.__exit__")


lock = empty()


def set_lock(lock1):
    global lock
    logging.debug("set_lock({!r})".format(lock1))
    lock = lock1


def writeback_pages():
    try:
        open(filename, 'w').close()
        with open(filename, 'w') as f: json.dump(pages, f, indent=2)
    except KeyboardInterrupt:
        writeback_pages()


def writeback_version():
    try:
        open(version_filename, 'w').close()
        with open(version_filename, 'w') as f: json.dump(version, f)
    except KeyboardInterrupt:
        writeback_version()


def reload_version():
    global version
    try:
        with open(version_filename) as f:
            version = json.load(f)
    except FileNotFoundError:
        writeback_version()


def init():
    global pages

    logging.debug("init() len(keys)={}, version={}".format(len(pages), version))
    try:
        with open(filename, 'r') as f: pages = json.load(f)
    except FileNotFoundError:
        writeback_pages()

    reload_version()


def refresh():
    global version
    version0 = version
    reload_version()
    if version > version0: init()


def write():
    global version
    writeback_pages()
    version += 1
    writeback_version()


class Page:
    def __init__(self, html, links, title):
        self._html, self.links, self.title = html, links, title

    def html(self):
        return self._html


def page(title, auto_suggest=True):
    global pages
    assert isinstance(title, str)
    try:
        with lock:
            logging.debug("---{{{ lock acquired")
            title1 = json.dumps([title, auto_suggest])
            refresh()

            if pages.get(title1, None) != None:
                return Page(*pages[title1])

            logging.debug("cache miss {}".format(title1))
            page = page_1(title, auto_suggest=auto_suggest)
            pages[title1] = (page.html(), page.links, page.title)
            write()
            return Page(*pages[title1])
    finally:
        logging.debug("---}}} unlocked")

