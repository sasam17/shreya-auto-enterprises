# Deploying Shreya Auto — instructions for the developer

This app is **Python 3 + Flask**. Storage is **plain JSON files** (`data/*.json`) plus uploaded
photos in `static/assets/img/` — **no database**. Deploy the **`shreya-auto-app/`** folder only.
(The sibling `website/` folder is a static demo — ignore it.)

Production entry point is **`wsgi.py`** → it exposes `application` and forces production settings.

Budget ~15 minutes. Follow it top to bottom.

---

## 0. Five hard requirements (get these right and nothing breaks)

1. **A Python host** (Python 3.8+). NOT PHP/WordPress shared hosting — that cannot run Flask.
2. **A persistent/permanent disk.** The admin writes to `data/*.json` and saves photos to disk.
   On an *ephemeral* host (free Render web service, Heroku) those are wiped on every restart.
   Use **PythonAnywhere** (persistent by default) or a **VPS** with a normal disk.
3. **Run it via `wsgi.py`** (WSGI server), **never** `python app.py` (that's the dev server).
4. **Set two environment variables**: `SHREYA_ADMIN_PASSWORD` and `SHREYA_SECRET_KEY`.
   ⚠ **`wsgi.py` now refuses to start** (raises a clear `RuntimeError`) if `SHREYA_ADMIN_PASSWORD`
   is left as the built-in default — so the site can never go live with an unprotected admin.
   If you see that error at deploy, set a strong password env var and reload.
5. **Serve over HTTPS** (the host provides it). The login cookie is HTTPS-only in production.

**Admin URL is NOT `/admin`.** To keep automated bots off the login page, the admin panel lives at
a **secret address** — by default `/office-2f9k7x` (plain `/admin` returns 404). Change it to your
own with the optional `SHREYA_ADMIN_PATH` env var (e.g. `manage-fy3x9b`). You log in at
`https://YOUR-SITE/<that path>`. Optional: `SHREYA_SESSION_TIMEOUT_MIN` (default 30) auto-logs-out
an idle admin session.

Filenames/paths are already lowercase and case-consistent, so Linux (case-sensitive) is fine.

---

## 1. Recommended host: PythonAnywhere (free tier is enough)

### Step 1 — Account & code
1. Create a free **Beginner** account at pythonanywhere.com.
2. Get the code onto the server (a **Bash console** under the *Consoles* tab):
   - **Zip (simplest):** zip the `shreya-auto-app` folder, upload it on the *Files* tab, then
     `unzip shreya-auto-app.zip` in the console. **OR**
   - **Git:** `git clone <repo-url> shreya-auto-app`

### Step 2 — Virtualenv + dependencies
In the Bash console:
```bash
cd ~/shreya-auto-app
mkvirtualenv --python=/usr/bin/python3.10 shreya
pip install -r requirements.txt
```
Note the virtualenv path it prints (e.g. `/home/USERNAME/.virtualenvs/shreya`).

### Step 3 — Create the web app
*Web* tab → **Add a new web app** → **Manual configuration** → **Python 3.10**. Then set:
- **Source code:** `/home/USERNAME/shreya-auto-app`
- **Working directory:** `/home/USERNAME/shreya-auto-app`
- **Virtualenv:** `/home/USERNAME/.virtualenvs/shreya`

### Step 4 — WSGI file (the important bit)
The *Web* tab links to a WSGI config file. **Replace its entire contents** with this, editing the
three placeholders:
```python
import sys, os

project = "/home/USERNAME/shreya-auto-app"          # <-- your username
if project not in sys.path:
    sys.path.insert(0, project)

# Secrets — set here, do not commit them anywhere:
os.environ["SHREYA_ADMIN_PASSWORD"] = "CHOOSE-A-STRONG-PASSWORD"   # required (app won't start without it)
os.environ["SHREYA_SECRET_KEY"]     = "PASTE-A-LONG-RANDOM-HEX"    # see below
os.environ["SHREYA_ADMIN_PATH"]     = "office-2f9k7x"              # optional: your secret admin URL

# Optional — email each inquiry to the owner (Gmail App Password):
# os.environ["SHREYA_MAIL_USERNAME"] = "shreyaauto.enterprises@gmail.com"
# os.environ["SHREYA_MAIL_PASSWORD"] = "the-16-char-gmail-app-password"

from wsgi import application      # forces debug off + HTTPS-only cookies
```
Generate the secret key once (Bash console):
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Step 5 — (Optional, faster) static files mapping
*Web* tab → **Static files** → add: URL `/assets/` → Directory
`/home/USERNAME/shreya-auto-app/static/assets/`.

### Step 6 — Reload
Click the green **Reload** button. The site is live at `https://USERNAME.pythonanywhere.com`,
admin at `https://USERNAME.pythonanywhere.com/office-2f9k7x` (or whatever `SHREYA_ADMIN_PATH` you set).

> A **custom domain** (e.g. shreyaautoenterprises.com) on PythonAnywhere requires the paid
> **Hacker plan (~$5/mo)**. The free `*.pythonanywhere.com` URL works fully from any device.

---

## 2. Smoke test (do this every deploy — it catches the real problems)

1. Open `https://USERNAME.pythonanywhere.com` → site loads, cars show.
2. Open your secret admin path (e.g. `/office-2f9k7x`) → log in with the password → dashboard.
   (Check that plain `/admin` returns **404** — proof the rename took effect.)
3. **Add a test car** → then click **Reload** on the Web tab → open the admin again → the car is
   **still there**. ✅ This proves the disk is persistent (the #1 thing that goes wrong).
4. Open the admin from a **phone** → it works (no LAN/VPN — it's a normal HTTPS site now).
5. Delete the test car.

If step 3's car disappears after a Reload, the disk is **not** persistent — switch hosts (or add
a persistent disk). Don't go live until step 3 passes.

---

## 3. If you use a VPS instead (Hostinger VPS, Render+disk, Railway, etc.)

Same five requirements. Differences:
- Install deps in a venv, then run with a real WSGI server:
  `gunicorn wsgi:application` (Linux) — add `gunicorn` to the venv. (`waitress` also works.)
- Put **nginx** in front for HTTPS (Let's Encrypt) and reverse-proxy to gunicorn.
- Set the env vars (`SHREYA_ADMIN_PASSWORD`, `SHREYA_SECRET_KEY`, optional mail) in the
  service/systemd unit — not in code.
- Ensure the app directory (with `data/` and `static/assets/img/`) is on the **persistent disk**.

---

## 4. Updating the site later (Sambhav edits code → you redeploy) — WITHOUT losing inventory

The owner's live data is written by the app **on your server**: `data/cars.json`,
`data/partners.json`, `data/inquiries.json`, and admin-uploaded car photos
`static/assets/img/cars/upload-*.webp`. These are **gitignored on purpose** — they're
server-owned. A fresh checkout has no `data/cars.json`; the app auto-creates it from the
committed `data/cars.seed.json` on first run (same for partners). So:

```bash
cd ~/shreya-auto-app
git pull          # code only — leaves the gitignored live data + uploaded photos untouched
# then click Reload (PythonAnywhere Web tab) / restart the service
```

- ✅ `git pull` is safe: it only updates files that changed in the commit (templates, CSS, JS,
  `app.py`). It does **not** touch the live inventory or uploaded photos.
- ❌ Do **NOT** run `git reset --hard`, `git checkout -- data/`, or `git clean -fdx` on the live
  server — those can wipe the owner's inventory/photos. If you ever must, back up `data/` and the
  `static/assets/img/cars` + `img/team` folders first.
- Your env vars (`SHREYA_ADMIN_PASSWORD`, etc.) live in the WSGI config, not the repo, so a pull
  never disturbs them.

---

## 5. Do NOT

- ❌ Don't run `python app.py` as the public server (dev server, debug on). Use `wsgi.py`.
- ❌ Don't deploy to an ephemeral-disk host without a persistent volume (admin data gets wiped).
- ❌ Don't leave the default admin password (`shreya2017`) — set `SHREYA_ADMIN_PASSWORD`. (The app
  now enforces this: `wsgi.py` refuses to start on the default, so you can't forget.)
- ❌ Don't commit the password/secret key into the code — set them as environment variables.

Questions about the app's internals are answered in `app.py` (well-commented) and `config.py`.
