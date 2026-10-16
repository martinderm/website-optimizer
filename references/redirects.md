---
title: Redirects
description: Permanent redirects, chains, wildcards, and the URL lifecycle after a migration.
evidence_level: normative
support_level: fully_supported
applies_to: [website-optimizer]
references:
  - https://developers.google.com/search/docs/crawling-indexing/301-redirects
  - https://httpwg.org/specs/rfc9110.html#status.301
last_verified: 2026-10-15
review_due: 2027-01-15
---

# Redirects

A redirect is a promise that a URL still means something. Breaking it costs
traffic slowly and invisibly.

## Permanent, always

**301** for anything that moved permanently. A 302 says "temporarily" and the
redirect is not treated as a signal to consolidate signals; a temporary redirect
that stays temporary for a year is a 302 that was wrong on day one.

Use 301 for:

- a moved page,
- an HTTP-to-HTTPS or host-to-host migration,
- a slug change,
- a domain consolidation.

Reserve 302 for genuinely temporary states: a maintenance page, a seasonal
landing page, an A/B test variant.

## Host and protocol canonicalisation

Exactly one host and one protocol should serve a site. Redirect everything else
permanently, **including the path and the query string**:

```
https://www.example.com/some/page?ref=x  →  https://example.com/some/page?ref=x
```

A redirect to the bare domain drops the path and is the most common form of this
bug. Preserve both.

## Chains and loops

A redirect chain — `/a → /b → /c → /d` — passes the signal along at each hop and
adds latency at each hop. **Point every old URL directly at its final
destination**, not at the next hop.

Loops are a configuration error that produces an error page in a browser and a
bot in a crawler.

## Wildcards, specific before general

```apache
# Specific exceptions first
RewriteRule ^portfolio/items/?$   /projects/       [R=301,L]
RewriteRule ^portfolio/items/([^/]+)/?$  /projects/$1/  [R=301,L]

# General rule last
RewriteRule ^portfolio/([^/]+)/?$  /projects/$1/  [R=301,L]
```

The order is the whole point: a catch-all placed first swallows the specific
cases. Map an entire legacy section at once rather than page by page — the
per-page approach is what produces chains.

The same rules belong in whichever redirect mechanism the host serves: `.htaccess`
for Apache, `_redirects` for Cloudflare Pages and Netlify, `redir` in a Caddyfile.

## After a migration

1. Inventory every URL with traffic before changing anything. Analytics, Search
   Console, server logs, and external links.
2. Map each to exactly one destination. Anything without a mapping gets a
   deliberate decision, not a default.
3. Check the archived old site does not compete. If the old site stays online,
   set it to `noindex` and point its canonicals at the new domain.
4. Watch for months, not days. Search Console reports "not found" for URLs that
   nobody thought to redirect, and they keep appearing.

## Legacy archives

Keeping an old site online for reference:

- `noindex` it (`blog_public = 0` on WordPress), otherwise you have two sites
  competing for the same queries.
- Replace every internal domain reference — including JSON-escaped variants that
  plugins leave behind in their own option tables.
- The archive is reachable by URL for people who need it; it is not indexed.
- Do not redirect the archive: its whole purpose is to remain a distinct,
  non-competing address.

## 404s

- A branded 404 page with real navigation helps a visitor and gives a crawler a
  way onward. It does not soften the error itself.
- A 404 must be a 404. Serving a 200 with an error message tells crawlers the
  URL exists and indexes it.
- Soft 404s — a real page that answers "not found" under an old URL — waste
  crawl budget. Redirect or 404 them.

## Checklist

- [ ] 301, not 302, for everything permanent
- [ ] Host and protocol redirect preserves path and query string
- [ ] No chains; every old URL points at its final destination
- [ ] No loops
- [ ] Specific redirect rules ordered before wildcards
- [ ] Traffic-inventory-driven mapping, no unmapped URLs
- [ ] Archived old site set to `noindex`, references rewritten
- [ ] 404 returns a 404, with a branded page
- [ ] Redirects verified by fetching them, not by reading the config

## Verification

Configuration that reads correctly and redirects wrongly is common. Check the
live responses:

```bash
curl -sI https://old.example.com/legacy/path/
```

Expect `301` and a single `Location`. Then follow it and expect `200`. A chain
shows up as several `301` responses before the `200`.

## When the rules are not in a file

*Advisory, not a rule. The decision belongs to the site; this is what to weigh
before making it.*

The checklist above assumes the rules can be read somewhere. On most platforms
they cannot:

| Platform | Where redirects usually live | Readable as a file |
|---|---|---|
| Apache | `.htaccess` or vhost config | yes |
| Netlify / Cloudflare Pages | `_redirects` | yes |
| nginx | `server` block in the site config | **no — and it fails silently, see below** |
| WordPress | database — core, Redirection, or an SEO plugin | no |

The last row is the one that bites. WordPress has no `.htaccess` on nginx, and
its redirects are rows in a database whose shape changes with every plugin
update.

### Do not point an nginx vhost at this tool

An nginx `server` block is not an `.htaccess`. nginx writes `return 301` and
`rewrite`; Apache writes `Redirect` and `RewriteRule`. Pointing the audit at an
nginx config parses **zero** rules and reports nothing, because there is no error
to raise — the file was read successfully, it simply contained nothing it
recognised. That is the most dangerous shape a redirect audit can take: a clean
bill of health for a site that redirects traffic.

Export the mappings instead — JSON, CSV or TSV is what the tool reads — and let
it check that export against the live server, which is the check that actually
matters.

**Weigh these before choosing a source:**

- *Read the database.* Answers "what is stored", which is not the question anyone
  has. The schema moves under you, and a silently wrong read is worse than no
  read: it produces a confident clean bill of health for a site that is losing
  traffic.
- *Read the server config.* True, but it has to be re-read per deployment and it
  does not exist on the machine doing the audit.
- *Check a URL list against the live server.* Survives every update, works on
  every platform, and answers the question that actually matters: *does this old
  URL still go where it should?* Its limit is real — it can only check URLs
  someone remembered to write down.

**Whatever the source, the report must say which one it used.** A redirect audit
that does not name its source is indistinguishable from one that found nothing.
The same holds for the finding: a run that checked twenty remembered URLs is not
a statement about the other eight hundred, and must not read like one.

**Record the decision and its owner, not just its source.** "nginx" is half an
answer. The other half is who synchronises it after a deployment, and when. A
redirect map nobody maintains is a redirect map that is wrong by the next release.

**Keep it in two places, with different jobs.** The decision — where the rules
live, who maintains them — is normative and belongs in the workspace's site
dossier. The paths and limits are parameters and belong in the site config. One
home per fact, and they are not the same fact.