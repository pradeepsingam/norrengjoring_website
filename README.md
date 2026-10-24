# Nor Rengjøring website

HTML, CSS and JavaScript with a PHP 8.1+ contact endpoint. Run locally from this folder:

```sh
php -S 127.0.0.1:8765
```

Open http://127.0.0.1:8765/.

## Hosting

Use PHP hosting with working session storage and a configured `mail()` transport.
Upload the entire folder, including `contact.php`, images, fonts, `site.js`, `shared.css`,
`.htaccess`, and the directory `index.html` files. The directory pages preserve the former
WordPress URLs without rewrite support. `.htaccess` supplies permanent redirects
on Apache with mod_rewrite; other hosts should configure equivalent HTTP 301 rules.
Static-only hosts such as Netlify cannot run this PHP mail handler directly.
Query strings and fragments are preserved by the static redirect script.

## Contact delivery

The contact form posts to `contact.php`, which sends plain-text email to
`post@norrengjoring.no` through PHP `mail()`. The sender is fixed to
`no-reply@norrengjoring.no`; the validated visitor address is used only for
Reply-To. The hosting provider must permit this sender and configure outbound
mail and domain authentication. A successful `mail()` call means the transport
accepted the message; it does not prove inbox delivery. Verify delivery on the
real host before publishing. No actual email was sent during local checks.

The handler validates fields server-side, rejects header injection and oversized
requests, checks session CSRF tokens, includes a honeypot, and limits attempts
per session. Consider a host-level IP rate limit for public traffic. No message
content is retained by the application. Do not put credentials in browser JavaScript.

For manual testing without sending email, start a separate server with
`NOR_CONTACT_TEST_MODE=1 php -S 127.0.0.1:8766`. Test mode is explicitly labeled
in the response and UI. Never enable this flag on the published site. Automated
tests also disable the mail transport, so they cannot deliver messages.

## Assets and preferences

Required images and both font families are hosted locally. Five shared cleaning
photos are reused across page heroes, intro cards and banners; identical copies
and unused illustration fallbacks have been removed.
Photographs use WebP. The two font families use self-hosted Latin WOFF2 subsets
that include Norwegian characters; their license notices are in `fonts/`.
Google Maps is optional and is loaded only after the visitor allows functional
services or explicitly chooses to display the map. The preference is stored in
browser local storage. It can be withdrawn through the preferences button.
No analytics or advertising scripts are installed.

The social icons were removed because no verified business profile links were
provided. Add linked icons only once the actual account URLs are available.

## Checks

```sh
python3 -m unittest discover -s tests -v
node --check site.js
php -l contact.php
```

## SEO and production domain

The production origin is `https://www.norrengjoring.no/`. Every content page has
an absolute canonical, its own title/description, Norwegian language metadata,
social preview tags and factual JSON-LD. Service pages link to `tjenester.html`.
The sitemap lists 13 content pages; the 404 page, contact API and redirect helpers
are excluded. Keep `sitemap.xml` in sync when adding or removing pages.

`.htaccess` redirects the production domain to HTTPS/www, `/index.html` to `/`,
former WordPress page paths to their HTML replacements, and `/wp-sitemap.xml`
to `/sitemap.xml`. Eight known WordPress image URLs also redirect to their
local replacements. It also configures a real 404 error document, compression and
asset cache headers. These rules were exercised on a local Apache server.
If a trusted reverse proxy terminates TLS, configure HTTPS detection on the
hosting server so it does not redirect already-secure requests repeatedly.
The local PHP development server does not process `.htaccess`.

After deployment, verify the live HTTP responses, canonical URLs, structured
data and mail delivery. Verify this exact property in Google Search Console
and submit `https://www.norrengjoring.no/sitemap.xml`. A sitemap or valid markup
does not guarantee indexing or rich-result display. No ranking or traffic
improvement has been measured yet.
