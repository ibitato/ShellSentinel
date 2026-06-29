# Static website SEO conventions

Guidelines for maintaining `website/` and `website/manuals/` so search engines index Shell Sentinel correctly.

**Tier:** project & collaboration (English only). Operator-facing copy lives in product manuals (EN/ES/DE).

## Canonical URLs

Every public page must declare `<link rel="canonical">` pointing to its final HTTPS URL on `www.shellsentinel.net`. This applies to main pages (`website/*.html`) and manuals (`website/manuals/`).

## hreflang

When multilingual content exists (EN/ES/DE):

- Add `rel="alternate"` links with `hreflang` for each language.
- Set `hreflang="x-default"` to the **English** URL.
- Keep `website/sitemap.xml`, canonical URLs and `hreflang` links consistent.

## Before publishing

1. Validate `website/sitemap.xml` and affected pages (URL Inspection / Search Console, or local tools such as `xmllint`).
2. After deploying static pages, spot-check URLs in Google Search Console and Bing Webmaster Tools (Coverage / URL Inspection).
3. Document indexing warnings in the PR or `CHANGELOG.md` when relevant.

## Local checks

Before merging website changes, verify there are no orphan routes, duplicate canonicals, or missing `hreflang` pairs across manual families (`user-guide-*`, `plugin-development-*`, `custom-providers-*`, `project-overview-*`, `contributor-handbook-*`).
