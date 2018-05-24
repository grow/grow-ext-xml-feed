"""Xml feed extension for importing xml feeds into Grow documents."""

from grow import extensions
from grow.documents import document
from grow.extensions import hooks


class XmlFeedPostRenderHook(hooks.PostRenderHook):
    """Handle the post-render hook."""

    def trigger(self, previous_result, doc, raw_content, *_args, **_kwargs):
        """Execute post-render modification."""
        return previous_result


class XmlFeedExtension(extensions.BaseExtension):
    """XML Feed import extension."""

    @property
    def available_hooks(self):
        """Returns the available hook classes."""
        return [XmlFeedPostRenderHook]
