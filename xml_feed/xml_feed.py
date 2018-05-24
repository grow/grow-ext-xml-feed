"""Xml feed extension for importing xml feeds into Grow documents."""

from protorpc import messages
from grow import extensions
from grow.documents import document
from grow.extensions import hooks


class XmlFeedPreprocessHook(hooks.PreprocessHook):
    """Handle the preprocess hook."""

    KIND = 'xml_feed'

    class Config(messages.Message):
        """Config for Xml feed preprocessing."""
        url = messages.StringField(1)
        collection = messages.StringField(2)

    def trigger(self, previous_result, config, names, tags, run_all, rate_limit,
                *_args, **_kwargs):
        """Execute preprocessing."""
        config = self.parse_config(config)
        print 'Triggered xml feed preprocessing:'
        print 'URL: {}'.format(config.url)
        print 'Collection: {}'.format(config.collection)
        return previous_result


class XmlFeedExtension(extensions.BaseExtension):
    """XML Feed import extension."""

    @property
    def available_hooks(self):
        """Returns the available hook classes."""
        return [XmlFeedPreprocessHook]
