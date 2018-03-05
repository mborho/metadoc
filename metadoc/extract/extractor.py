#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import asyncio
import logging
import lxml
import math
import time
import hashlib

from langdetect import detect
#from libextract.api import extract
from goose3 import Goose, Configuration

from .ner import EntityExtractor
from .html import HtmlMeta

logging.getLogger("requests").setLevel(logging.DEBUG)

class Extractor(object):
  """Entity recognition, pullquote extraction etc.
  """
  def __init__(self, html=None, title=" ", **kwargs):
    self.html = html or None
    self.title = title or None
    self.entities = []
    self.keywords = []
    self.names = []
    self.fulltext = None
    self.language = None
    self.description = None
    self.canonical_url = None
    self.image = None
    self.published_date = None
    self.modified_date = None
    self.scraped_date = None
    self.contenthash = None
    self.reading_time = None

    config = Configuration()
    config.enable_image_fetching = False
    self.goose = Goose(config=config)

  def detect_language(self):
    """Langdetect is non-deterministic, so to achieve a higher probability
    we attempt detection multiple times and only report success if we get identical results.
    """
    try:
        nondet_attempts = [detect(self.fulltext) for i in range(0,2)]
        is_unique = len(set(nondet_attempts)) == 1
        self.language = nondet_attempts[0] if is_unique else False
    except:
        pass

  def sanitize_html(self):
    # Lxml bails out on html w/ emojis
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
      "]+", flags=re.UNICODE)

    self.html = emoji_pattern.sub(r'', self.html)

  def extract_text(self):
    """Parse fulltext, do keyword extraction using the newspaper lib
    => newspaper.readthedocs.io
    """
    res = self.goose.extract(url=None, raw_html=self.html.encode("utf-8"))
    self.fulltext = res.cleaned_text
    """libextract_nodes = list(extract(self.html.encode("utf-8")))
    self.fulltext = libextract_nodes[0].text_content()"""

    entities = EntityExtractor(self.fulltext)
    entities.get_scored_entities() # Averaged Perceptron Tagger
    self.keywords = entities.get_keywords() # Above median?
    self.names = entities.get_names() # Filter top

  def extract_metadata(self):
    """Sniff for essential and additional metadata via
    either metatags and or json-ld"""

    title_breaks = [":", "-", "–", "/"]
    html_meta = HtmlMeta(self.html)
    html_meta.extract()

    self.authors = html_meta.jsonld.get("authors") \
      or html_meta.metatags.get("article:author") \
      or html_meta.metatags.get("author")

    self.title = html_meta.jsonld.get("headline") or html_meta.title
    self.description = html_meta.metatags.get("description")
    self.canonical_url = html_meta.links.get("canonical")
    self.image = html_meta.metatags.get("og:image") or html_meta.jsonld.get("thumbnailUrl")
    self.published_date = html_meta.published_date
    self.modified_date = html_meta.modified_date
    self.scraped_date = html_meta.scraped_date

  def get_contenthash(self):
    """Generate md5 hash over title and body copy in order to keep track
    of changes made to a text, do diffs if necessary
    """
    contentstring = (self.title + self.fulltext).encode("utf-8")
    self.contenthash = hashlib.md5(contentstring).hexdigest()
    return self.contenthash

  def get_reading_time(self):
    """Calculate average reading time in seconds"""
    if not self.fulltext: return None
    wordcount = len(self.fulltext.split())
    self.reading_time = math.floor(wordcount / 300 * 60)

  def get_all(self):
    start_time = time.time()
    self.sanitize_html()
    #logging.info("--- extraction module sanitize: %s seconds ---" % (time.time() - start_time))
    self.extract_text()
    #logging.info("--- extraction module extract text %s seconds ---" % (time.time() - start_time))
    self.extract_metadata()
    #logging.info("--- extraction module %s extract metadata ---" % (time.time() - start_time))
    self.detect_language()
    #logging.info("--- extraction module %s detect language seconds ---" % (time.time() - start_time))
    self.get_contenthash()
    #logging.info("--- extraction module %s contenthash ---" % (time.time() - start_time))
    self.get_reading_time()
    logging.info("--- extraction module %s seconds ---" % (time.time() - start_time))
    return

  async def async_get_all(self, loop):
    asyncio.set_event_loop(loop)
    return await loop.run_in_executor(None, self.get_all)
