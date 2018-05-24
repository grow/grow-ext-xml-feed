# grow-ext-feed

Simple extension for importing grow documents from a feed url.

## Usage

### Initial setup

1. Create an `extensions.txt` file within your pod.
1. Add to the file: `git+git://github.com/grow/grow-ext-xml-feed`
1. Run `grow install`.
1. Add the following section to `podspec.yaml`:

```
ext:
- extensions.xml_feed.XmlFeedExtension
```
