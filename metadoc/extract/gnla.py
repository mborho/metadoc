# -*- coding: utf-8 -*-
import logging
import six
from google.cloud import language
from google.cloud.language import enums
from google.cloud.language import types


logger = logging.getLogger(__name__)


class EntityExtractor(object):

    def __init__(self, text, *, lang="en"):

        if isinstance(text, six.binary_type):
            text = text.decode('utf-8')

        self.text = text
        self.lang = lang

        # Instantiates a client
        self.client = language.LanguageServiceClient()
        self.keywords = []
        self.names = []

    def get_keywords(self):
        return list(set(self.keywords))

    def get_names(self):
        return list(set(self.names))

    def get_scored_entities(self):
        entities =  self._analyze_entities()

        # entity types from enums.Entity.Type
        entity_type = ('UNKNOWN', 'PERSON', 'LOCATION', 'ORGANIZATION',
                       'EVENT', 'WORK_OF_ART', 'CONSUMER_GOOD', 'OTHER')

        for entity in [e for e in entities if e.salience > 0.015]:
            if entity.name[0].isupper() or entity.metadata.get('wikipedia_url'):
                self.names.append(entity.name)

            logger.info(u'{:<14}: {} ({}) {} '.format(
                entity_type[entity.type], entity.name, entity.salience, entity.metadata.get('wikipedia_url', '-')))

    def _analyze_entities(self):
        """Detects entities in the text."""
        document = types.Document(
            content=self.text,
            language=self.lang,
            type=enums.Document.Type.PLAIN_TEXT)

        return self.client.analyze_entities(document).entities
