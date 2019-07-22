"""Xml feed extension for importing xml feeds into Grow documents."""

import collections
import datetime
import textwrap
import time
import re
import yaml
import feedparser
import slugify
from bs4 import BeautifulSoup as BS
from datetime import datetime
from dateutil.parser import parse
from protorpc import messages
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
        file_format = messages.StringField(4)
        slugify = messages.BooleanField(5, default=False)

    @staticmethod
    def _cleanup_slug(value):
        # Remove multiple dashes.
        value = re.sub(r'[-]{2,}', '-', value)
        # Remove multiple periods.
        value = re.sub(r'[\.]{2,}', '.', value)
        # Remove trailing period.
        value = re.sub(r'[\.-]$', '', value)
        return value

    @staticmethod
    def _cleanup_yaml(value):
        if ':' in value:
            return '"{}"'.format(value)
        return value

    @staticmethod
    def _parse_articles_atom(feed, options, slugify):
        used_titles = set()

        for entry in feed.entries:
            article = Article()
            article.title = entry.title.encode('utf-8')
            if entry.summary != entry.content[0].value:
                article.description = entry.summary.encode('utf-8')
            article.content = entry.content[0].value.encode('utf-8')
            article.link = entry.link
            article.published = entry.published_parsed

            if article.title:
                if slugify:
                    slug = slugify(article.title)
                else:
                    slug = self._cleanup_slug(utils.slugify(article.title))

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
                article.content = soup_article_content.prettify().encode('utf-8')
                soup_article_image = soup_article_content.find('img')

                if soup_article_image:
                    article.image = soup_article_image['src']

            if not article.description:
                article.description = article.title

            yield article

    @staticmethod
    def _parse_articles_rss(feed, options, slugify):
        used_titles = set()

        for entry in feed.entries:
            article = Article()
            article.title = entry.title.encode('utf-8')
            # article.description = entry.summary.encode('utf-8')
            article.content = entry.summary.encode('utf-8')
            article.link = entry.link
            article.published = entry.published_parsed

            if article.title:
                if slugify:
                    slug = slugify(article.title)
                else:
                    slug = self._cleanup_slug(utils.slugify(article.title))

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
                # article.content = soup_article_content.get_text().encode('utf-8')
                article.content = soup_article_content.prettify().encode('utf-8')
                soup_article_image = soup_article_content.find('img')

                if soup_article_image:
                    article.image = soup_article_image['src']

            if not article.description:
                article.description = article.title

            yield article

    @classmethod
    def _parse_feed(cls, feed_url, options, slugify):
        feed = feedparser.parse(feed_url)

        if feed.version == 'atom10':
            for article in cls._parse_articles_atom(feed, options):
                yield article
        elif feed.version == 'rss20':
            for article in cls._parse_articles_rss(feed, options):
                yield article
        else:
            raise ValueError('Feed importer only supports rss and atom feeds.')

    def trigger(self, previous_result, config, names, tags, run_all, rate_limit,
                *_args, **_kwargs):
        """Execute preprocessing."""
        if not config['collection'].endswith('/'):
            config['collection'] = '{}/'.format(config['collection'])
        options = Options(config)

        # Can't handle the custom parts of the config.
        sanitized_config = dict(
            (k,v) for k,v in config.iteritems() if k not in CONFIG_FIELDS_TO_REMOVE)
        config = self.parse_config(sanitized_config)

        for article in self._parse_feed(config.url, options, config.slugify):
            article_datetime = datetime.fromtimestamp(time.mktime(article.published))
            slug = self._cleanup_slug(article.slug)

            file_format = config.file_format or '{year}/{slug}.html'
            file_name = file_format.format(
                year=article_datetime.year, month=article_datetime.month,
                day=article_datetime.day, slug=slug)
            pod_path = '{}{}'.format(config.collection, file_name)

            data = collections.OrderedDict()
            data['$title'] = article.title
            data['$description'] = article.description
            data['image'] = article.image
            data['published'] = article_datetime
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
