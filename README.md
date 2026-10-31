# Mudra — Attendance & Fees

A web app for **Mudra**, a Kuchipudi dance class. It handles attendance, students and monthly fees.
Google sign-in restricts it to allowed accounts, data syncs across her devices, and it works offline.
It costs ₹0 to run (Firebase free Spark plan).

| | TEST | PROD |
|---|---|---|
| Branch | `dev` | `main` |
| URL | https://mudra-925e7.web.app | `https://<prod-project-id>.web.app` |
| Firebase project | your test project | her prod project |
| Who can sign in | aamir.salam5@gmail.com | her Gmail (added later) |
| Data | sample/fake | her real data |

**Repo:** https://github.com/aamirsalam/mudra
**Local copy:** `C:\Users\Aamir\Documents\Projects\mudra`

> History: v1–v2 were offline-only (data in the browser, hosted on GitHub Pages at
> aamirsalam.github.io/mudra). v3 (this) adds Firebase for login, sync, and test/prod environments.

---

## 1. Client requirements

| # | Requirement | Notes |
|---|---|---|
| 1 | Mark attendance | Classes on certain weekdays, in batches |
| 2 | Add / remove students | Keep history when a student leaves |
| 3 | Track fees | Monthly. Due mid-month (15th). ₹1,000 now, may change |
| 4 | First-fee rule | Due on the *next* 15th after joining (joined 5 Oct → Oct fee; 20 Oct → first fee Nov). Not per class |
| 5 | Look back at past classes | "Was X absent that day?" / "Did X attend?" |
| 6 | WhatsApp fee reminders | Editable message |
| 7 | Free to run | No hosting or subscription cost |
| 8 | Surface Pro + phones | Touch-friendly. Android & iPhone |
| 9 | Name fixed as "Mudra" | Not editable in the app |
| 10 | **Only her** can use it | Others opening the link must not be able to use it |
| 11 | **Several devices** | Same data on her Surface and phone |
| 12 | **Test copy for Aamir** | Same app, separate data, his own login, never her account |

---

## 2. Architecture

```
                          GitHub: aamirsalam/mudra
                 ┌────────────────────┴────────────────────┐
             branch dev                                branch main
                 │  GitHub Actions (.github/workflows/deploy.yml)
                 ▼                                          ▼
   ┌─────────────────────────────┐            ┌─────────────────────────────┐
   │ Firebase project: TEST      │            │ Firebase project: PROD      │
   │  Hosting  → app files       │            │  Hosting  → app files       │
   │  Auth     → Google sign-in  │            │  Auth     → Google sign-in  │
   │  Firestore→ data + rules    │            │  Firestore→ data + rules    │
   │  access/allowlist: Aamir    │            │  access/allowlist: her      │
   └──────────────┬──────────────┘            └──────────────┬──────────────┘
                  ▼                                          ▼
          Aamir's browser                     Her Surface / phone (installed PWA)
                                              ├─ Service worker: app + SDK cached → opens offline
                                              └─ Firestore offline cache: data + queued writes
```

### Why this design
- **Firebase (free Spark plan)** gives hosting, Google sign-in and a database with **built-in offline
  sync** in one product. One class is far inside the free limits.
- **Security lives on the server.** `firestore.rules` only lets signed-in Google accounts listed in
  `access/allowlist` read or write. The page is public, but strangers just see "No access".
- **Two Firebase projects = two fully separate environments.** Different data, users and URLs. The same
  code runs in both, and only `config.js` differs.
- **The allowlist is data, not code.** You edit it in the Firebase console, so there's no deploy, and
  her email isn't in the public repo.
- **No build step / framework.** It's still one `index.html` with vanilla JS. The Firebase SDK is loaded
  from Google's CDN (pinned to v10.14.1).

**Alternatives considered:**
- Supabase: free projects pause after a week of inactivity, and it has no built-in offline sync.
- Google Sheets: slow, no offline support, fragile.
- Cloudflare Access: protects the site, but doesn't sync data.

---

## 3. Repository layout

```
public/                  ← everything that gets hosted
  index.html             the whole app (CSS + HTML + JS module)
  sw.js                  service worker (offline). __BUILD__ is replaced with the commit SHA on deploy
  manifest.json, icon-*.png
  config.js              GENERATED at deploy (copied from env/<target>.js) — git-ignored
env/
  test.js                Firebase web config for TEST   (fill in once)
  prod.js                Firebase web config for PROD   (fill in once)
firebase.json            hosting settings (no-cache headers) + rules file location
firestore.rules          allowlist-based access rules (same file for both envs)
firestore.indexes.json   empty (no composite indexes needed)
.github/workflows/deploy.yml   dev → test, main → prod
```

The Firebase web config (apiKey etc.) is **not a secret**. It only identifies the project.
Protection comes from the auth + rules.

---

## 4. How the app works (`public/index.html`)

### Data in Firestore
```
access/allowlist                          { emails: ["someone@gmail.com", ...] }   ← console only
studios/mudra                             { defaultFee, dueDay, waTemplate, lastBackup }
studios/mudra/batches/{id}                { name, days:[0-6], time }               0 = Sunday
studios/mudra/students/{id}               { name, phone, batchId, fee, joined, notes, active, left? }
studios/mudra/payments/{id}               { studentId, month:'YYYY-MM', amount, date, mode }
studios/mudra/attendance/{date|batchId}   { date, batchId, present:[studentId,...] }
```
- Attendance stores only the **present** IDs. A missing class doc means "not marked".
- Payments store the **amount actually paid**, so later fee changes don't rewrite history.

### Sync model
- The UI works on one in-memory `state` object, the same shape as the v2 offline app, so the screens
  didn't need rewriting.
- **Reading:** `subscribe()` opens live `onSnapshot` listeners on the settings doc plus the 4 collections.
  Any change, including from her other device, updates `state` and re-renders. If a dialog is open,
  the re-render waits until it closes.
- **Writing:** every change calls `save()`, which **diffs** `state` against what was last synced
  (key-order-independent JSON) and writes only the changed or deleted docs in a batch.
  Toggling one tile = 1 write.
- **Offline:** Firestore's `persistentLocalCache` keeps a local copy and queues writes until she
  reconnects. The service worker caches the app files and the Firebase SDK, so the app opens with no
  internet once she's signed in.
- Forms look objects up again by `id` on submit, so a sync arriving while a form is open can't lose the edit.

### Sign-in flow (`phase`)
`boot → signedout → (Google sign-in) → loading → ready`, or `denied` if the account isn't allowlisted
(the rules return `permission-denied`).
- Popup sign-in normally. Redirect sign-in when installed as an app (iOS PWA) or if a popup is blocked.
- `authDomain` is set to the site's own host so sign-in goes through `https://<host>/__/auth/handler`
  on Firebase Hosting. This avoids Safari/iOS third-party-storage problems. On localhost it uses
  `<project>.firebaseapp.com`.
- Sign-out also clears the local Firestore cache, so a shared device keeps no data.

### Upgrading from the offline-only version
If a device still has data from v1/v2 (IndexedDB `dance-register`) and the account is empty, a banner
offers **Upload**. It does this once per device.

### Fee logic
```
dueDate(m)      = m-15  (dueDay configurable)
firstMonth(s)   = joined <= dueDate(joinMonth) ? joinMonth : joinMonth + 1
billable(s,m)   = fee > 0 && m >= firstMonth(s) && (active || m <= left month)
feeStatus(s,m)  = paid | free | notyet | na | overdue | upcoming
```

### Screens
**Today** (tap to mark, change date to fix past) · **History** (by class: absentees and "not marked";
by student: calendar, %, unpaid months) · **Students** · **Fees** (Overdue → Due → First fee → Paid;
Mark paid / Undo / Remind) · **Reports** (CSV export) · **Settings** (account, batches, fee, due day,
WhatsApp template, backup/restore). "Load sample data" appears **only in TEST**.

The header shows a gold **TEST** tag in the test environment, so you never confuse it with prod.

### WhatsApp
**Remind** opens `wa.me/91…?text=…` with the message pre-filled, and she presses Send. Nothing is
automatic (that would need the paid Business API). It shows only for Due/Overdue fees on students who
have a phone number. Placeholders: `{name} {amount} {month} {due}`.

---

## 5. One-time setup (do this once per environment)

Do everything for **TEST** first. Repeat for **PROD** when you're ready to add her.

### A. Create the Firebase project
1. https://console.firebase.google.com → **Add project** → name it e.g. `mudra-test` (note the
   **project ID**, which may get a suffix). Google Analytics isn't needed.
2. **Build → Firestore Database → Create database** → location **asia-south1 (Mumbai)** →
   start in **production mode**.
3. **Build → Authentication → Get started → Sign-in method → Google → Enable**, then pick a support email.
4. **Project settings (gear) → General → Your apps → Web (`</>`)** → register an app (no hosting
   checkbox needed) → copy the `firebaseConfig` values into **`env/test.js`**.

### B. Allowlist
5. **Firestore → Start collection** `access` → document ID `allowlist` → field `emails`
   (type **array**) → add `aamir.salam5@gmail.com`.
   For PROD: add her Gmail here (and yours too, if she agrees to you having support access).

### C. Let sign-in work on the web.app domain
6. Google Cloud console for the same project → **APIs & Services → Credentials** → the OAuth client
   **"Web client (auto created by Google Service)"** → **Authorized redirect URIs** → add
   `https://<project-id>.web.app/__/auth/handler` → Save.
   (`<project-id>.web.app` is already an authorized domain in Firebase Auth by default. If you add a
   custom domain later, add it in both places.)

### D. Deploy credentials for GitHub Actions
7. Google Cloud console → **IAM & Admin → Service Accounts → Create** `github-deploy`, with roles:
   **Firebase Hosting Admin**, **Firebase Rules Admin**, **API Keys Viewer**, **Service Usage Consumer**.
   Then go to **Keys → Add key → JSON** and download it.
8. GitHub repo → **Settings → Environments → `test`** (created by the first workflow run, or create it)
   → **Add secret** `FIREBASE_SERVICE_ACCOUNT` = paste the whole JSON. Then delete the downloaded file.
   For PROD use environment `prod`. Optionally add **Required reviewers** so prod deploys need your approval.

### E. Deploy
9. Commit `env/test.js` and push to `dev`. The workflow deploys hosting + rules, and the run summary
   shows the URL.
10. Open `https://<project-id>.web.app` → sign in → **Settings → Load sample data** to play.

Until a secret or config is filled in, the workflow **skips with a warning** instead of failing.

---

## 6. Day-to-day workflow

```bash
git checkout dev
# edit public/index.html ...
git commit -am "Change X" && git push        # → deploys to TEST automatically
# check on the test URL, then:
git checkout main && git merge dev && git push   # → deploys to PROD
```
- No manual cache bumping: the workflow stamps `sw.js` with the commit SHA, so every deploy refreshes
  the offline cache. Devices pick it up the next time they open online (reload once or twice).
- **Add or remove a user:** edit `access/allowlist.emails` in that project's Firestore console. It takes
  effect immediately, with no deploy.
- **Rules change:** edit `firestore.rules` → push. The workflow deploys rules too.
- **Run locally:** `cp env/test.js public/config.js && npx firebase-tools serve --project <test-id>`
  (or any static server on `localhost`; localhost is an authorized domain).
- **Data model change:** settings get defaults from `fresh()`, so new fields are safe. Renaming fields
  needs a migration.

---

## 7. Her devices

- **Surface (Edge):** open the prod URL → ⋯ → **Apps → Install this site as an app**.
- **Android (Chrome):** ⋮ → **Install app**.
- **iPhone (Safari):** Share → **Add to Home Screen**.
- She signs in once per device with her Google account. After that it works offline, and all devices
  show the same data.
- **Backup:** Settings → Download backup gives a `.json` copy as an extra safety net. Restoring a backup
  replaces all cloud data.

---

## 8. Fixes & lessons learned

| Issue | Cause | Fix |
|---|---|---|
| Tabs overflowed on phones | 6 top tabs too wide | Bottom tab bar with icons at ≤ 640px |
| Date field overlapped Batch on iPhone | iOS date inputs ignore `width:100%` | `appearance:none; min-width:0` |
| iPhone zoomed in on form fields | iOS auto-zooms inputs < 16px | `font-size:16px` on all inputs |
| Fees hint squeezed on phones | inline flex | `.bar>.hint{flex:1 1 230px}` |
| Month text centred on iOS | WebKit default | `::-webkit-date-and-time-value{text-align:left}` |
| Old version cached after update | service worker | network-first SW + per-deploy cache name (commit SHA) |
| Anyone with the link could use it | static site, no auth | Google sign-in + Firestore rules allowlist |
| Separate data per device | browser-only storage | Firestore with offline cache |
| Write loops / extra writes risk | Firestore returns fields in a different order | diff uses key-sorted JSON |
| Edit lost if a sync arrives mid-form | snapshot replaces objects | forms re-look-up by `id` on submit |
| Claude couldn't create the repo / enable Pages | session API limits | done manually. Claude GitHub App installed for pushes |

---

## 9. Not built (ideas)
- Automatic WhatsApp sending (paid Business API)
- Per-class or term billing
- Roles (e.g. a read-only helper account)
