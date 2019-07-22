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

### Custom fields

If custom fields are necessary they can be specified as part of the preprocessor
config. For instance if you wanted to add a creator field `<dc:creator>` and a
`<foo>` field with custom names, you would update the previous example as
follows:

```
preprocessors:
- name: my_feed
  kind: xml_feed
  autorun: false
  url: https://www.blog.google/rss/
  collection: /content/feed/
  custom_field_names:
    creator: '{http://purl.org/dc/elements/1.1/}creator'
    custom_foo_field_name: 'foo'
  tags:
  - feed
```

In the resulting HTML files the `foo` and `dc:creator` information would be
stored under `custom_foo_field_name` and `creator` keys.

These custom field names can be used to alias or override default field names
and map a value to multiple aliases.  

### Custom file format

By default the xml extension will write the blog posts in directory by year,
this can be changed by providing a custom format using any of the following
variables:

```
day: Day of the article posting.
month: Month of the article posting.
slug: Slug of the article title.
year: Year of the article posting.
ext: File extension (html or md)
```

For example:

```
preprocessors:
- name: my_feed
  kind: xml_feed
  url: https://www.blog.google/rss/
  collection: /content/feed/
  file_format: "{year}/{month}/{day}/{slug}.{ext}"
```

The above config would write the imported documents to `/content/feed/2019/7/18/article-title.html`.

### Import as markdown

The preprocessor can also convert the content of the feed from html into markdown.

```
preprocessors:
- name: my_feed
  kind: xml_feed
  url: https://www.blog.google/rss/
  collection: /content/feed/
  convert_to_markdown: true
```

### Importing feed

To run the feed import run `grow preprocess -p my_feed`.

Alternatively you can use tags in the preprocessor configuration and run all of
the `feed` tagged preprocessors at the same time using `grow preprocess -t feed`.
