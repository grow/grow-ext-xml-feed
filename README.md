# grow-ext-feed

Simple extension for importing grow documents from a feed url.

Currently only supports RSS feeds.

## Usage

### Initial setup

1. Create an `extensions.txt` file within your pod.
1. Add to the file: `git+git://github.com/grow/grow-ext-xml-feed`
1. Run `grow install`.
1. Add the following sections to `podspec.yaml`:

```
ext:
- extensions.xml_feed.XmlFeedExtension
```

```
preprocessors:
- name: my_feed
  kind: xml_feed
  autorun: false
  url: https://www.blog.google/rss/
  collection: /content/feed/
  tags:
  - feed
```

### Importing feed

To run the feed import run `grow preprocess -p my_feed`.

Alternatively you can use tags in the preprocessor configuration and run all of
the `feed` tagged preprocessors at the same time using `grow preprocess -t feed`.
