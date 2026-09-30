# Frontend Migration Plan: Lovable → Vercel (whatwouldshesay.com)

## Goal
Move the What Would (S)he Say frontend off Lovable hosting to Vercel, repoint DNS, remove all Lovable
artifacts from the repo, and cancel the Lovable subscription. The Supabase Edge Functions and database
are **out of scope** and must not be touched.

## Current State (verified 2026-09-11)
- Apex `whatwouldshesay.com` → A record `185.158.133.1` = Lovable's edge IP.
- `www.whatwouldshesay.com` → no record. Only the apex resolves.
- DNS is managed at GoDaddy (`ns31.domaincontrol.com` / `dns.jomax.net`).
- App is maintained in the GitHub repo; Codex is the coding agent. Lovable is hosting only.
- Stack: Vite + React + TypeScript + shadcn-ui + Tailwind. Static build; no server runtime needed.

## Guardrails for Codex
- **Branch:** `chore/vercel-migration`. No direct commits to `main`.
- **Do not touch** `supabase/functions/**`, database migrations, or anything under
  `scripts/vectorstore-generation/` and `scripts/vector-investigation/`.
- **Never print or commit** secrets, API keys, or `.env` contents. Report variable *names* only.
- **Codex has no access** to GoDaddy, Vercel, or the Lovable dashboard. Every action in those
  systems is Jeff's. Stop and declare `ACTION REQUIRED:` when one is needed, then wait.
- **Stop at every GATE** and report inline.

---

## Phase 0: Discovery

**[Codex]**
1. Audit the repo for Lovable coupling and report a table of file → line → what it does:
   - `lovable-tagger` in `vite.config.ts` and in `package.json` devDependencies
   - Lovable badge, OG/meta tags, or script tags in `index.html`
   - Lovable URLs in `README.md`, docs, or code comments
   - `.github/workflows/**` — any Lovable action, or any deploy workflow at all
   - Any Lovable-specific config files
2. Report the frontend build contract: package manager and lockfile, Node version
   (`.nvmrc` / `engines`), build command, and output directory.
3. List every `VITE_`-prefixed env var the app reads, and where each is used. **Names only.**
   Flag whether the Supabase URL and anon key are hardcoded in source or read from env — this
   determines whether Vercel needs env vars configured at all.
4. Confirm the app talks to Supabase only via the Edge Function endpoints, with no other backends.
5. Verify the build works clean: fresh install, `npm run build`, then preview the output locally.
   Report any errors or warnings.
6. Report whether the repo has a Lovable GitHub App installed or a Lovable webhook
   (check repo settings if visible; otherwise flag it for Jeff to confirm).

**GATE 0 — report findings, then:**

> **ACTION REQUIRED:** Jeff to confirm (a) GitHub repo settings → Integrations/Webhooks: is the
> Lovable GitHub App or a Lovable webhook still connected? (b) Lovable billing: which plan and what
> monthly cost? (c) Vercel: which team/scope should own the project?

---

## Phase 1: Vercel Deploy (preview only, no DNS change)

> **ACTION REQUIRED:** Jeff to create the Vercel project — import the GitHub repo, select the
> `chore/vercel-migration` branch as the preview source, accept the detected Vite framework preset,
> and add any env vars Codex listed in Phase 0.3. Then give Codex the generated `*.vercel.app`
> preview URL.

**[Codex]** after receiving the preview URL:
1. Add `vercel.json` **only if needed** — a SPA rewrite so client-side routes don't 404 on refresh.
   Check whether the app uses client-side routing first; skip the file if it doesn't.
2. Smoke test the preview URL and report a pass/fail table:
   - Page loads, no console errors
   - Persona dropdown populates
   - One prompt per persona (Barbie, Homer, Jesus) returns a sensible in-character response
   - Verify the Edge Function calls succeed from the Vercel origin. **Call out any CORS failure
     explicitly** — the new origin is the most likely breakage point in this whole migration.
   - Client-side route refresh works, if applicable
3. If CORS fails, report the exact error and the required fix. **Do not modify Edge Functions** —
   this is a scope change for Jeff to approve.

**GATE 1 — report smoke test results. Do not proceed to DNS until every item passes.**

---

## Phase 2: DNS Cutover

**[Codex]** prepare first:
1. Record the current DNS state for rollback: apex A record, any `_lovable` TXT record, and all
   other records on the zone. Save to `docs/dns_rollback_whatwouldshesay.md`.
2. Produce the exact record changes Jeff needs to make at GoDaddy, in a copy-pasteable table.
3. **Leave MX and any email-related records untouched** and say so explicitly in the table.

> **ACTION REQUIRED:** Jeff to (a) lower the apex A record TTL to 600s at GoDaddy and wait for the
> old TTL (3600s) to expire — about an hour; (b) add `whatwouldshesay.com` and
> `www.whatwouldshesay.com` as domains in the Vercel project; (c) apply the DNS records Vercel
> specifies, replacing the Lovable A record; (d) tell Codex when applied.

**[Codex]** after DNS is applied:
4. Poll `dig` until the apex resolves to Vercel and report the result.
5. Confirm HTTPS works on both apex and `www`, with a valid certificate and no mixed-content warnings.
6. Re-run the full Phase 1 smoke test against the live domain.
7. Confirm `www` redirects to the apex (or whichever direction Jeff prefers).

**GATE 2 — report live-domain verification.**

> **Rollback at any point:** restore the apex A record to `185.158.133.1`. Lovable is still live
> and paid for until Phase 4, so rollback is a single DNS change.

---

## Phase 3: Repo Cleanup

**[Codex]** — separate commits, same branch:
1. Remove `lovable-tagger` from `vite.config.ts` and from `package.json`; update the lockfile.
2. Remove the Lovable badge, meta tags, and script tags from `index.html`.
3. Update both `README.md` files:
   - Replace the "Use Lovable" section with the Vercel + local dev workflow
   - Correct the hosting description
   - Correct the model label: the app uses `gpt-4o-mini`, not GPT-4o
   - Keep the credits and acknowledgements sections intact
4. Remove Lovable URLs from docs and comments.
5. Verify a clean build and re-run the smoke test against the resulting preview deploy.

**GATE 3 — PR review.**

> **ACTION REQUIRED:** Jeff to review and merge `chore/vercel-migration` to `main`, then confirm the
> production deploy on Vercel succeeded.

---

## Phase 4: Decommission Lovable

> **ACTION REQUIRED:** Jeff to, in order: (a) disconnect the Lovable GitHub App / webhook from the
> repo — **do this before canceling**, so nothing writes back to `main`; (b) remove the custom
> domain from the Lovable project; (c) cancel the Lovable subscription; (d) record the monthly
> savings.

**[Codex]** after Jeff confirms:
1. Remove the now-orphaned `_lovable` TXT record from the GoDaddy zone — produce the instruction;
   Jeff applies it.
2. Final verification: live site loads over HTTPS, all three personas respond, no Lovable references
   remain in the repo (grep and report).
3. Update `docs/dns_rollback_whatwouldshesay.md` to reflect the final state.

**GATE 4 — final report.**

---

## Acceptance Criteria
- `whatwouldshesay.com` and `www` serve from Vercel over valid HTTPS.
- All three personas return in-character responses on the live domain.
- Supabase Edge Functions and database are unchanged.
- Zero Lovable references in the repo; Lovable GitHub integration disconnected.
- Lovable subscription canceled; monthly savings recorded.
- Email/MX records unchanged throughout.

## Out of Scope
- The Weaviate → Supabase retrieval migration (separate plan, `docs/supabase_migration_plan.md`).
- Any UI or UX change.
- Renaming the `weaviate-chat` Edge Function.
