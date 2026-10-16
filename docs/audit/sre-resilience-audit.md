# SRE & Availability (`sre-resilience`) Audit Report: know-her

> **Auditor**: SRE & Availability Specialist (`sre-resilience` subagent)  
> **Date**: 2026-10-11  
> **Branch**: `hermes-subagent/subagent-sa-3-685520e1`  
> **Scope**: CI/CD Workflows, Curation Harvester & Network Probes, Service Worker & Offline Resilience, Bus Factor & Disaster Recovery.

---

## 1. Declared Read Scope

Every finding in this report is grounded in direct inspection of the following files and exact line ranges:

| Target File | Inspected Line Range | Functional Area |
| :--- | :--- | :--- |
| `.github/workflows/ci.yml` | 1 - 77 | CI Gate enforcement, runner steps, trigger topology, concurrency |
| `.github/workflows/deploy.yml` | 1 - 71 | CD Deployment gating, Pages environment, artifact packaging |
| `.github/workflows/daily-routine.yml` | 1 - 63 | Daily scheduled link probing, notification, issue creation |
| `.github/workflows/harvest-candidates.yml` | 1 - 202 | Pipeline B automated harvesting, branch isolation, PR automation |
| `.github/workflows/weekly-full-audit.yml` | 1 - 62 | Weekly deep link audit, scheduled run failure handling |
| `.github/workflows/lychee.yml` | 1 - 117 | Lychee link checker workflow, cache setup, issue deduplication |
| `.lychee.toml` | 1 - 19 | Link checker network timeouts, retries, WAF exclusion whitelist |
| `scripts/curate.py` | 1 - 401 | Frontmatter verification, live URL probing, 403 handling, retry logic |
| `scripts/curate_harvester.py` | 1 - 491, 620 - 895, 1320 - 1379, 1500 - 2045, 2130 - 2230 | Harvester HTTP client, probe budgets, subprocess timeouts, git push retry |
| `scripts/test_security_contracts.py` | 1 - 185 | URL protocol security assertions, 403 fallback mock contracts |
| `scripts/test_daily_loop.py` | 32, 59, 1050 - 1070, 2410 - 2450, 4455 - 4525, 5130 - 5185 | Test harness subprocess executions, timeout assertions |
| `scripts/test_pwa_contracts.py` | 1 - 229 | PWA manifest & SW contract structural regex verification |
| `public/sw.js` | 1 - 125 | Precache asset list, install/activate lifecycle, fetch caching, offline fallbacks |
| `public/manifest.webmanifest` | 1 - 30 | PWA manifest configuration, icons, display mode, start URL |
| `src/layouts/Base.astro` | 1 - 50, 220 - 248 | Service Worker registration, base path propagation, layout CSP |
| `src/components/AgePreferenceBanner.astro` | 15 - 44 | LocalStorage usage and namespace scoping |
| `src/components/DailyCard.astro` | 170 - 190 | LocalStorage quiz state and streaks |
| `src/components/DecisionGuide.astro` | 425 - 445 | Offline action copying and hardcoded URLs |
| `src/pages/privacy.astro` | 70 - 135 | Client-side privacy and LocalStorage clear keys |
| `src/pages/articles/[id].astro` | 30 - 45 | Canonical URL generation and Astro.site fallback |
| `src/pages/rss.xml.ts` | 15 - 30 | RSS feed canonical base URL resolution |
| `astro.config.mjs` | 1 - 17 | Static output, site origin, base path configuration |
| `package.json` | 1 - 34 | NPM dependencies, test script definitions, execution flags |
| `WORKMEMORY/PROJECT_OVERVIEW.md` | 1 - 140 | Architectural context, ADR records, historical changes |
| `WORKMEMORY/work.log` | 200 - 295 | Recent execution history, PWA/tooling rollout notes |

---

## 2. Executive Summary of Findings

| ID | Severity | Category | File:Line | Summary |
| :--- | :---: | :--- | :--- | :--- |
| **SRE-01** | **P0** | CI/CD Gate | `.github/workflows/deploy.yml:40-44`<br>`.github/workflows/ci.yml:49-53` | Production deployment blocked by real-time third-party external link probing |
| **SRE-02** | **P0** | Service Worker | `public/sw.js:11-20`<br>`public/sw.js:100-123` | Precache omits CSS and JS bundles; offline PWA renders broken unstyled DOM |
| **SRE-03** | **P0** | Network Probe | `scripts/curate.py:158-184`<br>`scripts/test_security_contracts.py:147-154` | 403 BOT_BLOCKED treated as valid/healthy, masking dead links; contracts diverge |
| **SRE-04** | **P1** | CI/CD Alerting | `.github/workflows/daily-routine.yml:52-63`<br>`.github/workflows/weekly-full-audit.yml:51-62` | Scheduled workflows lack issue deduplication, causing alert flooding on failure |
| **SRE-05** | **P1** | CI/CD Toolchain | `.github/workflows/ci.yml:29-41`<br>`.github/workflows/deploy.yml:26-38` | Missing explicit `actions/setup-python`; unpinned runner python risks command failure |
| **SRE-06** | **P1** | Service Worker | `public/sw.js:9`<br>`public/sw.js:37-40` | Static `CACHE_NAME` without build-hash bumping causes permanent stale cache & storage leak |
| **SRE-07** | **P1** | Service Worker | `public/sw.js:83-95` | Silent route masking on offline fallback creates severe UX confusion |
| **SRE-08** | **P1** | Network Probe | `scripts/curate.py:233-242`<br>`scripts/curate_harvester.py:834-854` | Zero rate limiting, delays, or jitter between outbound requests risks WAF IP throttling |
| **SRE-09** | **P1** | Network Probe | `scripts/curate_harvester.py:242-246` | Harvester sends bare User-Agent without browser headers, triggering WAF blockades |
| **SRE-10** | **P1** | Infrastructure | Repository Architecture<br>`astro.config.mjs:11-12` | Single Point of Failure (SPOF) on GitHub Pages with Bus Factor = 1 and zero mirror |
| **SRE-11** | **P2** | CI/CD Toolchain | `.github/workflows/harvest-candidates.yml:38` | Node version mismatch (Node 22 in Harvester vs Node 24 in CI/Deploy) |
| **SRE-12** | **P2** | CI/CD Concurrency | `.github/workflows/daily-routine.yml:1-12`<br>`.github/workflows/weekly-full-audit.yml:1-13` | Missing workflow concurrency control permits overlapping scheduled runs |
| **SRE-13** | **P2** | Subprocess Safety| `scripts/test_security_contracts.py:69-77` | Unbounded `subprocess.run` without `timeout=` parameter in security test |
| **SRE-14** | **P2** | Service Worker | `public/sw.js:25-29` | Atomic `cache.addAll()` aborts entire SW installation on single asset network hiccup |
| **SRE-15** | **P2** | DR / Portability | `astro.config.mjs:11`<br>`public/sw.js:11-20`<br>`public/robots.txt:4` | Hardcoded host and `/know-her/` path across 8+ files obstructs multi-domain migration |

---

## 3. Deep Dive Findings & Failure Scenarios

### Finding SRE-01: Production Deployment Coupled to Third-Party External Availability (P0)
- **Citations**:
  - `.github/workflows/deploy.yml:40-44`
  - `.github/workflows/ci.yml:49-53`
  - `scripts/curate.py:206-248`
- **Concrete Failure Scenario**:
  In `.github/workflows/deploy.yml`, step `Verify article sources (零404外链巡检门禁)` executes `pnpm curate:links`. This command iterates over all 25+ markdown articles in `src/content/articles/*.mdx` and performs live sequential HTTP requests to each third-party external server (`who.int`, `msdmanuals.cn`, `dxy.com`, `guokr.com`, etc.).
  If a single external medical portal undergoes maintenance (e.g. returns 502/503), drops TCP connections during a network glitch, or rate-limits GitHub Actions runner egress IP addresses, `check_single_url` returns `False`. The script exits with status 1, crashing the deployment workflow.
  **Impact**: Production releases of know-her (including critical emergency bugfixes, security patches, or editorial corrections) are completely paralyzed by the transient availability of arbitrary external websites.

### Finding SRE-02: Precache Omission of Bundled Stylesheets and Scripts Breaks Offline PWA (P0)
- **Citations**:
  - `public/sw.js:11-20`
  - `public/sw.js:100-123`
  - `dist/tools/index.html` (verified dependencies: `Base.*.css`, `PositionAndIntimacyGuide.*.js`, `ClinicMemo.*.js`, `ReportDecoder.*.js`)
- **Concrete Failure Scenario**:
  `public/sw.js` defines `PRECACHE_ASSETS` containing only 4 HTML pages (`/know-her/`, `/know-her/tools/`, `/know-her/guide/decision-tree/`, `/know-her/glossary/`) and 4 SVG/manifest files.
  When a user installs the PWA and subsequently goes offline in an emergency scenario (e.g. lost cellular connectivity in a subway, basement, or remote area):
  1. The browser navigates to `/know-her/tools/` or `/know-her/guide/decision-tree/`.
  2. The Service Worker returns the cached HTML skeleton.
  3. The HTML parses and attempts to load its compiled stylesheets and script modules (`_astro/Base.7DlL1xA9.css`, `_astro/ClinicMemo...js`, etc.).
  4. Because compiled assets were never precached, and the user had not previously navigated to that specific tool while online, the Cache-First fetch handler in `sw.js` line 121 catches the network failure and returns an empty HTTP 408 response (`Offline Resource Unavailable`).
  **Impact**: The user receives a blank or completely unstyled, broken webpage. Critical emergency scripts (72h/120h Emergency Contraception Countdown, COC Missed Pill Calculator, Decision Tree interactive diagnosis) fail to load, completely defeating the PWA's stated core mission.

### Finding SRE-03: Inverted 403 BOT_BLOCKED Logic Masking Inaccessible Content and Diverging Contracts (P0)
- **Citations**:
  - `scripts/curate.py:158-184`
  - `scripts/test_security_contracts.py:147-154`
  - `scripts/curate_harvester.py:844-854`
  - `.lychee.toml:17-19`
- **Concrete Failure Scenario**:
  In `scripts/curate.py:check_single_url`, if a URL responds with HTTP 403 on the initial probe, it performs a retry with desktop browser headers. If the retry still returns HTTP 403, line 181 prints `⚠️ [BOT_BLOCKED 403]` and returns `True`.
  Furthermore, `scripts/test_security_contracts.py` explicitly tests and enforces that two 403 responses MUST return `True` (lines 147-154).
  However, if an external source removes an article, puts it behind a strict paywall/login barrier, or geoblocks public traffic, real human users clicking "原文直达" are completely blocked with HTTP 403. `curate:check` and `curate:links` will falsely report 100% green health.
  Meanwhile, `curate_harvester.py` drops any candidate URL returning 403 as `probe_failed`, and `lychee-action` in `lychee.yml` marks any non-whitelisted 403 URL as a broken link and files a GitHub issue. Three tools in the same repository apply mutually contradictory definitions of external link health.

### Finding SRE-04: Alert Flooding via Undeduplicated Issue Creation in Scheduled Workflows (P1)
- **Citations**:
  - `.github/workflows/daily-routine.yml:52-63`
  - `.github/workflows/weekly-full-audit.yml:51-62`
- **Concrete Failure Scenario**:
  Both `daily-routine.yml` and `weekly-full-audit.yml` feature an `Alert on Failure` step that unconditionally invokes `github.rest.issues.create(...)` when the job fails.
  Unlike `lychee.yml` (which uses `gh issue list --label broken-links --state open` to deduplicate) and `harvest-candidates.yml` (which queries `github.rest.issues.listForRepo` for existing backlog issues), neither routine checks if an open alert issue already exists.
  If an upstream third-party link fails permanently, `daily-routine.yml` will create a brand new issue every morning at 00:00 UTC. Over 30 days, 30 identical duplicate issues are created, spamming repository maintainers and burying real operational notifications.

### Finding SRE-05: Missing Explicit Python Setup in CI/CD Gating Jobs (P1)
- **Citations**:
  - `.github/workflows/ci.yml:21-53`
  - `.github/workflows/deploy.yml:18-54`
  - `.github/workflows/daily-routine.yml:15-43`
  - `.github/workflows/weekly-full-audit.yml:15-43`
- **Concrete Failure Scenario**:
  These workflows invoke `pnpm test:graph`, `pnpm curate:check`, and `pnpm curate:links`, all of which execute `python -X utf8 scripts/...`.
  None of these workflows include an `actions/setup-python` step. They rely purely on whatever default `python` binary happens to exist on GitHub's `ubuntu-latest` runner image.
  When GitHub updates runner images or changes default python symlinks (or if standard runners unbind `python` in favor of `python3`), the runner immediately terminates with `/bin/sh: 1: python: not found`, breaking the entire CI and deployment pipeline without any code changes having been committed.

### Finding SRE-06: Static Cache Name Without Build Hashing Causes Permanent Stale Cache & Storage Leak (P1)
- **Citations**:
  - `public/sw.js:9`
  - `public/sw.js:33-43`
- **Concrete Failure Scenario**:
  `public/sw.js` hardcodes `const CACHE_NAME = 'know-her-offline-v1';`.
  Because `sw.js` is committed statically without build-time version injection:
  1. The browser's Service Worker bytecode never changes between deployments, preventing activation of the `activate` lifecycle hook.
  2. In `activate` (lines 37-40), stale cache cleanup only purges caches where `name !== CACHE_NAME`. Because `CACHE_NAME` is immutable, no cache deletion ever occurs.
  3. Every subsequent deployment emits new content-hashed assets (`_astro/Base.<new_hash>.css`). The Cache-First handler caches every newly requested asset into `'know-her-offline-v1'`. The old assets are never reclaimed, causing progressive and unbounded disk growth in user browsers.

### Finding SRE-07: Silent Route Masking on Offline Navigation Fallback (P1)
- **Citations**:
  - `public/sw.js:83-95`
- **Concrete Failure Scenario**:
  When a user is offline and navigates to an article URL that has not been cached (e.g. `/know-her/articles/body-dysmenorrhea/`), `sw.js` fails the network request and finds no direct cache match.
  Lines 84-87 fallback to `caches.match('/know-her/guide/decision-tree/')`.
  The browser address bar remains `https://rom4n2.github.io/know-her/articles/body-dysmenorrhea/`, but the screen displays the Emergency Decision Tree (避孕套破裂/漏服避孕药/异常出血), with zero visual indicator or banner stating: "You are currently offline; displaying emergency decision tree."
  Users seeking dysmenorrhea advice are startled to see an emergency contraception decision tree, inducing confusion and eroding trust in the application's clinical guidance.

### Finding SRE-08: Absence of Rate Limiting and Backoff in Batch Network Probing (P1)
- **Citations**:
  - `scripts/curate.py:233-242`
  - `scripts/curate_harvester.py:834-854`
- **Concrete Failure Scenario**:
  In `scripts/curate.py:cmd_check_links`, 25+ requests are dispatched in a tight loop with 0ms pause between probes. Similarly, in `scripts/curate_harvester.py`, up to 60 candidate URLs (`MAX_HARVEST_PROBES = 60`) are probed sequentially without `time.sleep()`.
  When auditing multiple articles pointing to the same host (e.g., WHO or MSD Manuals), the origin server detects rapid automated scraping from a datacenter IP range (GitHub Actions) and issues HTTP 429 (Too Many Requests) or drops connections.
  Because neither script implements token-bucket rate limiting or exponential backoff per host, whole batches of valid links are flagged as broken or rejected.

### Finding SRE-09: Harvester HTTP Probes Use Minimal Request Headers Triggering WAF Blocks (P1)
- **Citations**:
  - `scripts/curate_harvester.py:242-246`
- **Concrete Failure Scenario**:
  `curate_harvester.py:_http_get` creates requests using only `headers={"User-Agent": USER_AGENT}`.
  Modern Web Application Firewalls (Cloudflare, Akamai, Imperva) specifically detect automated scraping clients that send desktop Chrome User-Agent strings but omit the standard browser header fingerprint (`Accept`, `Accept-Language`, `Accept-Encoding`, `Sec-Fetch-Mode`, etc.).
  The harvester's requests are blocked with 403 Forbidden at the entry URL or sitemap endpoint, causing `discover_candidates` to return empty candidate lists and stalling daily curation.

### Finding SRE-10: Single Point of Failure (SPOF) on GitHub Pages & Bus Factor = 1 (P1)
- **Citations**:
  - Repository Architecture & `.github/workflows/deploy.yml`
  - `astro.config.mjs:11-12`
- **Concrete Failure Scenario**:
  The application is exclusively deployed to GitHub Pages under a single user namespace (`ROM4n2`).
  Because the site deals with sexual health, reproductive organs, clitoral anatomy, and contraceptive methods, algorithmic content flagging or false-positive abuse reporting on GitHub could lead to temporary repository or account suspension.
  Because no secondary mirror (such as Cloudflare Pages, Vercel, or independent S3/R2 object storage) is maintained, and no multi-maintainer organization or automated failover exists, any disruption to the single GitHub account results in a complete, unrecoverable site outage.

### Finding SRE-11: Toolchain Node Version Mismatch Across Workflows (P2)
- **Citations**:
  - `.github/workflows/harvest-candidates.yml:38`: `node-version: 22`
  - `.github/workflows/ci.yml:37`: `node-version: 24`
  - `.github/workflows/deploy.yml:34`: `node-version: 24`
- **Concrete Failure Scenario**:
  `harvest-candidates.yml` runs gate self-checks (`pnpm check` and `pnpm build`) on Node 22, whereas CI and deployment run on Node 24.
  Discrepancies in Vite/Rolldown module resolution, native V8 syntax, or pnpm cache behaviors between Node 22 and 24 risk false-positive pass/fail signals between candidate branches and master.

### Finding SRE-12: Missing Concurrency Controls on Scheduled Workflows (P2)
- **Citations**:
  - `.github/workflows/daily-routine.yml:1-12`
  - `.github/workflows/weekly-full-audit.yml:1-13`
- **Concrete Failure Scenario**:
  Neither `daily-routine.yml` nor `weekly-full-audit.yml` defines a `concurrency:` group.
  If a maintainer triggers `workflow_dispatch` while a scheduled cron run is underway, multiple runners concurrently probe external endpoints, doubling egress traffic and increasing the risk of race conditions or duplicate issues.

### Finding SRE-13: Unbounded Subprocess Execution in Security Contract Gate (P2)
- **Citations**:
  - `scripts/test_security_contracts.py:69-77`
- **Concrete Failure Scenario**:
  `test_security_contracts.py` executes `subprocess.run(["node", ...], check=True, cwd=PROJECT_ROOT)` without setting a `timeout=`.
  If Node.js experiences an ESM loading freeze, Windows path lock, or unhandled promise deadlock, the process will hang indefinitely until the parent runner timeout is reached.

### Finding SRE-14: Atomic `cache.addAll()` Fails Whole Service Worker Installation (P2)
- **Citations**:
  - `public/sw.js:25-29`
- **Concrete Failure Scenario**:
  W3C specification dictates that `cache.addAll()` is atomic. If any one of the 8 assets in `PRECACHE_ASSETS` (e.g. `og-card.svg`) returns an error or times out during install, the entire promise rejects. The Service Worker is discarded and enters redundant state, leaving the user with zero offline caching.

### Finding SRE-15: Hardcoded Domain and Subpath Inhibiting Disaster Recovery (P2)
- **Citations**:
  - `astro.config.mjs:11`
  - `public/robots.txt:4`
  - `public/og-card.svg:78`
  - `src/components/DecisionGuide.astro:436`
  - `public/sw.js:11-20`
- **Concrete Failure Scenario**:
  In a disaster recovery drill requiring migration to a custom domain (`know-her.org`) or alternative host, hardcoded references to `https://rom4n2.github.io/know-her/` in `robots.txt`, `sw.js`, and `DecisionGuide.astro` cause broken links, 404 cache attempts, and incorrect sitemap indexing.

---

## 4. Prioritized Remediation Roadmap

### Immediate Fixes (P0 Blockers):
1. **Decouple Deployment from Live Third-Party Uptime**:
   In `.github/workflows/deploy.yml` and `.github/workflows/ci.yml`, replace `pnpm curate:links` with internal validation (`pnpm curate:check` and offline contracts). Restrict full-link probing exclusively to asynchronous monitoring (`daily-routine.yml` and `weekly-full-audit.yml`) or run link checking with `continue-on-error: true` in CI.
2. **Precache Critical CSS & JS Bundles in Service Worker**:
   Integrate a post-build script or Workbox/Astro PWA integration that automatically collects generated `_astro/*.css` and `_astro/*.js` bundles for `/tools/` and `/guide/decision-tree/` into the Service Worker precache manifest.
3. **Harmonize 403 BOT_BLOCKED Contract**:
   Stop treating HTTP 403 as a universal pass (`return True`) in `curate.py`. Restrict 403 exemptions to an explicit domain whitelist (e.g. `.lychee.toml`'s Mayo Clinic whitelist). For unwhitelisted domains, classify 403 as `BOT_BLOCKED_UNVERIFIED` and require manual audit rather than silently passing in deployment gates.

### Secondary Hardening (P1 Reliability):
1. **Deduplicate Issue Creation in Scheduled Workflows**:
   Adopt the issue deduplication logic from `lychee.yml` / `harvest-candidates.yml` into `daily-routine.yml` and `weekly-full-audit.yml` before calling `issues.create`.
2. **Pin Python in all Workflows**:
   Add `actions/setup-python@v5` with `python-version: "3.12"` to `ci.yml`, `deploy.yml`, `daily-routine.yml`, and `weekly-full-audit.yml`.
3. **Build-Time Service Worker Version Invalidation**:
   Inject Git commit SHA or build timestamp into `CACHE_NAME` in `sw.js` during `pnpm build`, ensuring proper cache rotation and old cache eviction on release.
4. **Offline Fallback UI Transparency**:
   Provide a dedicated `/offline/` fallback page or inject a floating notification (`[离线模式] 目标文章未离线缓存，已为您载入应急决策树`) when route masking occurs.
5. **Rate Limiting & Realistic Headers in Probing Scripts**:
   Add a minimum 500ms delay between external requests in `curate.py` and `curate_harvester.py`, accompanied by standard browser request headers (`Accept`, `Accept-Language`).

### Resilience & Disaster Recovery (P2):
1. **Multi-Hosting Mirror**:
   Configure a secondary deployment target (e.g., Cloudflare Pages via GitHub Actions hook) to eliminate GitHub Pages as a single point of failure.
2. **Environment Variable Driven Domain Base**:
   Derive `site` and `base` in `astro.config.mjs` and all components from `process.env.SITE_URL` and `process.env.BASE_PATH` with sensible fallbacks.
