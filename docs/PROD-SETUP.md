# PROD setup — step by step

A checklist for taking Mudra live for her. Do the steps in order and tick each box.
TEST is already running (`mudra-925e7`), so PROD is the same process in a **new, separate**
Firebase project.

> **Golden rule:** don't merge `dev` → `main` until **Part F**. Merging to `main` is what deploys PROD.

---

## Part A — Before you start (5 min)

- [ ] Everything you want her to have is working on TEST: https://mudra-925e7.web.app
- [ ] Decide on the **PROD project ID**. It becomes her URL (`https://<id>.web.app`) and **can never be
      changed**. Suggestions: `mudra-academy`, `mudra-kuchipudi`, `mudra-dance`.
- [ ] Ask her for the **Google account she'll sign in with**. Any Gmail works.
- [ ] Decide whether **you** also get access to PROD (for support). Only add yourself if she agrees.

---

## Part B — Create the Firebase project (10 min)

1. - [ ] https://console.firebase.google.com → **Create a project**
2. - [ ] Name: `Mudra`. **Below the name, click the pencil ✏️ next to the project ID** and type your
         chosen ID (e.g. `mudra-academy`). If it's taken, pick another. ⚠️ This is the only chance to set it.
3. - [ ] Google Analytics: **off** (not needed) → Create project.
4. - [ ] Check the bottom-left of the console says **Spark — No-cost**. Never click Upgrade; the app
         doesn't need it.

### Firestore database
5. - [ ] **Databases & Storage → Firestore → Create database**
6. - [ ] Edition: Standard (if asked) · Database ID: `(default)` · Location: **asia-south1 (Mumbai)** ·
         Rules: **production mode** → Create
7. - [ ] Click **Create only once**, then wait. If you see *"Database already exists. Please use another
         database_id"*, it means it was created anyway: close the wizard, refresh, and check the
         location shows **asia-south1**.

### Google sign-in
8. - [ ] **Security → Authentication → Get started → Sign-in method → Google → Enable**
9. - [ ] Project support email: your email → **Save**

### Web app config
10. - [ ] ⚙️ **Project settings → General → Your apps → `</>` (Web)**
11. - [ ] Nickname `mudra-web` · **leave "Also set up Firebase Hosting" unticked** → Register app
12. - [ ] Copy the `firebaseConfig = { ... }` block. You need it in Part E.

---

## Part C — Allowlist: who can sign in (5 min)

13. - [ ] **Firestore → Data → + Start collection**
14. - [ ] Collection ID: `access` → Next
15. - [ ] Document ID: `allowlist`
16. - [ ] Field: `emails` · Type: **array** → add a value of type **string**: her Gmail address
17. - [ ] (Optional) add another string: `aamirsalam5@gmail.com`
18. - [ ] **Save**

> ⚠️ **The email must match exactly what Google reports.** Dots matter here: on TEST,
> `aamir.salam5@gmail.com` was refused because Google reports `aamirsalam5@gmail.com`.
> **Surest method:** after Part F, have her sign in once. She'll see a "No access" screen showing her exact
> address, so copy that into the list. Then she taps *Use a different account* and signs in again.
> Changes to the list apply **immediately**, with no deploy needed.

---

## Part D — Google Cloud settings (10 min)

These are in **Google Cloud console** for the same project. Use the project picker at the top and make
sure it shows your PROD project ID, **not** `mudra-925e7`.

### Sign-in redirect
19. - [ ] https://console.cloud.google.com/apis/credentials?project=mudra-academy
20. - [ ] Under **OAuth 2.0 Client IDs**, open **"Web client (auto created by Google Service)"**.
          (It only appears after step 8.)
21. - [ ] **Authorized JavaScript origins → + Add URI** → `https://mudra-academy.web.app`
          (no path, no trailing `/`)
22. - [ ] **Authorized redirect URIs → + Add URI** → `https://mudra-academy.web.app/__/auth/handler`
23. - [ ] **Save** (at the bottom). It can take a few minutes to take effect.

> ⚠️ On TEST, the handler URL was first put under *JavaScript origins*, which gives
> "Invalid Origin: URIs must not contain a path". The `/__/auth/handler` URL goes under **Redirect URIs**.

### Deploy key for GitHub Actions
24. - [ ] https://console.cloud.google.com/iam-admin/serviceaccounts?project=mudra-academy
25. - [ ] **+ Create service account** → name `github-deploy` → Create and continue
26. - [ ] Add these 4 roles:
          - **Firebase Hosting Admin**
          - **Firebase Rules Admin**
          - **API Keys Viewer**
          - **Service Usage Consumer**
          → Continue → Done
27. - [ ] Click the account → **Keys → Add key → Create new key → JSON**, and it downloads.

---

## Part E — GitHub (5 min)

### Secret
28. - [ ] https://github.com/aamirsalam/mudra/settings/environments → **New environment** → `prod`
          (or open it if it already exists)
29. - [ ] *(Recommended)* tick **Required reviewers** → add yourself. Every PROD deploy then waits for
          you to click **Approve** in Actions, which is a safety catch against accidental releases.
30. - [ ] **Environment secrets → Add secret** → Name `FIREBASE_SERVICE_ACCOUNT` → paste the **entire**
          JSON file contents → Add secret
31. - [ ] **Delete the downloaded JSON file** from your computer.

> ⚠️ Make sure it's the **`prod`** environment, not `test`. Each has its own secret with the same name.

### Config
32. - [ ] Either **send Claude the `firebaseConfig` block** from step 12, or edit it yourself:
          in your local clone (on branch `dev`), open `env/prod.js` and replace every `REPLACE_ME` with the
          matching value. Drop `measurementId` (it isn't needed). Then commit and push to `dev`:
          ```bash
          git checkout dev
          git add env/prod.js && git commit -m "Add PROD Firebase config" && git push
          ```
          (Pushing to `dev` only deploys TEST, so it's safe.)

---

## Part F — Go live (5 min)

33. - [ ] GitHub → **Pull requests → New pull request** → base: **`main`** ← compare: **`dev`** →
          Create pull request → **Merge**. (Or click the yellow "Compare & pull request" banner, but
          check the base is `main`.)
34. - [ ] **Actions → Deploy** shows a run on `main`. If you set Required reviewers, click
          **Review deployments → prod → Approve**.
35. - [ ] Wait for the green tick. The run summary shows `Deployed to prod: https://mudra-academy.web.app`

> If the run is green but finishes in a few seconds, it **skipped**, which means the secret or
> `env/prod.js` is missing. Open the run, read the yellow warning, fix it, and re-run with
> **Re-run all jobs**.

---

## Part G — Verify before giving it to her (10 min)

36. - [ ] Open `https://mudra-academy.web.app` in a private/incognito window.
          The header says **Mudra** with **no TEST tag**.
37. - [ ] Sign in with an account **not** on the list, and you should see **No access**. ✅ The lock works.
38. - [ ] If you added yourself: sign in, check the app is empty, and that **"Load sample data" does NOT
          appear** (it's hidden in prod by design). Add one fake student, check it appears on a
          second device, then **delete it**.
39. - [ ] Sign out (Settings → Sign out).

---

## Part H — Set up her devices

Do this with her, on each device she'll use:

40. - [ ] Open `https://mudra-academy.web.app`
          - **Surface (Edge):** ⋯ → **Apps → Install this site as an app** → pin to Start/taskbar
          - **Android (Chrome):** ⋮ → **Install app**
          - **iPhone (Safari):** Share → **Add to Home Screen**
41. - [ ] Open it from the new icon → **Sign in with Google** → her account.
          If "No access" appears: copy the address shown into the allowlist (Part C) → *Use a different account*.
42. - [ ] **Settings → Batches → Add** her real batches (days + times).
43. - [ ] **Settings → Fees**: check the default fee is ₹1,000 and the due day is 15.
44. - [ ] **Settings → WhatsApp message**: adjust the wording if she wants.
45. - [ ] **Students → + Add** each student (name, parent's phone, batch, joined date).
46. - [ ] Mark today's attendance once together so she sees how it works.
47. - [ ] On her second device: install, sign in, and check the same students appear.

> **If she used the old offline version on a device**, signing in on that device shows a banner:
> *"Found N students saved on this device… Upload?"* Tap **Upload** to move them into her account.

---

## Part I — Clean up

48. - [ ] Retire the old offline-only site: GitHub repo → **Settings → Pages → Unpublish site** (or set
          Source to *None*). After the merge, `main` has no root `index.html` anyway.
49. - [ ] Update `README.md`: replace `<prod-project-id>` with the real ID.
50. - [ ] Add a calendar reminder for the first week: ask her if anything is confusing.

---

## After go-live — day-to-day

| Task | How |
|---|---|
| Change the app | Edit on `dev` → push → test on https://mudra-925e7.web.app → PR `dev`→`main` → merge (→ approve) |
| Add/remove who can sign in | PROD Firestore → `access/allowlist` → edit `emails`. Instant, no deploy |
| Undo a bad release | Firebase console (PROD) → **Hosting** → release history → ⋮ on the previous release → **Rollback** |
| She gets a new phone | Install + sign in. Data is already in the cloud |
| Extra safety | Ask her to do **Settings → Download backup** monthly and keep it in Drive/OneDrive |
| Check usage stays free | Firebase console → **Usage and billing**. One class is a tiny fraction of the free limits |

## Common problems

| Symptom | Cause → Fix |
|---|---|
| "No access" for her | Allowlist email doesn't match exactly → copy the address from the No access screen into `emails` |
| Sign-in popup closes / redirect error | Redirect URI missing or still propagating (Part D, steps 21–23) → check, then wait 5–10 min |
| `auth/unauthorized-domain` | Using a custom domain not yet added → add it in Authentication → Settings → Authorized domains **and** the OAuth client |
| Deploy run green but nothing changed | Run skipped → missing `FIREBASE_SERVICE_ACCOUNT` in the **prod** environment, or `env/prod.js` still has `REPLACE_ME` |
| Deploy fails with "permission denied" | Service account is missing a role (Part D, step 26) → add it in Cloud console → IAM |
| Phone shows the old version | It updates on the next online open. Close and reopen the app (or pull to refresh) once or twice |
| No "Run workflow" button in Actions | That button only appears once the workflow is on `main`. Before that, push to `dev` to trigger |
