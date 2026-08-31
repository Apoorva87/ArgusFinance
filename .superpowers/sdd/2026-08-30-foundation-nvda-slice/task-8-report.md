# Task 8 Report: React market decision surface

## Scope

Implemented the local NVDA market observatory in `apps/dashboard/` at feature commit `393cfbb9459438e3bfbbf3366c6911de5e976428`.

## Design

- Tokens: `--ink #07131f`, `--panel #0f2233`, `--cloud #d9e7ef`, `--muted #8097a8`, `--signal #4fd1c5`, `--caution #f4b942`, with restrained `--error #ff6b6b`.
- The signature is a chronological, full-width expiration rail. It is the only initial-motion treatment and respects `prefers-reduced-motion`.
- The desktop surface uses an asymmetric liquidity/readout grid with hairline divisions; it stacks to one column at 700px and below. There are no strategy, payoff, trade, or recommendation controls.

## Files

- Vite/React/TypeScript metadata, exact-versioned scripts/dependencies, and pinned `package-lock.json` in `apps/dashboard/`.
- Typed relative API client and `MarketApiError` in `src/api/market.ts`.
- Snapshot view, expiration timeline, Plotly liquidity chart, accessible aggregate table, app load/error states, and responsive styles.
- Canonical deterministic NVDA test fixture plus component, API-client, and App-state tests in `src/`.

## TDD evidence

- RED: `npm test -- --run src/features/market/MarketSnapshotView.test.tsx` failed because `./MarketSnapshotView` did not exist. Vite reported: `Failed to resolve import "./MarketSnapshotView"`.
- GREEN focused: the same command passed with 3/3 tests after implementation.
- GREEN full: `npm test -- --run` passed: 1 file, 3 tests.
- Review regression tests: `src/api/market.test.ts` covers normalized relative request URLs and typed API errors; `src/App.test.tsx` covers loading, 404 capture guidance, and generic failure guidance. The API behavior already existed, so these tests were green on their first run; the App test first failed before execution because jsdom resolved Plotly's optional peer package, then passed after mocking only the renderer internals (the same test boundary as the existing chart test).

## Verification

- `npm run build` exited 0. Vite emitted the production bundle successfully.
- `git diff --check cb0c04d..HEAD` exited 0 after the report commit.
- Review verification: `npm ci` exited 0 with a clean reproducible install; focused and full Vitest runs passed 3 files / 8 tests; the production build exited 0.

## Accessibility and responsive self-critique

- Semantic landmark/headings, status regions, visible focus outline, readable status contrast, an accessible expiration list, and a captioned data table provide text equivalents for the chart.
- Delayed/frozen timestamps and missing Greeks stay explicit; missing Greek values are never converted to zero.
- The mobile rail remains horizontally readable and the analytical grid stacks without changing information order.

## Concerns/deviations

- The prior Node engine warning is resolved: all direct dependencies are exact-versioned and jsdom is pinned to `29.1.1`, whose declared Node range includes the local Node 25.8.1. Both `npm install` and `npm ci` completed without an `EBADENGINE` warning.
- Vite emitted its standard large-chunk advisory because bundled Plotly is approximately 4.3MB uncompressed / 1.3MB gzip. No data or UI behavior is affected; code splitting is deferred for this local first slice.
- Visual browser QA was unavailable to the controller because no browser instance was available. Code, build, responsive CSS, keyboard focus, reduced-motion, and accessible text-alternative review were completed instead.
