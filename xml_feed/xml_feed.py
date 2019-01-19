"""Xml feed extension for importing xml feeds into Grow documents."""

import collections
import requests
import textwrap
import yaml
from bs4 import BeautifulSoup as BS
from datetime import datetime
from dateutil.parser import parse
from protorpc import messages
from xml.etree import ElementTree as ET
from grow import extensions
from grow.common import structures
from grow.common import utils
from grow.common import yaml_utils
from grow.extensions import hooks

CONTENT_KEYS = structures.AttributeDict({
    'title': 'title',
    'description': 'description',
    'link': 'link',
    'published': 'pubDate',
    'content_encoded': '{http://purl.org/rss/1.0/modules/content/}encoded',
})

CONFIG_FIELDS_TO_REMOVE = [
    'field_aliases',
]

class Article(object):
    """Article details from the field."""

    def __init__(self):
        self.title = None
        self.description = None
        self.image = None
        self.link = None
        self.content = None
        self.fields = {}


class Options(object):
    def __init__(self, config):
        self.field_aliases = {}
        self._parse_config(config)

    def _parse_config(self, config):
        if 'field_aliases' in config:
            for alias, field in config['field_aliases'].iteritems():
                self.alias_field(field, alias)

    def alias_field(self, field, alias):
        if field not in self.field_aliases.keys():
            self.field_aliases[field] = []
        self.field_aliases[field] = self.field_aliases[field] + [alias]

    def get_aliases(self, field):
        if field in self.field_aliases.keys():
            return self.field_aliases[field]
        else:
            return []

    def get_all_aliases(self):
        all_aliases = []
        for aliases in self.field_aliases.values():
            all_aliases = all_aliases + aliases
        return all_aliases


class XmlFeedPreprocessHook(hooks.PreprocessHook):
    """Handle the preprocess hook."""

    KIND = 'xml_feed'

    class Config(messages.Message):
        """Config for Xml feed preprocessing."""
        url = messages.StringField(1)
        collection = messages.StringField(2)
        field_aliases = messages.BytesField(3)

    @staticmethod
    def _download_feed(url):
        return requests.get(url).content

    @classmethod
    def _parse_articles(cls, raw_feed, options):
        root = ET.fromstring(raw_feed)

        if root.tag == 'rss':
            for article in cls._parse_articles_rss(root, options):
                yield article
        else:
            raise ValueError('Only supports rss feeds currently.')

    @staticmethod
    def _parse_articles_rss(root, options):
        used_titles = set()

        for item in root.findall('./channel/item'):
            article = Article()

            for child in item:
                if child.tag == CONTENT_KEYS.title:
                    article.title = child.text.encode('utf8')
                elif child.tag == CONTENT_KEYS.description:
                    article.description = child.text.encode('utf8')
                    article.content = child.text.encode('utf8')
                elif child.tag == CONTENT_KEYS.link:
                    article.link = child.text.encode('utf8')
                elif child.tag == CONTENT_KEYS.published:
                    raw_date = child.text.encode('utf8')
                    article.published = parse(raw_date)
                elif child.tag == CONTENT_KEYS.content_encoded:
                    article.content = child.text.encode('utf8')
                elif child.text:
                    article.fields[child.tag] = child.text.encode('utf8')

                # Handle aliases, in addition to established defaults
                # Handled after defaults to allow for overrides
                for alias in options.get_aliases(child.tag):
                    article.fields[alias] = child.text.encode('utf8')

            if article.title:
                slug = utils.slugify(article.title)

                if slug in used_titles:
                    index = 1
                    alt_slug = slug
                    while alt_slug in used_titles:
                        alt_slug = '{}-{}'.format(slug, index)
                        index = index + 1
                    slug = alt_slug

                article.slug = slug

            if article.content:
                soup_article_content = BS(article.content, "html.parser")
                soup_article_image = soup_article_content.find('img')

                if soup_article_image:
                    article.image = soup_article_image['src']

            yield article

    def trigger(self, previous_result, config, names, tags, run_all, rate_limit,
                *_args, **_kwargs):
        """Execute preprocessing."""
        if not config['collection'].endswith('/'):
            config['collection'] = '{}/'.format(config['collection'])

        options = Options(config)

        sanitized_config = dict(
            (k,v) for k,v in config.iteritems()
            if k not in CONFIG_FIELDS_TO_REMOVE)
        config_message = self.parse_config(sanitized_config)

        raw_feed = self._download_feed(config_message.url)
        for article in self._parse_articles(raw_feed, options):
            pod_path = '{}{}.html'.format(config_message.collection, article.slug)
            data = collections.OrderedDict()

            data['$title'] = article.title
            data['$description'] = article.description
            data['image'] = article.image
            data['published'] = article.published
            data['link'] = article.link

            # Aliases handled after defaults to allow for overrides
            for alias in options.get_all_aliases():
                data[alias] = (
                    article.fields[alias] if alias in article.fields else None)

            raw_front_matter = yaml.dump(
                data, Dumper=yaml_utils.PlainTextYamlDumper,
                default_flow_style=False, allow_unicode=True, width=800)

            raw_content = textwrap.dedent(
                """\
                {}
                ---
                {}
                """).format(raw_front_matter, article.content)

            self.pod.logger.info('Saving {}'.format(pod_path))
            self.pod.write_file(pod_path, raw_content)

        return previous_result


class XmlFeedExtension(extensions.BaseExtension):
    """XML Feed import extension."""

    @property
    def available_hooks(self):
        """Returns the available hook classes."""
        return [XmlFeedPreprocessHook]
