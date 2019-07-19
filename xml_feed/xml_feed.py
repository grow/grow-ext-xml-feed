"""Xml feed extension for importing xml feeds into Grow documents."""

import datetime
import textwrap
import time
import feedparser
import tomd
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

    @staticmethod
    def _cleanup_yaml(value):
        if ':' in value:
            return '"{}"'.format(value)
        return value

    @staticmethod
    def _parse_articles_atom(feed):
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
                article.content = soup_article_content.prettify().encode('utf-8')
                soup_article_image = soup_article_content.find('img')

                if soup_article_image:
                    article.image = soup_article_image['src']

            if not article.description:
                article.description = article.title

            yield article

    @staticmethod
    def _parse_articles_rss(feed):
        used_titles = set()

        for entry in feed.entries:
            article = Article()
            article.title = entry.title.encode('utf-8')
            # article.description = entry.summary.encode('utf-8')
            article.content = entry.summary.encode('utf-8')
            article.link = entry.link
            article.published = entry.published_parsed

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
                # article.content = soup_article_content.get_text().encode('utf-8')
                article.content = soup_article_content.prettify().encode('utf-8')
                # article.content = tomd.convert(soup_article_content.prettify().encode('utf-8'))
                soup_article_image = soup_article_content.find('img')

                if soup_article_image:
                    article.image = soup_article_image['src']

            if not article.description:
                article.description = article.title

            yield article

    @classmethod
    def _parse_feed(cls, feed_url):
        feed = feedparser.parse(feed_url)

        print feed.version

        if feed.version == 'atom10':
            for article in cls._parse_articles_atom(feed):
                yield article
        elif feed.version == 'rss20':
            for article in cls._parse_articles_rss(feed):
                yield article
        else:
            raise ValueError('Feed importer only supports rss and atom feeds.')

    def trigger(self, previous_result, config, names, tags, run_all, rate_limit,
                *_args, **_kwargs):
        """Execute preprocessing."""
        if not config['collection'].endswith('/'):
            config['collection'] = '{}/'.format(config['collection'])

        config = self.parse_config(config)

        for article in self._parse_feed(config.url):
            article_datetime = datetime.fromtimestamp(time.mktime(article.published))
            pod_path = '{}/md/{}/{}.fm'.format(config.collection, article_datetime.year, article.slug)
            pod_path_md = '{}/md/{}/{}.md'.format(config.collection, article_datetime.year, article.slug)

            raw_front_matter = textwrap.dedent(
                """\
                $title: {}
                $description: {}
                $date: {}
                image: {}
                """.rstrip()).format(
                    self._cleanup_yaml(article.title),
                    self._cleanup_yaml(article.description),
                    article_datetime.strftime('%Y-%m-%d'),
                    article.image)

            raw_content = textwrap.dedent(
                """\
                {}
                ---
                """).format(raw_front_matter)

            self.pod.logger.info('Saving {}'.format(pod_path))
            self.pod.write_file(pod_path, raw_content)
            self.pod.write_file(pod_path_md, article.content)

        return previous_result


class XmlFeedExtension(extensions.BaseExtension):
    """XML Feed import extension."""

    @property
    def available_hooks(self):
        """Returns the available hook classes."""
        return [XmlFeedPreprocessHook]
