# Deploying Shreya Auto — so the admin works from any phone, anywhere

This guide puts the **Flask app** (the one with the `/admin` panel) on the internet so
you can add and remove cars from **any device, anywhere** — and the changes stick.

---

## 0. The ONE rule that matters

Your inventory lives in plain files: `data/cars.json`, `data/partners.json`, and the
uploaded photos in `static/assets/img/`. The admin **writes to those files**.

So you must deploy to a host whose **disk is permanent**. If you pick a host with a
"throwaway" disk (Heroku, a free Render web service, etc.), every car you delete or add
will **reappear/vanish on the next restart**. That is the only thing that can bite you.

✅ **Recommended host: [PythonAnywhere](https://www.pythonanywhere.com)** — its disk is
permanent, it serves HTTPS for free, and a free account is enough to go live. (Render,
Railway, etc. also work *only if* you attach a persistent disk — see §7.)

---

## 1. What you deploy

- **Deploy this folder** → `shreya-auto-app/` (the Flask app). This is the real product:
  public site **and** the live admin. Once it's online, the admin works from your phone
  over the internet — no Wi-Fi, no NordVPN, no IP addresses.
- The separate `website/` folder is just a **static demo** with a hard-coded car list. It
  has no admin and can't be updated by you. You can ignore it, or host it on Netlify as a
  throwaway preview. **It is NOT what your customers should see.**

---

## 2. Pre-flight (2 minutes, do this once)

1. **Pick a strong admin password.** You'll set it as an environment variable in step 3
   (don't leave it as `shreya2017`).
2. **Generate a secret key.** On your PC run:
   ```
   py -c "import secrets; print(secrets.token_hex(32))"
   ```
   Copy the long line it prints — you'll paste it in step 3.
   *(If you skip this, the app still auto-creates a private key on the server — but setting
   it yourself is cleaner.)*

You do **not** edit `config.py` for the live site — you set environment variables instead,
so no password ever sits in your code.

---

## 3. Put it on PythonAnywhere (free)

1. **Sign up** at pythonanywhere.com → create a **Beginner (free)** account.
2. **Upload the code.** Two easy ways:
   - *Git:* open a **Bash console** (Consoles tab) and run
     `git clone https://github.com/YOU/your-repo.git shreya-auto-app`, **or**
   - *Zip:* zip your local `shreya-auto-app` folder, upload it on the **Files** tab, then in
     a Bash console run `unzip shreya-auto-app.zip`.
3. **Make a virtualenv + install.** In the Bash console:
   ```
   cd ~/shreya-auto-app
   mkvirtualenv --python=/usr/bin/python3.10 shreya
   pip install -r requirements.txt
   ```
   *(Note the virtualenv path it prints, e.g. `/home/USERNAME/.virtualenvs/shreya`.)*
4. **Create the web app.** Web tab → **Add a new web app** → **Manual configuration** →
   **Python 3.10**.
5. **Fill in the Web tab:**
   - **Source code:** `/home/USERNAME/shreya-auto-app`
   - **Working directory:** `/home/USERNAME/shreya-auto-app`
   - **Virtualenv:** `/home/USERNAME/.virtualenvs/shreya`
6. **Edit the WSGI file** (the Web tab links to it). Delete what's there and paste — change
   `USERNAME`, the password, and the secret key:
   ```python
   import sys, os
   path = "/home/USERNAME/shreya-auto-app"
   if path not in sys.path:
       sys.path.insert(0, path)

   os.environ["SHREYA_ADMIN_PASSWORD"] = "your-strong-password"   # required — the site won't start without it
   os.environ["SHREYA_SECRET_KEY"]     = "paste-the-long-random-line-from-step-2"
   os.environ["SHREYA_ADMIN_PATH"]     = "office-2f9k7x"          # your secret admin address (change if you like)

   from wsgi import application   # this is your app; it forces debug off automatically
   ```
7. *(Optional, faster photos)* Web tab → **Static files** → add
   URL `/assets/` → Directory `/home/USERNAME/shreya-auto-app/static/assets/`.
8. Click the big green **Reload** button.

🎉 Your site is now live at **`https://USERNAME.pythonanywhere.com`** and the admin at your
**secret address** — **`https://USERNAME.pythonanywhere.com/office-2f9k7x`** (whatever you set
`SHREYA_ADMIN_PATH` to). Plain `/admin` deliberately shows "Not Found" — that keeps bots out.

---

## 4. Confirm it works from your phone

On your phone's browser (any network — mobile data is fine):

- Open `https://USERNAME.pythonanywhere.com` → you should see the site.
- Open `https://USERNAME.pythonanywhere.com/office-2f9k7x` (your secret admin path) → log in with
  your password → **delete a car**. Refresh the home page on your laptop — it's gone there too.
  That's the proof: **one live inventory, edited from anywhere, persists.**

No NordVPN setting, no IP address, no "same Wi-Fi" — those were only because you were
testing on your home network. On a real host it's just a normal website link.

---

## 5. Updating inventory later (the day-to-day)

When a car sells: open your secret admin path on your phone → **Remove**. When a new car arrives:
**Add a car** (upload a photo — it's auto-shrunk to fast WebP). Changes are instant and
permanent. You never touch code again.

---

## 5b. Get inquiries emailed to you (recommended)

Every contact-form submission is **already saved** and shown in the admin under
**"Inquiries"** (with tap-to-call + WhatsApp-reply links). To **also get each one emailed**:

1. On the owner's Gmail, create an **App Password**: Google Account → Security →
   2-Step Verification (turn on) → **App passwords** → generate one (16 characters).
2. Set these three values. **⚠ Never put the password in `config.py`** — that file is in the
   public GitHub repo. Use one of:
   - **Locally (to test on your PC):** copy `.env.example` to **`.env`** and fill it in. The
     `.env` file is gitignored, so it's never committed. Restart the app.
   - **On a web host (production):** set them as **environment variables** in the WSGI config
     (same place as `SHREYA_ADMIN_PASSWORD`).
   ```
   SHREYA_MAIL_USERNAME = shreyaauto.enterprises@gmail.com
   SHREYA_MAIL_PASSWORD = the-16-char-app-password        # the App Password, NOT the normal one
   SHREYA_MAIL_TO       = shreyaauto.enterprises@gmail.com   (where mail is delivered)
   ```
3. Restart/reload the app, open the admin, and click **✉ Send test email** at the top of the
   Inquiries section. If it arrives (check spam too), you're done — new inquiries now land in
   that inbox and still save in the admin.

The code is ready; it sends over Gmail's secure SMTP **in the background** and **never breaks the
site if email fails**. Leave the mail settings blank to keep email off (inquiries still save + show
in admin).

## 6. Back up your data (recommended monthly)

Your whole inventory is three small files. On the **Files** tab download:
`data/cars.json`, `data/partners.json`, `data/inquiries.json`, and the `static/assets/img/`
folder. Keep a copy. That's a full backup.

---

## 7. Custom domain & other hosts

- **Custom domain** (e.g. `shreyaauto.com.np`): PythonAnywhere needs a paid **Hacker plan
  (~$5/mo)** for a custom domain + always-on. The free `*.pythonanywhere.com` link already
  works fully from any phone — upgrade only when you want your own domain.
- **Render / Railway / Fly.io:** these work too, but their default disks are **temporary**.
  You **must** attach a **persistent disk/volume** mounted at the app folder, or your admin
  edits get wiped on each deploy/restart. On those hosts run the app with
  `gunicorn wsgi:application` (add `gunicorn` to requirements there).
- **Windows / your own server:** `pip install waitress` then `python wsgi.py` runs a proper
  production server (not the dev one).

---

## What the app already does for you in production

Loading the app through `wsgi.py` automatically:
- turns **debug mode off** (no error pages leaking internals),
- serves the **login cookie over HTTPS only** + marks it HTTP-only and SameSite=Lax
  (basic CSRF protection),
- caps uploads at **12 MB**,
- creates the `data/` and photo folders on startup,
- uses a **strong, stable secret key** (from `SHREYA_SECRET_KEY`, or an auto-generated
  `.secret_key` file that is never committed).

You set the **password** and (ideally) the **secret key** as environment variables — that's
the whole security checklist.
