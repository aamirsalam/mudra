# Mudra — Attendance & Fees

A free, offline web app for **Mudra**, a Kuchipudi dance class. It marks attendance, manages
students and tracks monthly fees. No server, no login, no subscription.

**Live:** https://aamirsalam.github.io/mudra/
**Repo:** https://github.com/aamirsalam/mudra
**Local copy:** `C:\Users\Aamir\Documents\Projects\mudra`

---

## 1. Client requirements

| # | Requirement | Notes |
|---|---|---|
| 1 | Mark attendance for students | Classes run on certain days of the week, in batches |
| 2 | Add / remove students | Keep history when a student leaves |
| 3 | Track fee payments | Monthly. Due mid-month (15th). Currently ₹1,000, may change later |
| 4 | First-fee rule | Due on the *next* 15th after joining, not pro-rated or per class (joined 5 Oct → Oct fee; joined 20 Oct → first fee Nov) |
| 5 | Look back at past classes | "Was X absent that day?" / "Did X actually attend?" |
| 6 | WhatsApp fee reminders | Editable message text |
| 7 | Free to run | No hosting or subscription cost |
| 8 | Runs on her **Surface Pro** | Touch-friendly. Later also: **phone** (Android/iPhone) |
| 9 | Institute name fixed as "Mudra" | Not editable in the app, so it can't be rebranded by others |

---

## 2. Solution overview

**A Progressive Web App (PWA): static files hosted free on GitHub Pages, data stored in the
browser on her device.**

```
 GitHub Pages (free hosting)            Her device (Surface / phone)
 ┌──────────────────────────┐   first   ┌──────────────────────────────────────┐
 │ index.html  (UI + logic) │──visit──▶ │ Edge/Chrome/Safari                   │
 │ sw.js       (offline)    │           │  ├─ Service worker cache → offline   │
 │ manifest.json, icons     │           │  └─ IndexedDB "dance-register" → DATA│
 └──────────────────────────┘           └──────────────────────────────────────┘
        code only — no data                    data never leaves the device
                                               (except the backup .json she downloads)
```

### Why this approach
- **₹0 cost:** GitHub Pages hosts static files for free. There's no backend to pay for or patch.
- **Offline:** the studio may not have internet, and a service worker caches the app.
- **Installable:** Edge, Chrome and Safari can "install" it as an app with its own icon.
- **Simple to maintain:** one HTML file, no build step, no framework, no dependencies.
- **Rejected alternatives:**
  - Google Sheets/AppSheet: it would sync across devices, but it's clunkier and depends on Google's limits.
  - A real backend (DB + API): overkill, and it costs money and upkeep.

### Trade-off to remember
**No sync.** Each device and browser has its own separate data. Her Surface and her phone are
independent copies, and your test data on your phone never reaches her. The only way to move data
is Backup → Restore, which *replaces* everything rather than merging. She should pick one main device.

---

## 3. Files

| File | Purpose |
|---|---|
| `index.html` | The whole app: CSS, HTML shell, and JS (~600 lines, vanilla, no libraries) |
| `sw.js` | Service worker. **Network-first**: tries the network, falls back to the cache when offline. `CACHE` name = version |
| `manifest.json` | PWA metadata: name "Mudra", icons, theme colour, `display: standalone` |
| `icon-192.png`, `icon-512.png` | App icons (gold lotus + ghungroo bells on maroon), generated with Python/PIL |

---

## 4. How the code is organised (`index.html`)

### Data model (one JSON object, saved to IndexedDB key `state`)
```js
{
  version: 2,
  batches:    [{ id, name, days:[0-6], time }],             // 0 = Sunday
  students:   [{ id, name, phone, batchId, fee, joined:'YYYY-MM-DD',
                 notes, active, left?:'YYYY-MM-DD' }],      // archive = active:false + left date
  attendance: { 'YYYY-MM-DD|batchId': [studentId, ...] },   // list of who was PRESENT
  payments:   [{ id, studentId, month:'YYYY-MM', amount, date, mode }],
  defaultFee: 1000, dueDay: 15, waTemplate: '...', lastBackup: ISO
}
```
- Attendance stores only **present** IDs. Absent = on the batch roster that day but not in the list.
- A class key existing with an empty list is a class held where nobody came. A missing key means
  not marked.
- Payments store the **amount actually paid**, so changing the fee later doesn't rewrite history.

### Storage
- `load()` / `save()` write the whole state to **IndexedDB**, falling back to `localStorage`.
- `navigator.storage.persist()` is requested so the browser is less likely to evict data.
- Every change calls `save()` straight away. There's no Save button.

### Rendering
- Simple pattern: `render()` rebuilds `<main>` from `VIEWS[tab]()`, a function returning an HTML string.
- All clicks go through one delegated listener → `ACT[data-act](data-id, element)`.
- All user text goes through `esc()` before insertion, to prevent HTML injection.
- Dialogs use the native `<dialog>` element (`openDlg(html, onSubmit)`).

### Fee logic (the key business rule)
```
dueDate(m)      = m + '-' + dueDay                      // e.g. 2026-11-15
firstMonth(s)   = joined <= dueDate(joinMonth) ? joinMonth : joinMonth + 1
billable(s,m)   = fee > 0 && m >= firstMonth(s) && (active || m <= left month)
feeStatus(s,m)  = paid | free | notyet | na | overdue (today > due) | upcoming
overdueMonths() = every billable, unpaid, past-due month → "+N earlier months unpaid"
```

### Screens (tabs)
| Tab | What it does |
|---|---|
| **Today** | Picks the batch scheduled for the weekday. Tap tiles to mark present. Change the date to fix a past class |
| **History → By class** | Every class in a month with absent names. Flags scheduled days with no attendance as "Not marked". Tap a class to edit it |
| **History → By student** | Month calendar (✓ attended / ✗ missed / ? not marked), overall %, unpaid months, recent payments. Also opened by tapping a student anywhere |
| **Students** | Add / edit / archive (keeps history) / delete (wipes history) |
| **Fees** | Month view sorted Overdue → Due → First fee → Paid. Mark paid (amount, date, UPI/Cash), Undo, Remind |
| **Reports** | Attendance % per student, classes per batch, CSV export (month summary + full register) |
| **Settings** | Batches, default fee (+ apply to all active), due day, WhatsApp template, backup/restore, sample data, erase |

### WhatsApp reminders
- No API is used, and nothing is sent automatically. That would need the WhatsApp Business API, which is paid and needs a server.
- **Remind** opens `https://wa.me/91XXXXXXXXXX?text=...` and she presses Send herself.
- It only shows when the fee is Due/Overdue **and** the student has a phone number. A 10-digit number gets `91` added.
- Template placeholders: `{name}` `{amount}` `{month}` `{due}`. These are filled by `fillMsg()`.

### Responsive layout
- **Desktop/Surface:** tabs across the top.
- **≤ 640px (phones):** bottom tab bar with icons, safe-area padding, smaller tiles, 2-column stats.

---

## 5. Fixes & lessons learned

| Issue | Cause | Fix |
|---|---|---|
| Tabs overflowed and Settings was hidden on phones | 6 top tabs too wide for a phone | Bottom tab bar with icons at ≤ 640px |
| Date field overlapped the Batch field on iPhone | iOS date inputs ignore `width:100%` | `appearance:none; min-width:0` on date/month inputs |
| iPhone zoomed in when tapping a form field | iOS Safari auto-zooms inputs with font < 16px (fields inherited 13px from labels) | `font-size:16px` on all inputs/selects/textareas |
| Fees "due on" note squeezed beside Month on phones | Inline flex layout | `.bar>.hint{flex:1 1 230px}` so it wraps below |
| Month text centred on iOS | WebKit default | `::-webkit-date-and-time-value{text-align:left}` |
| Phone showed old version after an update | Service worker cache | Network-first SW + bump `CACHE`. Reload once or twice |
| Couldn't edit the institute name | By design (requirement 9) | Name hard-coded as `STUDIO='Mudra'` |
| Claude couldn't create the repo or enable Pages | Session limits on repo creation / Pages API | Repo created manually. Pages enabled in Settings → Pages. Claude GitHub App installed for pushes |

---

## 6. Deploy & update

**Hosting:** GitHub Pages → Settings → Pages → *Deploy from a branch* → `main` / root.
The "pages build and deployment" action publishes each push in about a minute.

**To release a change:**
1. Edit the files.
2. Bump `CACHE` in `sw.js` (e.g. `mudra-v4` → `mudra-v5`).
3. Commit and push to `main`.
4. Users get it the next time they open the app online (reload once or twice). Data is untouched.

**Data model changes:** `state = Object.assign(fresh(), saved)` fills in new fields with defaults,
so adding fields is safe. Renaming or removing fields needs a small migration in the start-up block.

**Custom domain (optional):** free on GitHub's side, but the domain costs roughly ₹500–1,200 a year. Add a CNAME
(`app` → `aamirsalam.github.io`) and set it in Settings → Pages. ⚠️ Changing the URL changes
browser storage, so the data won't follow. Back up first, then restore on the new address.

**Code privacy:** free GitHub Pages needs a public repo, so anyone can copy the code. Her data is
never in the repo. For private code, use a private repo with Cloudflare Pages (free).

---

## 7. Setting up her device

**Surface (Edge):** open the link → ⋯ → **Apps → Install this site as an app** → pin to Start/taskbar.
**Android (Chrome):** ⋮ → **Install app** / Add to Home screen.
**iPhone (Safari):** Share → **Add to Home Screen**.

After the first online visit, it works offline.

### Backups (important)
- **Settings → Download backup** saves `mudra-backup-YYYY-MM-DD.json`. Keep it in OneDrive/Google Drive.
- The app shows a banner if no backup has been taken for 7 days.
- Clearing browser "cookies and site data", switching browser or profile, or a new device = empty app.
  Fix it with **Settings → Restore from backup**.
- Handy for setup: enter batches and students on one device, back up, then restore on hers.

---

## 8. Ideas not built (yet)
- Cloud sync between devices (would need Google Sheets, Firebase or Supabase)
- Automatic WhatsApp sending (paid WhatsApp Business API)
- Per-class or term-based billing (the current rule is monthly only)
