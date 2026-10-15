---
title: Dynamic sites
description: What differs on a runtime-rendered site: SEO plugins, database references, cache invalidation, and archives.
evidence_level: normative
support_level: fully_supported
applies_to: [website-optimizer]
references:
  - https://developer.wordpress.org/apis/wp-cli/
  - https://www.yoast.com/wordpress/plugins/seo/
last_verified: 2026-10-15
review_due: 2027-01-15
---

# Dynamic sites

Everything in `seo-core.md`, `indexing.md` and `structured-data.md` applies
here unchanged. This file holds only what differs because the site is **rendered
at request time from a database**.

**If the site is a generator, stop reading — `static-sites.md` is the correct
file and most of this does not apply.**

## The renderer decides what a crawler sees

This is the defining difference. Content that is injected by JavaScript after
load may or may not be seen by a crawler, depending on whether it renders.

- Server-side rendering keeps the page complete in the HTML. Client-side
  rendering depends on the crawler executing JavaScript.
- Audit the **rendered** page, not the served HTML skeleton. The difference is
  where most dynamic-site SEO defects hide.
- This is why live crawling exists in this skill: a static-output audit cannot
  see a runtime-rendered site at all. See `scripts/README.md`.

## SEO plugins

A plugin (Yoast, Rank Math, or equivalent) is usually the source of titles,
descriptions, canonicals, and structured data.

- **Audit what the plugin emits**, not what it reports in its own admin screen.
  The admin screen and the rendered head can disagree after a filter changes one.
- Do not let the plugin and a theme both emit the same tag. Two `<title>`
  elements, or a plugin canonical overridden by a theme canonical, produces
  contradictory signals.
- The plugin's database rows are not configuration. Editing them by hand means
  the next plugin update overwrites them. Change behaviour through filters or
  through the plugin's own settings.
- Keep its generated sitemap from including taxonomies, attachments, and search
  results.

## Database references after a move

Every internal URL lives in the database, in posts, in options, and in the
plugin-specific tables. A migration that changes the domain changes all of them.

```bash
wp db export ~/db-backups/pre-migration-$(date +%F).sql

wp search-replace "https://www.example.com" "https://old.example.com" --all-tables
wp search-replace "http://www.example.com"  "https://old.example.com" --all-tables
wp search-replace "https://example.com"     "https://old.example.com" --all-tables
wp search-replace "http://example.com"      "https://old.example.com" --all-tables
```

**Variants that are missed:**

```bash
# JSON-escaped URLs left behind by plugins in their own option tables
wp search-replace "https:\/\/www.example.com" "https:\/\/old.example.com" --all-tables
wp search-replace "https:\/\/example.com"    "https:\/\/old.example.com" --all-tables

# Unqualified references
wp search-replace "www.example.com" "old.example.com" --all-tables
```

- **Back up before any of this.** `--all-tables` is not reversible.
- Run against a restored copy first when the site has plugin option tables.
- Search for the old domain in the database afterwards; a residual reference is
  a live bug.

## Cache invalidation

A cache that is not invalidated after a content change serves stale metadata,
which is worse than no metadata because the change appears to have worked.

- Purge page cache, CDN, and any object cache.
- Update the last-modified timestamps so a CDN revalidates.
- After a domain change, purge **everything**. A cached page with the old
  canonical keeps serving it long after the database is correct.

## Archives and secondary installations

An old site kept online for reference:

```bash
wp option update blog_public 0     # noindex
wp cache flush
```

- `blog_public = 0` **must** be unset on the live site. Forgetting it is the
  classic failure mode: the site works, the content is right, and nothing is
  indexed anywhere.
- Verify: the served HTML must not contain `noindex`, and
  `site:example.com` must return results.
- The archive should not redirect. Its purpose is to remain a distinct,
  non-competing address (`redirects.md`).

## Custom post types and legacy URLs

A dynamic site has URL surfaces a generator does not: post types, paginated
archives, date archives, attachment pages, feeds, and search results.

- Decide explicitly which are indexable. Paginated archives are indexable;
  search results and feeds are not.
- After a migration, map the whole URL inventory, including the post-type
  prefixes the old site used (`/portfolio/items/<slug>/` →
  `/projects/<slug>/`).
- Attachment pages are usually thin duplicates of their parent; either
  canonicalise them or noindex them.

## Checklist

- [ ] Audited as rendered output, not as served HTML
- [ ] Plugin, theme, and code emit exactly one title and one canonical
- [ ] Plugin-generated sitemap excludes taxonomies, attachments, search
- [ ] Database backed up before any `search-replace`, including JSON-escaped
      variants and unqualified references
- [ ] Cache purged after every metadata or domain change
- [ ] `blog_public` is `1` on the live site and `0` on any archive
- [ ] Custom post types, date archives, and attachment pages have explicit
      indexability decisions
- [ ] Legacy URL inventory mapped completely for a migration