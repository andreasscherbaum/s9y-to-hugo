# s9y-to-hugo

Transform S9y blog into Hugo Markdown pages

## Description

This script migrates a [Serendipity](https://s9y.org/) blog into Markdown pages for the [Hugo](https://gohugo.io/) static blogging engine.

## Requirements

* Local Hugo installation
* S9y database export
* Images from the S9y blog
* Initialized Hugo blog
* Python packages from [requirements.txt](requirements.txt)

A Python [virtualenv](https://docs.python.org/3/library/venv.html) can be created using the `make virtualenv` [Makefile](Makefile) target.

## Preparation

[Initialize](https://gohugo.io/getting-started/quick-start/) a [new Hugo site](https://gohugo.io/commands/hugo_new_site/).

Use the new site as `targetdir` for the migration. Make sure a Hugo configfile (`hugo.yaml|json|toml)`) exists.

Make sure the [archetypes](https://gohugo.io/content-management/archetypes/) match what you expect for the new content. The migration will run `hugo new` ([documentation(https://gohugo.io/commands/hugo_new/)]) for each migrated blog posting.

Make sure the [taxonomies](https://gohugo.io/content-management/taxonomies/) are set. The migration script will use `categories`, `tags` and `authors`.

Make sure that `hugo new` creates an empty posting with all the details you need in there.

## Usage and commandline options

The script requires a couple of mandatory options, and has additional optional options which allow for moving the blog, or allow debugging the migration process.

```
./s9y-to-hugo.py <options>
```

Or:

```
. ./virtualenv/bin/activate && ./s9y-to-hugo.py <options>
```

### Commandline options

* `--help`: Shows a list of available options
* `-v`, `--verbose`: Show more verbose messages
* `-q`, `--quiet`: Only show error messages, no informational messages
* `--dbtype`: Select the type of source database (pg, mysql), currently only `pg` is supported
* `--dbhost`: Database host
* `--dbuser`: Database connection user
* `--dbpass`: Database connection password
* `--dbname`: Database name
* `--dbport`: Database port (defaults to PostgreSQL 5432)
* `--dbprefix`: Database table prefix (S9y allows hosting multiple blogs in the same database, [see documentation](https://docs.s9y.org/docs/users/using/configuration.html))
* `--webprefix`: The URL path prefix for the new blog, default to `/` (make sure your template supports subdirectories)
* `--oldwebprefix`: The URL path prefix of the old blog, default to `/` (migration to a new path is possible)
* `--targetdir`: The directory where your new Hugo blog resides locally
* `--imagedir`: The directory where images from the old blog are available for migration (must match path in blog postings)
* `--rewritefile`: The rewrite file which will have redirects from old to new URLs
* `--rewritetype`: Rewrite file type (webserver type), currently only `apache2` is supported
* `--use-bundles`: Use [Hugp Page Bundles](https://gohugo.io/content-management/page-bundles/) instead of a flat file structure
* `--remove-s9y-id`: Remove the S9y ID from the URL
* `--add-date-to-url`: Prefix the URL and the local file/directory with the ISO date of the posting
* `--ignore-post`: Do not migrate this posting, can be specified multiple times (use the relative URL from the S9y blog as parameter)
* `--ignore-picture-errors`: Ignore missing local picture errors in this posting (otherwise migration is aborted), can be specified multiple times
* `--use-utc`: Use UTC time instead of local time
* `--write-html`: Write a copy of the original HTML to a `.html` file
* `--archive-link`: Use this link for archive redirects (othewise `webprefix` is used)
* `--add-year-link-to-archive`: Adds redirects to a specific year (where applicable) for the archive links
* `--hugo-bin`: Use this binary as Hugo binary (otherwise auto-detected)

## Post Migration

After the migration, search the new blog postings for potential problems.

### TextReplaced

```
find <targetdir>/content/post/ -type f -name "*.md" -print0 | xargs -0 grep "TextReplaced"
```

Text for images was replaced, verify that everything looks alright.

If in doubt, use the `--write-html` option to create an additional file with the original HTML content.

### PictureMissing

A local picture is missing in the migrated blog posting. The `--ignore-picture-errors` option was used for this blog post.

### UnsupportedTags

Old and unsupported HTML flags have been found. S9y started off when HTML version 4 was still around. Very old blogs might contain unsupported HTML tags.

This affects old `<strike>` tags, which have been replaced with `<del>` during the migration.

It also affects `<s>` tags (recognized by the Markdown parser) and `<u>` tags (not recognized).

Consider using the `--write-html` option to write out the HTML into a file.

### CATEGORIESSKIPPED

One or more categories have not been migrated. This should only affect a root category from a category tree, but please check the details.

### s9yID

The migration tool writes the original database ID for the posting into the `s9yID` Frontmatter tag.

### OriginalLink

The migration tool writes the original blog posting URL into the `OriginalLink` Frontmatter tag.

### QuotesChanged

Some quotes have been changed, to remove unnecessary backslashes, or add necessary backslashes.

## Comments

Currently, comments are not migrated.

S9y supports a comment tree (comments answering comments). That's not something which can be easily shown in Markdown.

Patches welcome, if you have an idea how to solve this.
