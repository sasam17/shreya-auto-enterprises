# Shreya Auto Enterprises — Web App

A bilingual (English / नेपाली) website for **Shreya Auto Enterprises**, Bishalnagar,
Kathmandu, built as a small **Python (Flask)** web application. It serves the public
website, receives inquiries from the contact form, and has a password-protected
**admin panel** where cars are added through a web form (photos are optimised
automatically).

---

## 1. How to run it

**First time / every time:** double-click **`run.bat`**.
It installs the two libraries it needs (Flask + Pillow) on the first run, then opens
the site in your browser.

- Website: **http://localhost:5000**
- Admin panel: **http://localhost:5000/admin** (password is in `config.py`)
- On your phone (same Wi-Fi): `http://<your-PC-ip>:5000`

To run it by hand instead of the .bat:
```
py -m pip install -r requirements.txt
py app.py
```
Stop the server by closing the window (or pressing `Ctrl + C`).

---

## 2. What every file does (the project map)

```
shreya-auto-app/
├── app.py            ← THE PYTHON SERVER. Routes, the contact form, the admin panel.
├── config.py         ← Settings you edit: admin password, email login, etc.
├── requirements.txt  ← The two libraries the app needs.
├── run.bat           ← One-click launcher (Windows).
│
├── data/
│   ├── cars.json     ← The car listings. The admin panel reads & writes this.
│   ├── partners.json ← The five partners. Also editable in the admin panel.
│   └── inquiries.json← Every contact-form inquiry is saved here (auto-created).
│
├── templates/        ← HTML pages (Flask fills in the dynamic parts).
│   ├── index.html    ← The website itself.
│   └── admin.html    ← The admin login + dashboard.
│
└── static/assets/    ← Everything the browser downloads:
    ├── css/styles.css← ALL the visual design (colours, layout, animations).
    ├── js/main.js    ← The interactivity (menus, language, dark mode, form, etc.).
    ├── img/          ← Logo, car photos, partner photos, brand logos.
    └── video/        ← The promo film.
```

**The big idea, in one sentence:** `app.py` (Python) sends the `templates/index.html`
page to the browser, fills in the car list from `data/cars.json`, and the browser then
uses `styles.css` (looks) and `main.js` (behaviour) to bring it to life.

---

## 3. Adding & removing cars and partners (the admin panel)

1. Go to **http://localhost:5000/admin** and log in.
2. **Cars** — fill the **Add a car** form (brand, model, year, price, specs separated
   by commas, and a photo) and click **Add car**. Remove a car with the **Remove**
   button next to it.
3. **Partners** — scroll down to **Add a partner** (name, role, photo). The first
   partner in the list is shown larger ("lead") on the site; the rest sit in a row
   below. Remove a partner the same way.
4. Every photo is automatically shrunk and converted to fast WebP, and changes appear
   on the website immediately.

Behind the scenes this just edits `data/cars.json` and `data/partners.json` — so you
can back up your whole inventory and team by copying those two files.

---

## 4. The contact form

Every inquiry is **always saved** to `data/inquiries.json`, so nothing is ever lost.
To also get them **emailed** to you, open `config.py` and fill in `MAIL_USERNAME` /
`MAIL_PASSWORD` (for Gmail, create an "App Password"). Until you do, the form still
works perfectly and the "Send on WhatsApp" button opens a pre-filled chat.

---

## 5. How the website itself is built (the 3 front-end files)

You only need to understand three files to explain the whole look & feel:

- **`templates/index.html`** — the *structure*. Each `<section>` is one part of the page
  (hero, cars, services, why-us, real-stories, the partners, contact, footer). Notice
  every piece of text has `data-en` and `data-np` attributes — that is the bilingual
  system: the language toggle swaps which one is shown.

- **`static/assets/css/styles.css`** — the *design*. The top of the file defines the
  brand colours once as variables (`--blue`, `--cyan`, `--dark`…), so the whole site
  changes if you change them in one place. **Dark mode** works by swapping those
  variables when `data-theme="dark"` is set. Animations are CSS transitions plus a few
  `@keyframes` (the aurora glow, the marquee, the rotating card borders).

- **`static/assets/js/main.js`** — the *behaviour*. It is split into clearly numbered
  blocks: (1) builds the car cards, (2) language toggle, (2b) dark/light toggle,
  (3) mobile menu, (4) the moving hero, (5) scroll reveals, … down to the custom cursor
  and the count-up stats. Each block has a comment saying what it does.

---

## 6. Presenting & maintaining this with confidence

To genuinely *own* this project in front of anyone, be able to do these five things —
they take ten minutes to practise and they are all true:

1. **Run it** — double-click `run.bat`, show the site loading.
2. **Add a car live** — open `/admin`, add one with a photo, show it appear on the site.
   (This is the most impressive thing to demonstrate.)
3. **Change a brand colour** — in `styles.css`, change `--blue`, refresh, watch the
   whole site update. Explains the variable system instantly.
4. **Flip the language & dark mode** — and explain the `data-en`/`data-np` and
   `data-theme` ideas above.
5. **Show an inquiry arriving** — submit the contact form, open `data/inquiries.json`,
   show the saved record.

If you can do those five, you understand the architecture: a Python server, a JSON data
store, an admin panel, server-side form handling, and a themed bilingual front-end.

---

## 7. Before going live (checklist)

- [ ] Change `ADMIN_PASSWORD` and `SECRET_KEY` in `config.py`.
- [ ] (Optional) Add email login in `config.py` to receive inquiries by email.
- [ ] Confirm the contact details in `templates/index.html` (phones, landline, email).
- [ ] Replace `data/cars.json` cars with your real, current stock via the admin panel.

**Hosting:** because this is a Python app, it needs a Python host (e.g. **PythonAnywhere**
— free tier, very beginner-friendly — or Render). Upload the folder, point it at `app.py`.
*(If you ever want a no-server version, the `../website` folder is the same site as plain
files you can drag onto Netlify — but you lose the live admin panel.)*

---

**Brand:** blue `#1577D6` · navy `#0B3A77` · cyan `#37B2EA` · cinematic dark `#06182E` ·
fonts Space Grotesk (headlines) + Poppins (body) + Noto Sans Devanagari (Nepali).
