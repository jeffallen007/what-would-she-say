# DNS cutover and rollback: whatwouldshesay.com

**Status:** Cutover applied by Jeff at 2026-09-30 03:53 UTC (2026-09-29 8:53 PM PDT). Jeff captured the GoDaddy zone privately before editing. The original pre-cutover snapshot was taken at 2026-09-30 03:25–03:30 UTC. Both authoritative nameservers returned the old Lovable IP with 600 s TTL by 03:46:38 UTC. The conservative old-cache expiry was 04:47 UTC; Jeff chose to cut over earlier because traffic is negligible and kept the Lovable project live for rollback.

**Final state (2026-09-30 04:21 UTC):** PR #1 is merged and Vercel production is live. Jeff removed the custom domain from the Lovable project. The pre-cutover DNS values and cutover steps below are retained as historical records; the old one-step DNS rollback is no longer available. See [Final verification and current rollback](#final-verification-and-current-rollback).

## Source and limits

`ns31.domaincontrol.com` and `ns32.domaincontrol.com` are the authoritative nameservers. Direct, non-recursive `dig` queries to both returned the same records and TTLs below. Public DNS does not provide a complete list of a zone's hostnames. Jeff confirmed that he captured the GoDaddy zone, but its complete contents have not been shared for inspection here. Do not commit verification-token or other sensitive TXT values to this repository.

The prior migration plan said `www` had no DNS record. That is no longer correct: both authoritative nameservers now return a `www` A record pointing to Lovable. A GET over HTTPS returned HTTP 200 from both the apex and `www` at the time of this snapshot.

## Current records and rollback values

| GoDaddy name | Type | Current value | TTL | Cutover / rollback treatment |
|---|---|---|---:|---|
| `@` | A | `185.158.133.1` | 3600 s | Replace at cutover; restore this exact value on rollback. |
| `www` | A | `185.158.133.1` | 3600 s | Remove before adding a Vercel CNAME; restore this exact A record on rollback. |
| `@` | NS | `ns31.domaincontrol.com`, `ns32.domaincontrol.com` | 3600 s | Do not change nameservers. |
| `@` | SOA | `ns31.domaincontrol.com`, `dns.jomax.net`, serial `2025071500` | 3600 s | GoDaddy-managed; do not edit. |
| `_dmarc` | TXT | Present; value intentionally omitted | 3600 s | Email-related. Leave untouched. |

No public answer was returned for `@` MX, `@` AAAA, `@` TXT, `@` CAA, `www` AAAA, `www` CNAME, `www` TXT, or `_lovable` TXT. No public A/CNAME answer was returned for `mail`, `autodiscover`, or `autoconfig`. These are observations for queried names only, not proof that the GoDaddy zone has no other records. In particular, **do not delete any MX, SPF, DKIM, DMARC, mail, or other email-related entry found in GoDaddy**.

## GoDaddy change table

Vercel's [domain setup guide](https://vercel.com/docs/domains/set-up-custom-domain) describes an apex A record and a subdomain CNAME. It lists general-purpose examples, but says a project may receive specific values. Jeff supplied the project-specific values below from Vercel's **Settings → Domains**. Both domains currently show `Invalid Configuration`, as expected before cutover. If Vercel requests a domain-verification TXT record, record its name and add its exact value privately in GoDaddy; do not replace existing TXT entries or put the value here.

| Order | GoDaddy action | Name | Type | Value | TTL | Condition |
|---:|---|---|---|---|---:|---|
| 1 | Edit existing record | `@` | A | `185.158.133.1` | 600 s | **Done:** lower TTL only; keep Lovable IP. |
| 2 | Edit existing record | `www` | A | `185.158.133.1` | 600 s | **Done:** lower TTL only; keep Lovable IP. |
| 3 | Wait | — | — | — | At least 3600 s | **Skipped by Jeff:** cutover at 03:53 UTC, accepting possible stale Lovable answers until about 04:47 UTC. |
| 4 | Edit existing record | `@` | A | `216.198.79.1` | 600 s | **Done:** replaced `185.158.133.1`; one apex A record remains. |
| 5 | Delete existing record | `www` | A | `185.158.133.1` | — | **Done:** removed before adding CNAME. |
| 6 | Add record | `www` | CNAME | `2e80b9c1fab2ce73.vercel-dns-017.com` | 600 s | **Done:** added after deleting `www` A. |
| — | **No change** | `@`, `_dmarc`, DKIM/SPF/mail hosts, any others | **MX and all email-related records** | **Keep existing values** | **Keep existing TTLs** | Leave email service untouched throughout. |
| — | **No change** | `@` | NS | GoDaddy nameservers | Keep | Do not move DNS hosting. |
| — | **No change now** | `_lovable` | TXT | No public record found | — | Do not remove a Lovable verification entry during cutover if GoDaddy shows one. |

Jeff selected `whatwouldshesay.com` as the canonical address. Vercel initially redirected the apex to `www`; Jeff changed the project domain setting, with no GoDaddy DNS change. At approximately 2026-09-30 04:00 UTC, the apex served HTTP 200 directly and `www` returned HTTP 308 to `https://whatwouldshesay.com/`. GATE 2 redirect verification passed.

## Post-cutover verification

At approximately 2026-09-30 03:54 UTC, both GoDaddy nameservers returned `@` A `216.198.79.1` (TTL 600 s) and `www` CNAME `2e80b9c1fab2ce73.vercel-dns-017.com` (TTL 600 s). Public resolvers `1.1.1.1` and `8.8.8.8` also returned the new records. Earlier cached Lovable answers may persist elsewhere until the old 3600 s TTL expires.

TLS certificate validation succeeded for both `https://whatwouldshesay.com/` and `https://www.whatwouldshesay.com/`; both GET requests ultimately returned HTTP 200 from Vercel. Initially, the apex redirected to `www`. In a headless Chrome test starting at the apex, the dropdown contained GPT-4o, Barbie, Homer Simpson, and Jesus. Each of Barbie, Homer, and Jesus received HTTP 200 from both `weaviate-warmup` and `weaviate-chat`, and each response rendered in the page. The main page had no console errors, JavaScript errors, failed requests, or mixed-content warnings. A direct load of `/test-route-refresh` rendered the app's Not Found page; its own intentional 404 console message was the only error on that route.

After Jeff corrected the redirect, a second headless Chrome test began and stayed at `https://whatwouldshesay.com/`. Barbie, Homer, and Jesus again received HTTP 200 from warmup and chat, with answers rendered from the apex origin. There were no browser CORS errors, failed requests, JavaScript errors, console errors on the main page, or mixed-content warnings. A direct load of `/test-route-refresh` still rendered the app's Not Found page. This closes GATE 2, subject to the accepted stale-cache window for visitors who cached the old 3600 s DNS answers.

## Final verification and current rollback

After Jeff disconnected the domain from Lovable, the authoritative GoDaddy nameserver still returned `@` A `216.198.79.1` and `www` CNAME `2e80b9c1fab2ce73.vercel-dns-017.com`. The apex returned HTTPS 200; `www` returned HTTPS 308 to the apex, then 200. Browser testing from the apex showed HTTP 200 for the warmup and chat requests for Barbie, Homer, and Jesus, with answers rendered and no CORS, JavaScript, console, or failed-request errors on the main page. A direct route refresh still rendered the app's Not Found page; its own 404 log is expected.

Jeff reported no `_lovable` TXT record in GoDaddy. A direct query to the authoritative nameserver also returned no `_lovable` TXT answer. There is therefore no Lovable verification record to remove. Leave all NS, MX, SPF, DKIM, DMARC, mail, and other email-related records untouched. The complete GoDaddy zone inventory remains with Jeff; public DNS queries cannot prove the absence of every record.

The Lovable GitHub account connection had already been removed, and the GitHub repository API returned no webhooks. Jeff previously confirmed the Lovable account is on the Free Plan with no active billing, so the current Lovable charge is $0 per month; the former paid-plan amount is not recorded here. A repository grep found no Lovable references in active application, build, or root documentation files. Historical migration documents and protected vectorstore research files still contain references as records of the migration.

For a frontend regression, restore a previously Ready Vercel production deployment while keeping the current DNS records. Restoring only the old Lovable A records is no longer a valid rollback because the custom domain is disconnected there. A return to Lovable would first require Jeff to reattach and verify the domain in Lovable, then coordinate DNS changes and check HTTPS on both hostnames. Keep email records untouched in any rollback.
