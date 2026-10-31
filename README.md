# Mudra — Attendance & Fees

A free, offline attendance + fees app for Mudra. No server, no login, no subscription.
All data stays on the device (IndexedDB) — back it up weekly from **Settings → Download backup**.

## Features
- **Today** — picks the batch scheduled for the day; tap student tiles to mark present.
  Change the date to view or fix a past class.
- **History → By class** — every class in a month with who was absent; flags class days with
  no attendance marked; tap a class to open and fix it.
- **History → By student** — month calendar (attended / missed / not marked), overall attendance %,
  unpaid months with Remind / Mark paid, recent payments.
- **Students** — add / edit / archive (keeps history) / delete; tap a student to open their record.
- **Fees** — monthly, due on the 15th (configurable). A student's first fee is the first due date
  on or after joining (joined 5 Oct → Oct fee; joined 20 Oct → first fee Nov).
  Shows Overdue / Due / Paid, earlier unpaid months, and a WhatsApp Remind button.
- **Reports** — attendance % per student, classes held per batch, CSV export (opens in Excel).
- **Settings** — batches, default monthly fee (+ apply to all active students), due day,
  WhatsApp message template, backup / restore.

**WhatsApp:** "Remind" appears for students with a phone number and an unpaid fee. It opens WhatsApp
with the message pre-filled; she reviews it and presses Send. Nothing is sent automatically.
Template placeholders: `{name}` `{amount}` `{month}` `{due}`.

## Deploy (GitHub Pages, free)
1. Create a repo, e.g. `mudra`, and push these files to `main`:
   `index.html`, `sw.js`, `manifest.json`, `icon-192.png`, `icon-512.png`
2. Repo → Settings → Pages → Source: *Deploy from a branch* → `main` / root.
3. Open `https://<user>.github.io/mudra/` in **Microsoft Edge** on the Surface.
4. Edge menu (⋯) → **Apps → Install this site as an app**. Pin it to Start/taskbar.
5. Open it once while online; after that it works offline.

GitHub Pages on a free account needs a **public** repo, so anyone could copy the code.
To keep the code private for free, use a private repo with **Cloudflare Pages** instead.
Her data is never in the repo either way.

## Backups (important)
- Settings → **Download backup** saves a `.json` file. Move it into OneDrive.
  (Or set Edge → Settings → Downloads → "Ask me where to save each file" and pick OneDrive directly.)
- A reminder banner appears if no backup has been taken for 7 days.
- New device / reinstall: install the app, then Settings → **Restore from backup**.
- Clearing Edge "site data" for this site deletes the app's data — restore from backup if that happens.

## Updating the app
Push changes to the repo. The app is network-first, so she gets the new version the next time
she opens it online. Bump `CACHE` in `sw.js` when you release changes. Existing data carries over.
