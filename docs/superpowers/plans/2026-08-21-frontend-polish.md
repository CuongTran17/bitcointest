# Frontend Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or **superpowers:executing-plans** to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refresh the existing Local Bitcoin Bank frontend into a cohesive, readable fintech-style dashboard without changing backend APIs or feature behavior.

**Architecture:** Keep the current React component boundaries and data-loading flow. Centralize visual decisions in `styles.css` through CSS variables and shared utility classes, then update components to consume those styles instead of inline presentation rules. Improve layout and responsive behavior in place rather than introducing a UI framework or new dependency.

**Tech Stack:** React, TypeScript, Vite, plain CSS, existing component structure, existing backend API.

**Spec:** Approved frontend polish direction in chat on 2026-08-21: clean fintech dashboard, light neutral background, white surfaces, navy text, blue accent, semantic status colors, consistent spacing, improved responsive behavior, and no backend/API changes.

## Global Constraints

- Preserve all existing API contracts and user flows: wallet switching, faucet, send, mine, transaction detail, UTXO, mempool, and block explorer.
- Do not add a UI framework, icon library, font dependency, or other package.
- Keep Bitcoin values and transaction data unchanged; this work is presentation-only.
- Keep component responsibilities and existing request race protection intact.
- Remove inline visual styles from touched components and replace them with named CSS classes.
- Preserve the pre-existing untracked `backend/package-lock.json`; do not add, delete, or modify it.
- Keep the frontend build passing after every task.

---

### Task 1: Establish the shared visual system

**Files:**
- Modify: `frontend/src/styles.css`
- Test: `frontend/npm.cmd run build`

**Interfaces:**
- Produces shared CSS variables and utility classes consumed by all existing components.
- Does not change TypeScript props, API calls, or rendered data.

- [ ] **Step 1: Record the current frontend baseline**

Run:

```powershell
cd frontend
npm.cmd run build
cd ..
git diff --check
```

Expected: the current production build succeeds and there are no whitespace errors.

- [ ] **Step 2: Add design tokens**

At the top of `frontend/src/styles.css`, add a `:root` block with tokens for:

```css
:root {
  --color-bg: #f4f7fb;
  --color-surface: #ffffff;
  --color-surface-muted: #f8fafc;
  --color-text: #172033;
  --color-text-muted: #667085;
  --color-border: #e4e7ec;
  --color-border-strong: #cfd5df;
  --color-accent: #2563eb;
  --color-accent-dark: #1d4ed8;
  --color-success: #15803d;
  --color-warning: #b45309;
  --color-danger: #b42318;
  --radius-sm: 8px;
  --radius-md: 12px;
  --shadow-panel: 0 8px 24px rgba(16, 24, 40, 0.06);
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
}
```

Use the tokens for the existing `body`, `.panel`, buttons, inputs, labels, borders, and spacing rules. Keep the visual result light and low-contrast; do not introduce dark mode or gradients in this task.

- [ ] **Step 3: Normalize shared controls and focus states**

Update shared selectors so buttons, inputs, and selects have consistent height, radius, border, transition, and focus-visible treatment. Add explicit styles for:

```css
button:hover:not(:disabled) { ... }
button:focus-visible,
input:focus-visible,
select:focus-visible { ... }
button:disabled { ... }
```

Use classes for secondary/quiet actions where needed; do not make every button visually primary.

- [ ] **Step 4: Verify the visual-system slice**

Run:

```powershell
cd frontend
npm.cmd run build
cd ..
git diff --check
```

Expected: PASS with no TypeScript or CSS-related build errors.

- [ ] **Step 5: Commit the shared visual system**

```powershell
git add frontend/src/styles.css
git commit -m "style: establish frontend visual system"
```

### Task 2: Refresh app shell, wallet controls, and dashboard hierarchy

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/UserSwitcher.tsx`
- Modify: `frontend/src/components/WalletDashboard.tsx`
- Modify: `frontend/src/components/ReceivePanel.tsx`
- Modify: `frontend/src/components/SendPanel.tsx`
- Modify: `frontend/src/components/MineButton.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes existing component props and callbacks unchanged.
- Produces a clearer header, wallet selector, balance area, and primary wallet actions.

- [ ] **Step 1: Add semantic layout classes without changing behavior**

In `App.tsx`, wrap the existing header actions and wallet/dashboard area with named classes such as `app-header`, `brand-block`, `primary-actions`, `wallet-section`, and `activity-section`. Keep every existing callback and state value unchanged.

- [ ] **Step 2: Improve the wallet selector**

Update `UserSwitcher.tsx` to render a clear section label and selected-wallet context. Preserve the existing `users`, `selectedWallet`, and `onSelect` props. Use a shared `segmented-control` or `wallet-switcher` class rather than inline styling.

- [ ] **Step 3: Improve the balance panel**

Update `WalletDashboard.tsx` to make the total balance the visual anchor and place confirmed/unconfirmed values into compact stat items. Do not rename API fields or alter formatting values supplied by the component.

- [ ] **Step 4: Separate primary and secondary actions**

Use primary styling for faucet/send where appropriate and secondary styling for receive/mine or utility actions. Add visible labels and disabled states without changing event handlers. Keep the send and receive forms usable on narrow screens.

- [ ] **Step 5: Add shell and dashboard styles**

Update `styles.css` for:

- a wider but controlled app shell;
- a compact brand/header hierarchy;
- a wallet summary surface with stronger spacing;
- responsive action groups;
- consistent panel headings and section labels;
- no nested decorative cards inside existing panels.

- [ ] **Step 6: Verify the shell slice**

Run:

```powershell
cd frontend
npm.cmd run build
cd ..
git diff --check
```

Expected: PASS, with no changes to backend behavior.

- [ ] **Step 7: Commit the shell slice**

```powershell
git add frontend/src/App.tsx frontend/src/components/UserSwitcher.tsx frontend/src/components/WalletDashboard.tsx frontend/src/components/ReceivePanel.tsx frontend/src/components/SendPanel.tsx frontend/src/components/MineButton.tsx frontend/src/styles.css
git commit -m "style: improve wallet dashboard hierarchy"
```

### Task 3: Polish transaction activity and detail surfaces

**Files:**
- Modify: `frontend/src/components/TransactionHistory.tsx`
- Modify: `frontend/src/components/TransactionDetailPanel.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Preserve existing transaction selection and detail callbacks.
- Preserve all displayed transaction values and raw JSON behavior.

- [ ] **Step 1: Improve transaction history rows**

Update `TransactionHistory.tsx` so each row has a clear primary direction, secondary metadata, right-aligned amount/status, and consistent selected/hover states. Keep txids as text and preserve the existing click behavior.

- [ ] **Step 2: Add reusable status and amount classes**

Use semantic classes for confirmed, pending, success, warning, and unknown states. Do not infer new transaction meaning; map only from existing `status` and category values.

- [ ] **Step 3: Improve transaction detail layout**

Update `TransactionDetailPanel.tsx` so the header, relationship metadata, confirmation/block metadata, inputs, outputs, and raw JSON are visually grouped. Keep nullable values rendered safely and keep the raw toggle behavior unchanged.

- [ ] **Step 4: Replace inline detail styling**

Move visual rules for detail sections, raw JSON, buttons, and columns into named CSS classes in `styles.css`. Keep data-specific values in JSX, not CSS.

- [ ] **Step 5: Verify activity surfaces**

Run:

```powershell
cd frontend
npm.cmd run build
cd ..
git diff --check
```

Expected: PASS.

- [ ] **Step 6: Commit the activity slice**

```powershell
git add frontend/src/components/TransactionHistory.tsx frontend/src/components/TransactionDetailPanel.tsx frontend/src/styles.css
git commit -m "style: polish transaction activity surfaces"
```

### Task 4: Polish UTXO, Mempool, and Block Explorer views

**Files:**
- Modify: `frontend/src/components/UtxoViewer.tsx`
- Modify: `frontend/src/components/MempoolView.tsx`
- Modify: `frontend/src/components/BlockExplorer.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Preserve all existing props, API calls, refresh handlers, and selection callbacks.
- Preserve table data, empty states, loading states, errors, and navigation behavior.

- [ ] **Step 1: Create shared data-view classes**

Add reusable classes for section headers, summary stat grids, status badges, data tables, hash cells, toolbar controls, and empty/error states. Use modifier classes for view-specific differences instead of duplicating complete style blocks.

- [ ] **Step 2: Improve UTXO Viewer**

Keep the summary visible above the table. Improve column hierarchy for txid/vout, address, amount, confirmations, and spendability. Use badges for confirmed/pending and spendable/watch-only. Keep `No address` and `No unspent outputs.` behavior unchanged.

- [ ] **Step 3: Improve Mempool View**

Keep the node-wide label visible. Improve the fee summary and table density, retain the `pending` status badge, and make wallet direction and fee metadata easier to scan. Keep horizontal scrolling for narrow screens.

- [ ] **Step 4: Improve Block Explorer**

Separate explorer toolbar, block list, selected block detail, navigation buttons, and transaction list visually. Keep the limit selector, direct lookup, previous/next navigation, shortened hashes, and title tooltips unchanged in behavior.

- [ ] **Step 5: Remove remaining inline presentation styles**

Move inline `style={{ ... }}` rules from the three components into named CSS classes. Do not change request logic or component props while doing this.

- [ ] **Step 6: Verify data views**

Run:

```powershell
cd frontend
npm.cmd run build
cd ..
git diff --check
```

Expected: PASS.

- [ ] **Step 7: Commit the data-view slice**

```powershell
git add frontend/src/components/UtxoViewer.tsx frontend/src/components/MempoolView.tsx frontend/src/components/BlockExplorer.tsx frontend/src/styles.css
git commit -m "style: polish blockchain data views"
```

### Task 5: Responsive, accessibility, and interaction pass

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/UserSwitcher.tsx`
- Modify: `frontend/src/components/TransactionHistory.tsx`
- Modify: `frontend/src/components/TransactionDetailPanel.tsx`
- Modify: `frontend/src/components/UtxoViewer.tsx`
- Modify: `frontend/src/components/MempoolView.tsx`
- Modify: `frontend/src/components/BlockExplorer.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- No API or state-shape changes.
- All existing loading/error/empty behavior remains available.

- [ ] **Step 1: Add responsive breakpoints**

Use a small set of breakpoints to support desktop, tablet, and narrow mobile layouts. At minimum verify widths around 1280px, 900px, 720px, and 390px. Keep wide tables horizontally scrollable and prevent buttons/forms from overflowing.

- [ ] **Step 2: Add accessibility semantics**

Ensure every input has an associated label or aria-label, buttons have descriptive names, selected rows expose a visible state, and focus-visible outlines remain clear. Use semantic headings in document order.

- [ ] **Step 3: Normalize interaction states**

Add consistent hover, focus, active, selected, disabled, loading, empty, error, and success states. Ensure disabled refresh buttons remain visually understandable and do not reduce text contrast excessively.

- [ ] **Step 4: Verify the responsive/accessibility slice**

Run:

```powershell
cd frontend
npm.cmd run build
cd ..
git diff --check
```

Then manually inspect the app at desktop and mobile widths while exercising wallet switch, send, faucet, mine, transaction selection, UTXO refresh, mempool refresh, block lookup, and block navigation.

- [ ] **Step 5: Commit the responsive pass**

```powershell
git add frontend/src/App.tsx frontend/src/components frontend/src/styles.css
git commit -m "style: improve responsive frontend interactions"
```

### Task 6: Final regression verification and documentation

**Files:**
- Modify: `README.md` only if the visible UI flow or screenshots/instructions changed.

**Interfaces:**
- Consumes the existing full application.
- Produces verification evidence that existing backend and frontend behavior remains intact.

- [ ] **Step 1: Run the full verification suite**

Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -v
cd ..\frontend
npm.cmd run build
cd ..
git diff --check
git status --short --branch
```

Expected:

- all backend tests pass;
- frontend production build passes;
- no whitespace errors;
- unrelated `backend/package-lock.json` remains untouched.

- [ ] **Step 2: Perform the manual UI acceptance pass**

Check:

1. App shell and wallet context are immediately understandable.
2. Balance and primary actions are visually prioritized.
3. Transaction history and detail selection remain functional.
4. UTXO, Mempool, and Block Explorer summary/data states are readable.
5. Loading, empty, error, and populated states are visually distinct.
6. Tables remain usable at narrow widths.
7. Keyboard focus is visible and forms are operable without a mouse.
8. Faucet, send, and mine flows still refresh the relevant views.

- [ ] **Step 3: Update README only when needed**

Do not add implementation details to README. Update only user-facing instructions if labels or the order of visible sections changed materially.

- [ ] **Step 4: Commit final documentation if changed**

```powershell
git add README.md
git commit -m "docs: update frontend usage notes"
```

## Final Acceptance Checklist

- [ ] Shared visual tokens are used across the frontend.
- [ ] Inline presentation styles are removed from touched components.
- [ ] Header, wallet switcher, balance, and actions have clear hierarchy.
- [ ] Transaction history and detail surfaces are easier to scan.
- [ ] UTXO, Mempool, and Block Explorer views use a consistent data-view style.
- [ ] Loading, empty, error, selected, hover, focus, and disabled states are consistent.
- [ ] Desktop, tablet, and mobile layouts remain usable.
- [ ] Existing API calls and user flows are unchanged.
- [ ] Backend tests pass.
- [ ] Frontend production build passes.
- [ ] `git diff --check` passes.
- [ ] README is updated only if user-facing flow changed.
