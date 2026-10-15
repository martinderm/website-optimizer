---
title: Static sites
description: What differs on a generated site: the robots layout, sitemap config, redirect files, and build-output auditing.
evidence_level: normative
support_level: fully_supported
applies_to: [website-optimizer]
references:
  - https://gohugo.io/configuration/sitemap/
  - https://gohugo.io/getting-started/configuration/
last_verified: 2026-10-15
review_due: 2027-01-15
---

# Static sites

Everything in `seo-core.md`, `indexing.md` and `structured-data.md` applies here
unchanged. This file holds only what is different because the site is **generated
and served as files**.

## The robots.txt trap

The single most important static-site rule in this skill.

**`enableRobotsTXT = true` is not enough.** The built-in output contains a
`User-agent: *` line and nothing else. Without an explicit `Sitemap:` directive,
search engines get no auto-discovery signal and you are relying entirely on
console submission.

A template is required:

```
layouts/robots.txt
---
User-agent: *
Disallow:

Sitemap: {{ "sitemap.xml" | absURL }}
```

Add `Disallow:` entries for genuinely private paths:

```txt
User-agent: *
Disallow: /admin/

Sitemap: {{ "sitemap.xml" | absURL }}
```

**This is an observed rule, not a specification** (`sources.md`). It is listed
here with high emphasis because it has been silently wrong on more than one site
in this workspace, and it fails invisibly: nothing errors, the site just never
gets discovered.

Verify on the built output, not in the template:

```bash
curl -s https://example.com/robots.txt
```

Expect a `200`, `text/plain`, and a line reading exactly
`Sitemap: https://example.com/sitemap.xml`.

## Sitemap configuration

```toml
enableRobotsTXT = true

[sitemap]
filename = "sitemap.xml"
```

- The generated sitemap is accurate as long as the build is. Emptied taxonomy
  terms and empty sections appear in the sitemap unless the templates filter
  them — check the file, not the config.
- `lastmod` reflects the build time for generated pages. It is not wrong, but it
  is not informative either.
- Pages excluded from the output cannot appear in the sitemap. If a URL matters,
  it must exist in the output.

## Redirects live in files

| Host | Mechanism |
|---|---|
| Apache | `.htaccess` |
| Cloudflare Pages, Netlify | `_redirects` |
| Caddy | `redir` directive in the Caddyfile |
| nginx | `return 301` |

The rules are the same as in `redirects.md`; only the syntax differs. The
ordering rule — specific before wildcard — applies identically, and the specific
syntax is the one thing that differs between hosts enough to cause a silent
mismatch when the same rule is copied between them.

## Verify the built HTML, not the source

On a generated site the thing that ships is `public/`, and it is often not what
the template implies:

- A staging `noindex` in a template applies to every built page.
- Front matter missing on one content file produces a page without a title.
- A partial that is not included in the base template silently removes a block
  from every page.
- Escaping bugs appear only in the serialised output.

**Always audit the build output.** That is what the tool reads, and it is the
only place these defects exist.

```bash
python scripts/wo.py on-page
```

with `static_dir` pointing at the generated directory.

## Per-page metadata comes from front matter

Titles, descriptions, and structured data should be **data in the content file**,
not literals in a template. A literal in a template is the same on every page,
which is exactly the duplication check in `seo-core.md` flags.

A missing front-matter value should degrade visibly — an empty title is a
finding — rather than fall back to a plausible-looking constant.

## Asset pipeline

- Emit modern formats at build time (`images.md`); never resize per request.
- Fingerprint filenames so they can be served immutable (`performance.md`).
- Keep the favicon set in the site root of the **build output**. An icon present
  in the repository but absent from the build is a common cause of "works
  locally".

## Multi-site operations

Each site is its own build with its own configuration. `site.optimizer.toml` is
per domain, and audit runs are stored per domain in the consuming workspace's
evidence zone. Nothing about one site's configuration may leak into another's —
`llms.txt` in particular is written per domain, never merged across sites.

## Checklist

- [ ] `layouts/robots.txt` template exists and is referenced
- [ ] Live `robots.txt` contains the exact `Sitemap:` line
- [ ] `sitemap.xml` inspected: no empty taxonomies, no redirects
- [ ] Redirect rules in the host's own mechanism, specific before wildcard
- [ ] Metadata from front matter, not template literals
- [ ] Audit run against `public/`, not against the source tree
- [ ] Favicon set present in the build output
- [ ] One configuration and one `llms.txt` per domain