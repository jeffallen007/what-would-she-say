# DNS cutover and rollback: whatwouldshesay.com

**Status:** Pre-cutover snapshot, 2026-09-30 03:25–03:30 UTC (2026-09-29 evening Pacific). Jeff has captured the GoDaddy zone privately and lowered only the `@` and `www` A-record TTLs to 600 s; no routing values have changed. Both authoritative nameservers returned the original Lovable IP with 600 s TTL at 2026-09-30 03:46 UTC. The exact time of the later TTL edit is still needed to calculate the safe cutover time.

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
| 3 | Wait | — | — | — | At least 3600 s | Count from the later TTL edit so prior cached answers expire. Actual edit time is pending. |
| 4 | Edit existing record | `@` | A | `216.198.79.1` | 600 s | Replace `185.158.133.1` only after step 3; leave one apex A record. |
| 5 | Delete existing record | `www` | A | `185.158.133.1` | — | Required because a CNAME cannot coexist with `www` A. |
| 6 | Add record | `www` | CNAME | `2e80b9c1fab2ce73.vercel-dns-017.com` | 600 s | Add immediately after step 5. |
| — | **No change** | `@`, `_dmarc`, DKIM/SPF/mail hosts, any others | **MX and all email-related records** | **Keep existing values** | **Keep existing TTLs** | Leave email service untouched throughout. |
| — | **No change** | `@` | NS | GoDaddy nameservers | Keep | Do not move DNS hosting. |
| — | **No change now** | `_lovable` | TXT | No public record found | — | Do not remove a Lovable verification entry during cutover if GoDaddy shows one. |

Choose `whatwouldshesay.com` as the canonical domain and configure `www` to redirect to it in Vercel. That redirect is a Vercel project setting, not a GoDaddy record. If the dashboard recommends different DNS record types or extra verification, pause and reconcile the table before editing GoDaddy.

## Rollback if the live domain fails

Keep the Lovable custom domain in place until live-domain verification passes. At GoDaddy, restore `@` A to `185.158.133.1`. For `www`, remove the Vercel CNAME and restore A `185.158.133.1`. Use 600 s TTL during the rollback to limit further caching; after the old site is confirmed stable, restore the original 3600 s TTLs if desired. Leave all NS, MX, TXT, and other email-related records untouched. Verify both authoritative nameservers and HTTPS GET on apex and `www` after propagation.

The GoDaddy zone inventory is held privately by Jeff. Append the actual time of the later TTL edit, any verification record names, and the cutover/rollback timestamps when available. This public-DNS snapshot alone cannot establish every GoDaddy zone entry.
