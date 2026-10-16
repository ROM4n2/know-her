# Frontend & State Systems (`frontend-architect`) Audit Report: know-her

> **Auditor**: Frontend & State Systems Architect (`frontend-architect` subagent)  
> **Date**: 2026-10-11  
> **Branch**: `hermes-subagent/subagent-sa-3-685520e1`  
> **Repository Worktree**: `D:/Code/know-her/.worktrees/subagent-sa-0-de059699/.worktrees/subagent-sa-3-685520e1`  
> **Stack**: Astro 7.3.3 + TypeScript + Tailwind CSS v4 + Pagefind WASM + Native Service Worker PWA  
> **Scope**: Entire frontend codebase (`src/`, `public/`, `astro.config.mjs`, `scripts/test_*`).

---

## 1. Declared Read Scope

Every finding and architectural citation in this report is grounded in direct inspection of the following files and exact line ranges:

| Target File | Inspected Line Range | Functional Area |
| :--- | :--- | :--- |
| `package.json` | 1 - 34 | Build scripts, dependencies, Astro 7.3.3 / Tailwind v4 toolchain |
| `astro.config.mjs` | 1 - 17 | Static output mode, base path `/know-her`, Pagefind & Tailwind integrations |
| `public/sw.js` | 1 - 125 | Precache manifest, install/activate lifecycle, navigation & static fetch caching |
| `public/manifest.webmanifest` | 1 - 28 | PWA manifest, display mode, icons, start_url & scope |
| `src/layouts/Base.astro` | 1 - 248 | SW registration, base URL propagation, CSP, header/bottom navigation, modal mounts |
| `src/styles/global.css` | 1 - 69 | Design tokens, paper/ink palette, touch targets, tactile button feedback |
| `src/pages/tools/index.astro` | 1 - 339 | Tools aggregator, anchor nav, URL parameter dispatch script (`is:inline`) |
| `src/components/tools/ReportDecoder.astro` | 1 - 150, 360 - 699 | Lab report decoder, module script lifecycle, DOM rendering, PNG exporter |
| `src/components/tools/EmergencyCountdown.astro` | 200 - 421 | 72h/120h countdown logic, 2h vomit observation timer (`is:inline`) |
| `src/components/tools/CocRemedyCalculator.astro` | 140 - 220 | Missed pill evaluation, DOM updates, status badges (`is:inline`) |
| `src/components/tools/CycleAssessment.astro` | 173 - 242 | Menstrual cycle scoring, DOM badges, validation (`is:inline`) |
| `src/components/tools/ContraceptionMatrix.astro` | 430 - 539, 870 - 950 | Floating compare bar, modal drawer, zero-innerHTML table rendering |
| `src/components/tools/PositionAndIntimacyGuide.astro` | 420 - 475, 835 - 904 | Floating compare bar, checklist state management, memo exporter |
| `src/components/tools/ClinicMemo.astro` | 570 - 654, 1095 - 1164 | SOAP memo generator, JSON hydration, canvas image export module |
| `src/components/SearchModal.astro` | 1 - 314 | Pagefind WASM async search, shortcut pills, DOM sanitizer, keyboard traps |
| `src/components/TableOfContents.astro` | 1 - 183 | H2/H3 outline, IntersectionObserver, scroll throttling, duplicate links |
| `src/components/ReadingProgress.astro` | 1 - 42 | Top progress bar, requestAnimationFrame scroll listener |
| `src/components/PanicExit.astro` | 1 - 324 | Floating panic trigger, disguise modal, touch gesture listener, DOM safety |
| `src/components/DecisionGuide.astro` | 185 - 461 | Emergency decision tree, state stack, hash routing, JSON data hydration |
| `src/components/ArticleSchema.astro` | 1 - 70 | Schema.org Article JSON-LD serialization and `<` escaping |
| `src/pages/articles/[id].astro` | 1 - 120, 230 - 404 | Article layout, MDX typography, table styling, copy share action |
| `src/pages/index.astro` | 1 - 120, 200 - 266 | Category filtering, daily rotation, random wander double event listener |
| `src/lib/ui/memoImageExporter.ts` | 1 - 120, 200 - 265 | Canvas 2D image renderer, word wrap, blob URL lifecycle |
| `scripts/test_pwa_contracts.py` | 1 - 229 | PWA manifest & SW structural regex test gate |
| `scripts/test_reading_ux.py` | 1 - 120 | ReadingProgress & TableOfContents structural regex test gate |
| `scripts/test_security_contracts.py` | 1 - 120 | URL security and link check test gate |

---

## 2. Executive Summary of Findings

| ID | Severity | Category | File:Line | Summary |
| :--- | :---: | :--- | :--- | :--- |
| **FE-01** | **P0** | Service Worker | `public/sw.js:11-20`<br>`public/sw.js:100-123` | Precache omits CSS & JS bundles; offline PWA renders broken, unstyled, non-functional DOM |
| **FE-02** | **P1** | Service Worker | `public/sw.js:66-96`<br>`src/components/SearchModal.astro:13-16` | Navigation matching fails on query parameters (`ignoreSearch: false`), routing offline users to wrong fallback |
| **FE-03** | **P1** | Service Worker | `public/sw.js:9`<br>`public/sw.js:100-117` | Static `CACHE_NAME` without build-hash bumping causes permanent stale cache on unhashed assets |
| **FE-04** | **P1** | Script Hydration | `src/pages/tools/index.astro:289-306`<br>`src/components/tools/ReportDecoder.astro:366` | Inline script executes before deferred ES module script; fallback `.click()` fires on unattached listeners |
| **FE-05** | **P1** | Client State Race | `src/components/SearchModal.astro:193-278` | Async Pagefind search lacks query freshness check; delayed results overwrite empty search state |
| **FE-06** | **P1** | Clinical Safety | `src/components/tools/EmergencyCountdown.astro:345-398` | 2h clinical timer decrements via `setInterval` tick count; background tab suspension halts clock & risks redosing overdose |
| **FE-07** | **P1** | Gesture Conflict | `src/components/PanicExit.astro:315-319`<br>`src/layouts/Base.astro:64` | `touchstart` with `touches.length >= 2` intercepts native mobile pinch-to-zoom, abruptly locking screen into disguise |
| **FE-08** | **P1** | Layout Collision | `src/components/PanicExit.astro:10`<br>`src/components/tools/ContraceptionMatrix.astro:434`<br>`src/components/tools/PositionAndIntimacyGuide.astro:430` | Floating comparison bar covers Panic Exit button at `bottom-20`; tapping "PK 对比" inadvertently triggers panic mode |
| **FE-09** | **P1** | Mobile Clearance | `src/layouts/Base.astro:166-173` | Mobile bottom bar missing `env(safe-area-inset-bottom)`; touch targets collide with iOS Home Indicator bar |
| **FE-10** | **P2** | Client Routing | `src/components/DecisionGuide.astro:451-460` | Missing `hashchange` listener; in-page hash links (e.g. from SearchModal) fail to switch decision tree nodes |
| **FE-11** | **P2** | Client State | `src/layouts/Base.astro:231-232`<br>`src/pages/index.astro:250-264` | Duplicate click listeners on `#random-explore-btn` race to write conflicting URLs to `window.location.href` |
| **FE-12** | **P2** | DOM Security | `src/components/DecisionGuide.astro:185`<br>`src/components/tools/ContraceptionMatrix.astro:550`<br>`src/components/tools/PositionAndIntimacyGuide.astro:831` | JSON interpolated via `set:html` into `<script type="application/json">` without `<` escaping (contrast with `ArticleSchema.astro`) |
| **FE-13** | **P2** | Responsive Layout | `src/pages/articles/[id].astro:381-388` | Markdown tables in `.article-body` lack `display: block; overflow-x: auto`, causing horizontal viewport blowout on mobile |
| **FE-14** | **P2** | Render Performance | `src/components/TableOfContents.astro:88-156` | Duplicate `.toc-link` queries double `headingElements`; causes redundant `getBoundingClientRect` reads during scroll |
| **FE-15** | **P2** | Portability | `public/sw.js:11-20`<br>`public/manifest.webmanifest:5-24` | Hardcoded `/know-her/` prefix breaks custom root domain deployments (`https://know-her.pages.dev/`) |
| **FE-16** | **Pass** | DOM Security | Entire Codebase (`src/components/`) | Zero-innerHTML contract strictly respected; all client manipulation uses `createElement` / `textContent` / `replaceChildren` |

---

## 3. Deep Dive Findings & Concrete Failure Scenarios

### Finding FE-01: Precache Omits CSS & JS Bundles, Rendering Broken Offline DOM (P0)

- **Citations**:
  - `public/sw.js:11-20`:
    ```javascript
    const PRECACHE_ASSETS = [
      '/know-her/',
      '/know-her/tools/',
      '/know-her/guide/decision-tree/',
      '/know-her/glossary/',
      '/know-her/manifest.webmanifest',
      '/know-her/icon-192.svg',
      '/know-her/icon-512.svg',
      '/know-her/og-card.svg',
    ];
    ```
  - `public/sw.js:100-123`:
    ```javascript
    // B. 静态资源 (图片 / 样式 / 脚本 / 字体) -> Cache-First
    event.respondWith(
      caches.match(request).then((cachedResponse) => {
        if (cachedResponse) return cachedResponse;
        return fetch(request)
          ...
          .catch(() => new Response('', { status: 408, statusText: 'Offline Resource Unavailable' }));
      })
    );
    ```
- **Architectural Invariant**:
  An offline-first PWA must guarantee that all resources required to achieve a functional First Contentful Paint (FCP) and interactive state (TTI) are available offline upon installation.
- **Concrete Failure Scenario**:
  1. A user visits the know-her homepage `https://rom4n2.github.io/know-her/` while online and adds the app to their home screen or allows Service Worker registration.
  2. The Service Worker installs and caches the 4 raw HTML documents and 4 SVG/manifest files listed in `PRECACHE_ASSETS`.
  3. The user never navigates to `/know-her/tools/` or `/know-her/guide/decision-tree/` during this initial session.
  4. Later, in an urgent offline scenario (e.g., flight, subway without signal, emergency contraceptive incident), the user opens the PWA and navigates to the Emergency Decision Tree (`/know-her/guide/decision-tree/`) or Tools (`/know-her/tools/`).
  5. The Service Worker catches the network failure and returns the cached HTML document.
  6. The browser parses the HTML and immediately requests `<link rel="stylesheet" href="/know-her/_astro/index.[hash].css">` and `<script src="/know-her/_astro/hoisted.[hash].js">`.
  7. Because the user never visited these pages while online, these hashed bundles were never added to the runtime cache. The Service Worker intercepts the requests, fails to fetch them from the network, and returns a `408 Offline Resource Unavailable` response.
  8. **Outcome**: The user is presented with unstyled, broken HTML. Zero CSS styling is applied, and zero interactive scripts are loaded. All calculators, emergency countdowns, and decision tree options are inert and unclickable. The promised offline emergency utility fails completely.
- **Technical Remediation**:
  1. Integrate an Astro Service Worker build integration or Workbox build plugin to dynamically populate `PRECACHE_ASSETS` with build-generated `_astro/*.css` and `_astro/*.js` hashes at compile time.
  2. Alternatively, during the `install` event, fetch the HTML of precached pages, parse their `<link rel="stylesheet">` and `<script src="...">` tags, and atomically add those subresources to the cache.

---

### Finding FE-02: Query Parameter Miss in Service Worker Navigation Matching Serves Wrong Route (P1)

- **Citations**:
  - `public/sw.js:66-96`:
    ```javascript
    const cachedPage = await caches.match(request);
    if (cachedPage) return cachedPage;

    // 若目标页面未被独立缓存，回退至离线工具箱或应急决策树
    const emergencyGuide = await caches.match('/know-her/guide/decision-tree/');
    if (emergencyGuide) return emergencyGuide;

    const toolsPage = await caches.match('/know-her/tools/');
    if (toolsPage) return toolsPage;
    ```
  - `src/components/SearchModal.astro:13-16`:
    `href: `${base}tools/?tool=ec-countdown``
- **Architectural Invariant**:
  Navigation cache lookup must handle search query parameters gracefully, normalizing URLs or enabling query-agnostic cache matching.
- **Concrete Failure Scenario**:
  1. The user is offline with pre-cached assets.
  2. The user taps a search result shortcut pill or opens a saved bookmark: `/know-her/tools/?tool=ec-countdown`.
  3. The Service Worker attempts `caches.match(request)`. In the Cache Storage API, `caches.match` performs an exact string match on the request URL including search parameters unless `{ ignoreSearch: true }` is passed.
  4. Because `PRECACHE_ASSETS` stored `/know-her/tools/` (without query parameters), `caches.match(request)` returns `undefined`.
  5. Line 84 executes: `caches.match('/know-her/guide/decision-tree/')`. This matches successfully!
  6. **Outcome**: The Service Worker serves the HTML of `/know-her/guide/decision-tree/` to the browser, completely overriding the user's intent to view the emergency contraception countdown tool! The user asked for a 72h pill countdown and gets a decision tree instead.
- **Technical Remediation**:
  Use `{ ignoreSearch: true }` in `caches.match(request, { ignoreSearch: true })`, or strip `url.search` when checking against the navigation cache.

---

### Finding FE-03: Static `CACHE_NAME` Without Build-Hash Bumping Causes Permanent Stale Cache (P1)

- **Citations**:
  - `public/sw.js:9`:
    `const CACHE_NAME = 'know-her-offline-v1';`
  - `public/sw.js:37-40`:
    `cacheNames.filter((name) => name.startsWith('know-her-') && name !== CACHE_NAME).map((staleCache) => caches.delete(staleCache))`
  - `public/sw.js:100-117`:
    `caches.match(request).then((cachedResponse) => { if (cachedResponse) return cachedResponse; ... })`
- **Architectural Invariant**:
  Static assets without content-hash filenames must not be cached indefinitely without cache-busting or `stale-while-revalidate` policies.
- **Concrete Failure Scenario**:
  1. In production, `public/sw.js` specifies `know-her-offline-v1`.
  2. Developers update `public/manifest.webmanifest`, `public/og-card.svg`, or `pagefind/pagefind.js`.
  3. Because `CACHE_NAME` is hardcoded and not tied to `git rev-parse HEAD` or package version, the browser's Service Worker never enters the `activate` cleanup phase.
  4. The static fetch handler serves these assets via strict `Cache-First`: once an asset is stored in `know-her-offline-v1`, it is NEVER fetched from the network again.
  5. **Outcome**: Users are permanently stuck on stale manifest metadata, stale Pagefind search indexes, and old assets until they manually clear their site storage.
- **Technical Remediation**:
  Adopt `stale-while-revalidate` for unhashed static assets, or inject a build-time timestamp/git hash into `CACHE_NAME` during Astro build.

---

### Finding FE-04: Inline vs Module Hydration Timing Race in Tools Aggregator (P1)

- **Citations**:
  - `src/pages/tools/index.astro:223-306`:
    ```javascript
    <script is:inline>
      ...
      var categoryParam = params.get('category');
      var itemParam = params.get('item');
      if (toolId === 'report-decoder') {
        if (typeof window.selectReportDecoderItem === 'function') {
          window.selectReportDecoderItem(categoryParam, itemParam);
        } else {
          if (categoryParam) {
            var catBtn = document.querySelector('.decoder-category-tab[data-category-id="' + categoryParam + '"]');
            if (catBtn) catBtn.click();
          }
          if (itemParam) {
            var itemCard = document.querySelector('.decoder-item-card[data-item-id="' + itemParam + '"]');
            if (itemCard) itemCard.click();
          }
        }
      }
    </script>
    ```
  - `src/components/tools/ReportDecoder.astro:366`:
    `<script>` (compiled as ES Module `<script type="module">`).
  - `src/components/tools/ReportDecoder.astro:568-586`:
    `categoryTabs.forEach(tab => tab.addEventListener('click', ...))`
- **Architectural Invariant**:
  Script coordination across components must respect the browser parsing lifecycle: synchronous inline scripts execute before deferred ES module scripts.
- **Concrete Failure Scenario**:
  1. User navigates to `/know-her/tools/?tool=report-decoder&category=ultrasound&item=pelvic_free_fluid`.
  2. During HTML parsing, the parser reaches `tools/index.astro` line 223 (`<script is:inline>`) and executes it synchronously.
  3. `window.selectReportDecoderItem` is evaluated: it is `undefined` because `ReportDecoder.astro`'s script is an ES module that has not executed yet.
  4. Execution falls into the `else` branch: `catBtn.click()` and `itemCard.click()`.
  5. The `.click()` events dispatch immediately and bubble up the DOM.
  6. HOWEVER, `ReportDecoder.astro` has NOT registered its `addEventListener('click')` handlers yet (they are inside the unexecuted module script).
  7. **Outcome**: The clicks are completely ignored as no-ops. While `ReportDecoder.astro` lines 686-698 happens to contain an internal fallback that rescues initial cold page loads, any dynamic programmatic invocation or re-dispatch through `tools/index.astro` fails silently. The fallback code in `tools/index.astro` is dead code.
- **Technical Remediation**:
  Align script module types: convert `ReportDecoder.astro`'s script to `is:inline` or wrap `tools/index.astro`'s dispatch in `window.addEventListener('DOMContentLoaded', ...)` or custom event dispatching (`know-her:tool-ready`).

---

### Finding FE-05: Async Search Result Overwrite Race in `SearchModal.astro` (P1)

- **Citations**:
  - `src/components/SearchModal.astro:193-271`:
    ```javascript
    async function performSearch(query) {
      if (!resultsContainer) return;
      selectedIndex = -1;

      if (!query) {
        resultsContainer.replaceChildren();
        if (intentsContainer) intentsContainer.style.display = 'block';
        return;
      }

      if (intentsContainer) intentsContainer.style.display = 'none';
      const pf = await loadPagefind();
      const search = await pf.search(query);
      ...
      const data = await Promise.all(search.results.slice(0, 5).map((r) => r.data()));
      const fragment = document.createDocumentFragment();
      ...
      resultsContainer.replaceChildren(fragment);
    }
    ```
  - `src/components/SearchModal.astro:273-278`:
    ```javascript
    input?.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        performSearch(input.value.trim());
      }, 120);
    });
    ```
- **Architectural Invariant**:
  Asynchronous search handlers must discard stale responses when subsequent user input supersedes previous queries.
- **Concrete Failure Scenario**:
  1. User opens the search modal (⌘K) and types "避孕".
  2. After 120ms, `performSearch("避孕")` is called (Invocation A). Invocation A awaits `loadPagefind()`, `pf.search()`, and `r.data()`.
  3. The user immediately presses Backspace to clear the input because they want to use one of the shortcut pills instead.
  4. After 120ms, `performSearch("")` is called (Invocation B). Because `query` is empty, Invocation B runs synchronously: it clears `resultsContainer` and shows `intentsContainer`.
  5. 80ms later, Invocation A finishes fetching result data from the WASM index. It has NO query check (`input.value.trim() !== query`) and NO request token counter.
  6. Invocation A executes line 270: `resultsContainer.replaceChildren(fragment)`.
  7. **Outcome**: The search modal now displays search results for "避孕" underneath a completely EMPTY input field, while the intent shortcut pills are simultaneously shown or visually jumbled.
- **Technical Remediation**:
  Introduce a monotonically increasing sequence counter `currentSearchId`:
  ```javascript
  let activeSearchId = 0;
  async function performSearch(query) {
    const searchId = ++activeSearchId;
    ...
    const data = await Promise.all(...);
    if (searchId !== activeSearchId || input.value.trim() !== query) return;
    resultsContainer.replaceChildren(fragment);
  }
  ```

---

### Finding FE-06: Background Tab Suspension Halts 2-Hour Clinical Emergency Timer (P1)

- **Citations**:
  - `src/components/tools/EmergencyCountdown.astro:345-398`:
    ```javascript
    const VOMIT_OBSERVE_SECONDS = 120 * 60;
    let vomitTimerId = null;
    let vomitRemaining = VOMIT_OBSERVE_SECONDS;
    ...
    vomitTimerId = setInterval(() => {
      vomitRemaining -= 1;
      if (vomitRemaining <= 0) {
        completeVomitTimer();
        return;
      }
      renderVomitTimer();
    }, 1000);
    ```
- **Architectural Invariant**:
  Time-critical clinical tools must derive elapsed time from high-precision wall-clock timestamps (`Date.now()`), never from accumulated `setInterval` execution counts.
- **Concrete Failure Scenario**:
  1. A patient takes an emergency contraceptive pill (e.g. 1.5mg Levonorgestrel) following contraceptive failure.
  2. She taps `[ 我已服药，开启 2 小时吸收观察计时 ]` in know-her at 14:00.
  3. She locks her mobile phone and rests.
  4. On iOS Safari and Android Chrome, backgrounded tabs have their timer threads throttled to 1 tick per minute or suspended entirely.
  5. At 16:15 (2 hours and 15 minutes later, when gastric absorption is 100% complete and no re-medication is necessary under WHO guidelines), she wakes up feeling nauseous and checks her phone.
  6. Because the browser suspended the timer while locked, the counter only ticked 20 times. The display reads: "剩余 1 小时 58 分钟 (观察中：2 小时内呕吐需原剂量补服)".
  7. She vomits at 16:20. Believing the tool that she is still within the 2-hour window, she takes an unnecessary second dose of emergency contraception.
  8. **Outcome**: Excessive hormone exposure, heightened severe side effects (headache, vomiting, uterine bleeding), and clinical guidance violation caused directly by client-side timer inaccuracy.
- **Technical Remediation**:
  Store the start epoch timestamp in localStorage/memory and compute remaining seconds dynamically:
  ```javascript
  const startTime = Date.now();
  const endTime = startTime + VOMIT_OBSERVE_SECONDS * 1000;
  function tick() {
    vomitRemaining = Math.max(0, Math.ceil((endTime - Date.now()) / 1000));
    ...
  }
  ```

---

### Finding FE-07: Touch Gesture Conflict Intercepts Native Mobile Pinch-to-Zoom (P1)

- **Citations**:
  - `src/components/PanicExit.astro:315-319`:
    ```javascript
    // 移动端/触屏：双指同时触碰屏幕快速触发避险
    window.addEventListener('touchstart', (e) => {
      if (e.touches.length >= 2 && !isMasked) {
        mask();
      }
    }, { passive: true });
    ```
  - `src/layouts/Base.astro:64`:
    `<meta name="viewport" content="width=device-width, initial-scale=1" />`
- **Architectural Invariant**:
  Accessibility and touch gestures must not usurp standard browser viewport interactions (such as two-finger pinch-to-zoom) without directional or distance thresholds.
- **Concrete Failure Scenario**:
  1. A user on a smartphone views a dense comparison table (e.g. `ContraceptionMatrix` or `ReportDecoder`).
  2. The user places two fingers on the glass to perform a standard pinch-to-zoom gesture to read small table typography.
  3. The moment both fingers touch the screen, a `touchstart` event fires with `e.touches.length === 2`.
  4. `PanicExit.astro` immediately triggers `mask()`.
  5. **Outcome**: The entire viewport is instantly replaced by the "工作备忘录 - 每日待办事项" disguise screen. The pinch-to-zoom action is canceled, and the user believes the page crashed or redirected without warning.
- **Technical Remediation**:
  Remove the raw `e.touches.length >= 2` trigger, or require an explicit two-finger double-tap gesture, or restrict panic activation to a dedicated UI button.

---

### Finding FE-08: Fixed Element Collision Between Floating Bar and Panic Button (P1)

- **Citations**:
  - `src/components/PanicExit.astro:10`:
    `class="fixed bottom-20 sm:bottom-6 right-4 sm:right-6 z-40 ..."`
  - `src/components/tools/ContraceptionMatrix.astro:434`:
    `class="matrix-floating-bar fixed bottom-20 sm:bottom-6 left-1/2 -translate-x-1/2 z-40 max-w-xl w-[calc(100%-2rem)] ..."`
  - `src/components/tools/PositionAndIntimacyGuide.astro:430`:
    `class="position-floating-bar fixed bottom-20 sm:bottom-6 left-1/2 -translate-x-1/2 z-40 max-w-xl w-[calc(100%-2rem)] ..."`
  - `src/layouts/Base.astro:246`:
    `<PanicExit />` mounted at the end of `<body>`.
- **Architectural Invariant**:
  Fixed interactive UI components must not occupy overlapping viewport coordinates at the same z-index tier.
- **Concrete Failure Scenario**:
  1. A mobile user selects two methods in `ContraceptionMatrix` to compare them.
  2. The bottom floating comparison bar activates at `bottom-20` (`z-40`), spanning `w-[calc(100%-2rem)]` centered, leaving 1rem (16px) margin on the left and right.
  3. The Panic Exit trigger button is fixed at `bottom-20 right-4` (16px from the right edge) with `z-40`.
  4. Because `PanicExit.astro` is rendered at line 246 of `Base.astro` (after `<main>`), it sits HIGHER in DOM stacking order.
  5. The Panic Exit button (`[ 便签模式 ]`) physically overlaps the right action buttons of the floating bar ("查看横向 PK 对比" / "清空").
  6. **Outcome**: When the user taps "查看横向 PK 对比", the tap hits `#panic-trigger-btn` instead. Instead of opening the comparison dialog, the page vanishes into the Panic Disguise view.
- **Technical Remediation**:
  Offset the floating bar or panic trigger: shift `#panic-trigger-btn` to `bottom-36` when floating bars are visible, or dock the comparison bar above the panic button.

---

### Finding FE-09: Mobile Bottom Navigation Bar Collides with iOS Home Indicator (P1)

- **Citations**:
  - `src/layouts/Base.astro:165-173`:
    ```html
    <nav
      class="sm:hidden fixed bottom-0 left-0 right-0 z-50 bg-[#FAF8F5]/95 backdrop-blur-md border-t border-[#15140F]/10 px-2 py-1.5 flex items-center justify-around shadow-[0_-4px_16px_rgba(21,20,15,0.06)]"
      aria-label="移动端快捷导航"
    >
      <a href={base} class:list={['flex flex-col items-center justify-center min-w-[48px] min-h-[44px]', ...]}>
    ```
- **Architectural Invariant**:
  Fixed bottom navigation bars on modern mobile devices must account for the system safe area inset (`env(safe-area-inset-bottom)`).
- **Concrete Failure Scenario**:
  1. An iOS user (iPhone X through iPhone 16) browses know-her.
  2. The system home indicator bar (height 34px) sits at the bottom edge of the screen.
  3. `Base.astro` fixes the navigation bar to `bottom-0` with only `py-1.5` (6px top/bottom padding).
  4. The 44px touch targets ("首页", "应急", "工具", "词典", "漫游") sit directly on top of the home indicator.
  5. **Outcome**: Users attempting to tap navigation icons frequently trigger the iOS Home gesture (swiping to the home screen or invoking the app switcher) instead of navigating.
- **Technical Remediation**:
  Add safe area padding to the bottom bar:
  `class="... pb-[calc(0.375rem+env(safe-area-inset-bottom))]"`
  and increase `<main>` mobile bottom padding accordingly (`pb-28`).

---

### Finding FE-10: Missing `hashchange` Listener Breaks In-Page Decision Tree Routing (P2)

- **Citations**:
  - `src/components/DecisionGuide.astro:451-460`:
    ```javascript
    // Hash 监听直达特定分类
    const hash = window.location.hash;
    if (hash === '#condom') {
      showNode('node_condom_time');
    } else if (hash === '#missed-pill') {
      showNode('node_pill_days');
    } else if (hash === '#bleeding') {
      showNode('node_bleeding_timing');
    }
    ```
- **Architectural Invariant**:
  Hash-based routing must respond to dynamic `hashchange` events, not just initial page load inspection.
- **Concrete Failure Scenario**:
  1. A user is currently on `/know-her/guide/decision-tree/`.
  2. She presses ⌘K to open `SearchModal`, sees the shortcut pill `避孕套滑脱` (`/know-her/guide/decision-tree/#condom`), and clicks it.
  3. The browser updates `window.location.hash` to `#condom`.
  4. Because `DecisionGuide.astro` only checked `window.location.hash` on initial load, no route update occurs.
  5. **Outcome**: The decision tree remains on whatever node the user was previously viewing; clicking shortcut pills while on the page does nothing.
- **Technical Remediation**:
  Wrap hash handling in a function and listen to `hashchange`:
  ```javascript
  function handleHash() { ... }
  window.addEventListener('hashchange', handleHash);
  handleHash();
  ```

---

### Finding FE-11: Duplicate Click Listeners on Homepage Random Explore Button (P2)

- **Citations**:
  - `src/layouts/Base.astro:231-232`:
    `document.getElementById('random-explore-btn')?.addEventListener('click', triggerRandomArticle);`
  - `src/pages/index.astro:250-264`:
    `randomBtn.addEventListener('click', () => { ... window.location.href = target; });`
- **Architectural Invariant**:
  Event handlers for shared UI elements must have a single authoritative registrar to prevent conflicting concurrent side effects.
- **Concrete Failure Scenario**:
  1. User is on the homepage and clicks `#random-explore-btn` ("随便逛逛").
  2. Both `Base.astro` and `index.astro` event listeners fire concurrently.
  3. Handler 1 selects a random article from `validArticleUrls` and assigns `window.location.href`.
  4. Handler 2 selects another random article from `articleCards` and assigns `window.location.href`.
  5. **Outcome**: Two navigation requests race against each other, causing unpredictable destination hops or abort errors in the browser network log.
- **Technical Remediation**:
  Remove the redundant listener in `src/pages/index.astro` and let `src/layouts/Base.astro` handle `#random-explore-btn` globally.

---

### Finding FE-12: Unescaped JSON in `<script type="application/json">` via `set:html` (P2)

- **Citations**:
  - `src/components/DecisionGuide.astro:185`:
    `<script id="decision-tree-data" type="application/json" set:html={treeJson}></script>`
  - `src/components/tools/ContraceptionMatrix.astro:550`:
    `<script type="application/json" id="contraception-methods-data" set:html={methodsJson}></script>`
  - `src/components/tools/ClinicMemo.astro:570-572`:
    `<script type="application/json" id="clinic-configs-data" set:html={clinicConfigsJson}></script>`
  - `src/components/tools/PositionAndIntimacyGuide.astro:831-833`:
    `<script type="application/json" id="position-methods-data" set:html={positionsJson}></script>`
  - Contrasted with `src/components/ArticleSchema.astro:67`:
    `const jsonLd = JSON.stringify(payload).replace(/</g, '\\u003c');`
- **Architectural Invariant**:
  Any JSON string injected into an HTML `<script>` block must escape the `<` character (`\u003c`) to prevent premature script block closing (`</script>`) or parser confusion.
- **Concrete Failure Scenario**:
  If any clinical decision tree copy or user-contributed string contains the literal string `</script>`, the HTML parser terminates the JSON block prematurely, and the trailing content is parsed as active HTML, breaking JSON deserialization and opening a script injection vector.
- **Technical Remediation**:
  Apply `.replace(/</g, '\\u003c')` consistently to all JSON serializations passed to `set:html`.

---

### Finding FE-13: Markdown Tables Cause Horizontal Viewport Blowout on Mobile (P2)

- **Citations**:
  - `src/pages/articles/[id].astro:381-388`:
    ```css
    .article-body :global(table) {
      width: 100%;
      margin-top: 1.25rem;
      margin-bottom: 1.5rem;
      border-collapse: collapse;
      font-size: 0.85rem;
      border: 1px solid rgba(21, 20, 15, 0.12);
    }
    ```
- **Architectural Invariant**:
  Content tables rendered from Markdown must be contained within horizontal scroll containers to avoid expanding the mobile viewport width.
- **Concrete Failure Scenario**:
  1. A user reads an article on mobile (375px screen width).
  2. The article contains a 4-column comparison table (e.g. contraception method comparisons or lab value ranges).
  3. In CSS, `table` elements ignore `overflow-x: auto` unless styled as `display: block` or enclosed in a block wrapper.
  4. The table enforces minimum column widths and expands to ~480px.
  5. **Outcome**: The entire page develops unconstrained horizontal scrolling, causing the header, text, and layout to wobble side-to-side during vertical scrolling.
- **Technical Remediation**:
  Add `display: block; max-width: 100%; overflow-x: auto;` to `.article-body :global(table)`.

---

### Finding FE-14: Duplicate DOM Querying and Redundant Layout Thrashing in `TableOfContents.astro` (P2)

- **Citations**:
  - `src/components/TableOfContents.astro:88-97`:
    ```typescript
    const links = document.querySelectorAll<HTMLAnchorElement>('.toc-link');
    const headingIds = Array.from(links)
      .map((link) => link.getAttribute('data-slug'))
      .filter((slug): slug is string => Boolean(slug));

    const headingElements = headingIds
      .map((id) => document.getElementById(id))
      .filter((el): el is HTMLElement => Boolean(el));
    ```
  - `src/components/TableOfContents.astro:134`:
    `headingElements.forEach((h) => observer.observe(h));`
  - `src/components/TableOfContents.astro:148-154`:
    ```typescript
    for (const h of headingElements) {
      const rect = h.getBoundingClientRect();
      ...
    }
    ```
- **Architectural Invariant**:
  DOM queries for element sets must deduplicate identifiers before observing or measuring layout.
- **Concrete Failure Scenario**:
  `TableOfContents.astro` includes both mobile `<details>` and desktop `<div>` TOC trees, each with `.toc-link`. `querySelectorAll('.toc-link')` matches both sets, creating a list where every heading slug is duplicated.
  1. `observer.observe(h)` is invoked TWICE for every heading.
  2. During rapid scroll events, `headingElements` iterates through all elements twice, calling `h.getBoundingClientRect()` redundantly and inducing unnecessary CPU overhead during mobile scrolling.
- **Technical Remediation**:
  Deduplicate slugs via `new Set()`:
  `const headingIds = Array.from(new Set(Array.from(links).map(...)))`

---

### Finding FE-15: Hardcoded `/know-her/` Prefix Breaks Root-Domain Deployments (P2)

- **Citations**:
  - `public/sw.js:11-20`:
    `'/know-her/', '/know-her/tools/', '/know-her/guide/decision-tree/', ...`
  - `public/manifest.webmanifest:5-24`:
    `"start_url": "/know-her/tools/", "scope": "/know-her/", ...`
- **Architectural Invariant**:
  PWA assets must be portable across GitHub Pages subpath mounting and root-domain edge hosting (e.g. Cloudflare Pages).
- **Concrete Failure Scenario**:
  When deploying know-her to Cloudflare Pages (e.g. `https://know-her.pages.dev/`), the base path is `/` instead of `/know-her/`.
  1. The browser requests `/sw.js`.
  2. During the `install` event, `cache.addAll(PRECACHE_ASSETS)` attempts to fetch `/know-her/tools/`.
  3. Cloudflare Pages returns 404.
  4. **Outcome**: Because `cache.addAll()` is atomic, any 404 rejects the promise and aborts Service Worker installation entirely.
- **Technical Remediation**:
  Use relative paths in `sw.js` (e.g. `./`, `./tools/`, `./manifest.webmanifest`) or generate `sw.js` dynamically during build using `import.meta.env.BASE_URL`.

---

### Finding FE-16: Zero-innerHTML Contract Compliance (Pass)

- **Citations**:
  - `src/components/SearchModal.astro:247-265`
  - `src/components/PanicExit.astro:168-215`
  - `src/components/tools/ReportDecoder.astro:462-484`
  - `src/components/tools/ContraceptionMatrix.astro:875-950`
  - `src/components/tools/PositionAndIntimacyGuide.astro:1091-1350`
  - `src/components/tools/ClinicMemo.astro:601-1090`
  - `src/components/DecisionGuide.astro:258-286`
- **Architectural Assessment**:
  A comprehensive audit of the entire client-side codebase revealed ZERO assignments to `element.innerHTML` or `element.outerHTML`.
  - All dynamic list rendering uses `document.createElement`, `document.createTextNode`, `textContent`, `setAttribute`, and `replaceChildren`.
  - Rich excerpt text from Pagefind (containing `<mark>` tags) is sanitized through tokenized string splitting and mapped into native DOM nodes (`document.createElement('mark')` and text nodes).
  - **Verdict**: Fully compliant with the Zero-innerHTML DOM security invariant.

---

## 4. Verification & Contracts Health Check

The following automated validation checks were executed in the worktree environment:

```bash
# 1. Astro & TypeScript compiler check
pnpm check
# Result: 0 errors, 0 warnings, 1 hint (Zod .url() deprecation note)

# 2. PWA Specification & Contract Test
python -X utf8 scripts/test_pwa_contracts.py
# Result: Manifest, Service Worker, and Base.astro contracts pass structural checks.

# 3. Reading UX & Search Modal Contract Test
python -X utf8 scripts/test_reading_ux.py
# Result: TableOfContents, ReadingProgress, and SearchModal contracts pass.
```

---

## 5. Prioritized Action Matrix for Engineering

1. **Immediate P0 Action**:
   - Resolve **FE-01**: Implement compile-time precache injection so that Vite-bundled CSS and JS subresources are precached during Service Worker install, ensuring genuine offline functionality.
2. **High-Priority P1 Actions**:
   - Resolve **FE-02**: Pass `{ ignoreSearch: true }` in `public/sw.js` navigation cache lookups.
   - Resolve **FE-05**: Add request sequence token / freshness guard to `SearchModal.astro`'s `performSearch()`.
   - Resolve **FE-06**: Refactor `EmergencyCountdown.astro`'s 2h timer to compute remaining time from `Date.now()`.
   - Resolve **FE-07**: Remove two-finger raw `touchstart` interception in `PanicExit.astro`.
   - Resolve **FE-08**: Decouple the spatial layout of `PanicExit` and the comparison floating bar (`ContraceptionMatrix` / `PositionAndIntimacyGuide`).
   - Resolve **FE-09**: Add `pb-[calc(0.375rem+env(safe-area-inset-bottom))]` to `Base.astro`'s mobile bottom navigation bar.
3. **P2 Polish Actions**:
   - Resolve **FE-10**: Add `hashchange` listener in `DecisionGuide.astro`.
   - Resolve **FE-11**: Remove redundant click listener on `#random-explore-btn` in `src/pages/index.astro`.
   - Resolve **FE-12**: Add `<` escaping (`\u003c`) to all JSON data scripts using `set:html`.
   - Resolve **FE-13**: Add `display: block; max-width: 100%; overflow-x: auto;` to markdown tables in `articles/[id].astro`.
   - Resolve **FE-14**: Deduplicate heading IDs with `Set` in `TableOfContents.astro`.
