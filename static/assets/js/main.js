/* =====================================================================
   Shreya Auto Enterprises — site behaviour (vanilla JS, no dependencies)
   ===================================================================== */
(function () {
  "use strict";
  var WHATSAPP_PRIMARY = "9779841594067";   // Sachit Kuinkel — handles all inquiry / WhatsApp messages
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var pointerFine = window.matchMedia("(hover: hover) and (pointer: fine)").matches;

  /* -------------------------------------------------------------------
     1) CAR LISTINGS  —  EDIT THIS LIST to add / remove / update cars.
        brand  : must match a filter chip ("Kia" / "Maruti Suzuki") to filter
        name   : model shown as the title
        year   : optional ("" to hide)
        img    : path under assets/img/cars/
        fit    : "cover" (a normal photo) | "contain" (a designed poster image)
        price  : "Rs. 37,50,000"  — "" shows "Price on request"
        badge  : small tag on the photo
        specs  : short strings (km / fuel / engine / transmission)
     ------------------------------------------------------------------- */
  // The car list is provided by the Python server (from data/cars.json) as
  // window.SHREYA_CARS. The hard-coded list below is only a fallback used if
  // the page is opened directly as a file, without the server running.
  var CARS = (window.SHREYA_CARS && window.SHREYA_CARS.length) ? window.SHREYA_CARS : [
    { brand:"Maruti Suzuki", name:"Brezza", year:"2021", img:"assets/img/cars/car7-md.webp", full:"assets/img/cars/car7.webp", fit:"contain", price:"Rs. 37,50,000", badge:"Featured", specs:["53,000 km","Petrol","1500 cc"] },
    { brand:"Kia", name:"Sportage", year:"2019", img:"assets/img/cars/car8-md.webp", full:"assets/img/cars/car8.webp", fit:"contain", price:"Rs. 50,00,000", badge:"Automatic", specs:["34,325 km","Petrol","2000 cc","Automatic"] },
    { brand:"Kia", name:"Sonet", year:"", img:"assets/img/cars/car2-md.webp", full:"assets/img/cars/car2.webp", fit:"cover", price:"", badge:"In stock", specs:["SUV","Well maintained"] },
    { brand:"Kia", name:"Seltos", year:"", img:"assets/img/cars/car4-md.webp", full:"assets/img/cars/car4.webp", fit:"cover", price:"", badge:"In stock", specs:["SUV","Single owner"] }
  ];

  var grid = document.getElementById("carsGrid");
  var carsLimit = grid ? parseInt(grid.getAttribute("data-limit") || "0", 10) : 0;  // home shows a few; the /cars page shows all

  function esc(s) {
    // Escape any text before it goes into innerHTML — defence in depth against stored XSS.
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (m) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m];
    });
  }

  function carPage(id) { return "/car/" + id; }   // this car's own page (Flask route)

  function carCard(car) {
    var el = document.createElement("article");
    var sold = (car.status === "sold");
    el.className = "car-card reveal-fade beam" + (sold ? " car-card--sold" : "");
    el.setAttribute("data-brand", car.brand || "");
    var titleYear = car.year ? ' <span>· ' + esc(car.year) + "</span>" : "";
    var specs = (car.specs || []).map(function (s) { return '<span class="spec">' + esc(s) + "</span>"; }).join("");
    var price = car.price
      ? '<div class="car-card__price">' + esc(car.price) + "</div>"
      : '<div class="car-card__price is-request" data-en="Price on request" data-np="मूल्यका लागि सम्पर्क">Price on request</div>';
    var plainLabel = (car.brand || "") + " " + (car.name || "") + (car.year ? " " + car.year : "");
    var label = esc(plainLabel);
    var fit = car.fit === "contain" ? "contain" : "cover";   // whitelist, never raw
    var url = carPage(car.id);
    var badge = sold
      ? '<span class="car-card__sold" data-en="Sold" data-np="बिक्री भयो">Sold</span>'
      : '<span class="car-card__badge">' + esc(car.badge) + "</span>";
    var mediaInner = badge +
      '<span class="car-card__brand">' + esc(car.brand) + "</span>" +
      '<img class="is-' + fit + '" src="' + esc(car.img) + '" loading="lazy" decoding="async" onerror="this.onerror=null;this.src=this.src.indexOf(\'-md.webp\')>-1?this.src.replace(\'-md.webp\',\'.webp\'):this.src.replace(\'.webp\',\'.jpg\')" alt="' + label + ' for sale at Shreya Auto" />';
    // Only AVAILABLE cars open their page; sold cars are shown but not clickable.
    var media = sold
      ? '<div class="car-card__media">' + mediaInner + "</div>"
      : '<a class="car-card__media" href="' + url + '" aria-label="View ' + label + '">' + mediaInner + "</a>";
    var foot = sold
      ? '<div class="car-card__foot">' + price + '<span class="car-card__enq is-sold" data-en="Sold out" data-np="बिक्री भयो">Sold out</span></div>'
      : '<div class="car-card__foot">' + price +
          '<a class="car-card__enq" href="' + url + '"><span data-en="View details" data-np="विवरण हेर्नुहोस्">View details</span><svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M13.2 5.2 11.8 6.6l4.4 4.4H4v2h12.2l-4.4 4.4 1.4 1.4 6.8-6.8z"/></svg></a>' +
        "</div>";

    el.innerHTML = media +
      '<div class="car-card__body">' +
        '<div class="car-card__title">' + esc(car.name) + titleYear + "</div>" +
        '<div class="car-card__specs">' + specs + "</div>" +
        foot +
      "</div>";
    return el;
  }

  function renderCars(filter) {
    if (!grid) return;
    var list = CARS.filter(function (c) { return !filter || filter === "all" || c.brand === filter; });
    // available cars first, sold ones last (stable — keeps the given order within each group)
    list = list.slice().sort(function (a, b) { return (a.status === "sold" ? 1 : 0) - (b.status === "sold" ? 1 : 0); });
    var shown = carsLimit > 0 ? list.slice(0, carsLimit) : list;
    grid.innerHTML = "";
    shown.forEach(function (c) { grid.appendChild(carCard(c)); });
    var va = document.getElementById("viewAllCars");   // "View all N cars" button on the home page
    if (va) {
      va.style.display = (carsLimit > 0 && list.length > carsLimit) ? "" : "none";
      var cnt = va.querySelector("[data-count]");
      if (cnt) cnt.textContent = list.length;
    }
    applyLang(currentLang);
    observeReveals();
    initTilt();
  }

  function buildFilters() {
    // Build the brand filter chips from the actual cars, so new brands appear automatically.
    var fbar = document.getElementById("filters");
    if (!fbar) return;
    var brands = [];
    CARS.forEach(function (c) { if (c.brand && brands.indexOf(c.brand) === -1) brands.push(c.brand); });
    var html = '<button class="chip is-active" data-filter="all" data-en="All" data-np="सबै">All</button>';
    brands.forEach(function (b) { html += '<button class="chip" data-filter="' + esc(b) + '">' + esc(b) + "</button>"; });
    fbar.innerHTML = html;
  }

  var filters = document.getElementById("filters");
  if (filters) {
    filters.addEventListener("click", function (e) {
      var chip = e.target.closest(".chip");
      if (!chip) return;
      filters.querySelectorAll(".chip").forEach(function (c) { c.classList.remove("is-active"); });
      chip.classList.add("is-active");
      renderCars(chip.getAttribute("data-filter"));
      if (grid) grid.scrollTo({ left: 0, behavior: reduceMotion ? "auto" : "smooth" });
    });
  }

  /* ------------------------- 2) LANGUAGE TOGGLE ------------------------- */
  var currentLang = localStorage.getItem("sa-lang") === "np" ? "np" : "en";
  function applyLang(lang) {
    currentLang = lang;
    document.documentElement.lang = lang === "np" ? "ne" : "en";
    document.body.classList.toggle("lang-np", lang === "np");
    document.querySelectorAll("[data-en]").forEach(function (n) {
      var v = lang === "np" && n.getAttribute("data-np") ? n.getAttribute("data-np") : n.getAttribute("data-en");
      if (v != null) n.textContent = v;
    });
    document.querySelectorAll(".lang-toggle__opt").forEach(function (o) {
      o.classList.toggle("is-active", o.getAttribute("data-lang") === lang);
    });
    localStorage.setItem("sa-lang", lang);
    splitWords();
    splitReveal();
  }
  var langToggle = document.getElementById("langToggle");
  if (langToggle) langToggle.addEventListener("click", function () { applyLang(currentLang === "en" ? "np" : "en"); });

  /* ------------------------- 2b) THEME TOGGLE (light / dark) ------------------------- */
  var themeToggle = document.getElementById("themeToggle");
  if (themeToggle) themeToggle.addEventListener("click", function () {
    var next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    try { localStorage.setItem("sa-theme", next); } catch (e) {}
  });

  /* ------------------------- 3) NAV (mobile + scrolled) ------------------------- */
  var nav = document.getElementById("nav");
  var burger = document.getElementById("navBurger");
  if (burger && nav) {
    burger.addEventListener("click", function () {
      var open = nav.classList.toggle("is-open");
      burger.setAttribute("aria-expanded", open ? "true" : "false");
      burger.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    });
  }
  document.querySelectorAll(".nav__links a").forEach(function (a) {
    a.addEventListener("click", function () {
      if (nav) nav.classList.remove("is-open");
      if (burger) burger.setAttribute("aria-expanded", "false");
    });
  });

  /* ------------------------- 4) SCROLL + INTERACTIVE 3D HERO -------------------------
     The hero car, its aurora glow and a cursor spotlight move at different depths in
     response to the pointer (desktop) or device tilt (mobile gyro), and to scroll —
     a real-feeling 3D parallax with ~zero payload. */
  var progress = document.getElementById("scrollProgress");
  var heroImg = document.getElementById("heroImg");
  var heroFrame = document.getElementById("heroFrame");
  var heroEl = document.getElementById("hero");
  var heroAurora = heroEl ? heroEl.querySelector(".hero__aurora") : null;
  var heroSpot = heroEl ? heroEl.querySelector(".hero__spotlight") : null;
  var hx = 0, hy = 0, hScroll = 0, heroRaf = false;

  function renderHero() {
    heroRaf = false;
    if (reduceMotion) return;
    if (heroFrame) {
      heroFrame.style.setProperty("--fy", (hx * 4).toFixed(2) + "deg");
      heroFrame.style.setProperty("--fx", (-hy * 3).toFixed(2) + "deg");
    }
    if (heroImg) {
      heroImg.style.setProperty("--px", (hx * 12).toFixed(1) + "px");
      heroImg.style.setProperty("--py", (hy * 9 + hScroll * 0.05).toFixed(1) + "px");
    }
    if (heroAurora) heroAurora.style.transform = "translate3d(" + (-hx * 30).toFixed(1) + "px," + (-hy * 24).toFixed(1) + "px,0)";
  }
  function requestHero() { if (!heroRaf) { heroRaf = true; requestAnimationFrame(renderHero); } }

  if (heroEl && !reduceMotion) {
    if (pointerFine) {
      heroEl.addEventListener("pointermove", function (e) {
        var r = heroEl.getBoundingClientRect();
        hx = ((e.clientX - r.left) / r.width - 0.5) * 2;
        hy = ((e.clientY - r.top) / r.height - 0.5) * 2;
        if (heroSpot) { heroSpot.style.setProperty("--sx", (e.clientX - r.left) + "px"); heroSpot.style.setProperty("--sy", (e.clientY - r.top) + "px"); heroSpot.style.opacity = "1"; }
        requestHero();
      });
      heroEl.addEventListener("pointerleave", function () { hx = 0; hy = 0; if (heroSpot) heroSpot.style.opacity = "0"; requestHero(); });
    } else if (window.DeviceOrientationEvent) {
      window.addEventListener("deviceorientation", function (e) {
        if (e.gamma == null || e.beta == null) return;
        hx = Math.max(-1, Math.min(1, e.gamma / 28));
        hy = Math.max(-1, Math.min(1, (e.beta - 45) / 28));
        requestHero();
      }, true);
      // iOS requires a user-gesture permission grant before gyro events flow
      if (typeof DeviceOrientationEvent.requestPermission === "function") {
        window.addEventListener("touchend", function ask() {
          DeviceOrientationEvent.requestPermission().catch(function () {});
        }, { once: true });
      }
    }
  }

  var ticking = false;
  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () {
      var y = window.scrollY;
      var docH = document.documentElement.scrollHeight - window.innerHeight;
      if (progress) progress.style.width = (docH > 0 ? (y / docH) * 100 : 0) + "%";
      if (nav) nav.classList.toggle("is-scrolled", y > 20);
      if (y < window.innerHeight) { hScroll = y; renderHero(); }
      updateStatement();
      revealSweep();
      ticking = false;
    });
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  renderHero();
  onScroll();

  /* ------------------------- 5) REVEAL on scroll (mask / up / img) ------------------------- */
  var REVEAL_SEL = ".reveal-up:not(.is-in), .reveal-fade:not(.is-in), .reveal-mask:not(.is-in), .reveal-img:not(.is-in), .reveal-wipe:not(.is-in), .reveal-pop:not(.is-in), .split-words:not(.is-in)";
  var revealObserver = null;
  if (!reduceMotion && "IntersectionObserver" in window) {
    revealObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) { entry.target.classList.add("is-in"); revealObserver.unobserve(entry.target); }
      });
    }, { threshold: 0.08, rootMargin: "0px 0px -4% 0px" });
  }
  // Failsafe: anything on screen that the observer somehow missed gets revealed —
  // a hidden element must never leave a blank hole in the page.
  function revealSweep() {
    var els = document.querySelectorAll(REVEAL_SEL);
    for (var i = 0; i < els.length; i++) {
      var r = els[i].getBoundingClientRect();
      if (r.top < window.innerHeight - 40 && r.bottom > 0) els[i].classList.add("is-in");
    }
  }
  function observeReveals() {
    document.querySelectorAll(REVEAL_SEL).forEach(function (el) {
      if (!revealObserver) { el.classList.add("is-in"); return; }
      var explicit = el.getAttribute("data-delay");
      var delay;
      if (explicit != null) { delay = parseInt(explicit, 10) * 90; }
      else {
        var sibs = Array.prototype.filter.call(el.parentElement.children, function (c) {
          return c.classList.contains("reveal-up") || c.classList.contains("reveal-fade") || c.classList.contains("reveal-mask") || c.classList.contains("reveal-img");
        });
        var i = sibs.indexOf(el);
        delay = (i > 0 ? Math.min(i, 6) * 70 : 0);
      }
      el.style.transitionDelay = delay + "ms";
      revealObserver.observe(el);
    });
  }

  /* ------------------------- 6) DRAG-TO-SCROLL the car rail ------------------------- */
  var lastDragEnd = 0;
  if (grid) {
    var down = false, startX = 0, startScroll = 0, moved = false;
    grid.addEventListener("pointerdown", function (e) {
      if (e.pointerType === "mouse" && e.button !== 0) return;
      down = true; moved = false; startX = e.clientX; startScroll = grid.scrollLeft;
    });
    grid.addEventListener("pointermove", function (e) {
      if (!down) return;
      var dx = e.clientX - startX;
      if (Math.abs(dx) > 6) { moved = true; grid.classList.add("is-dragging"); }
      if (moved) grid.scrollLeft = startScroll - dx;
    });
    function endDrag() {
      if (!down) return;
      down = false; grid.classList.remove("is-dragging");
      if (moved) lastDragEnd = Date.now();
    }
    grid.addEventListener("pointerup", endDrag);
    grid.addEventListener("pointerleave", endDrag);
    grid.addEventListener("pointercancel", endDrag);
  }

  /* ------------------------- 7) LIGHTBOX ------------------------- */
  var lightbox = document.getElementById("lightbox");
  var lightboxImg = document.getElementById("lightboxImg");
  var lightboxVideo = document.getElementById("lightboxVideo");
  var lightboxClose = document.getElementById("lightboxClose");
  function openLightbox(src, alt) {
    if (!lightbox) return;
    lightboxVideo.hidden = true; lightboxImg.hidden = false;
    lightboxImg.src = src; lightboxImg.alt = alt || "";
    lightbox.classList.add("is-open"); lightbox.setAttribute("aria-hidden", "false");
  }
  function openVideo(src) {
    if (!lightbox) return;
    lightboxImg.hidden = true; lightboxImg.src = "";
    lightboxVideo.hidden = false; lightboxVideo.src = src;
    lightbox.classList.add("is-open"); lightbox.setAttribute("aria-hidden", "false");
    lightboxVideo.play().catch(function () {});
  }
  function closeLightbox() {
    if (!lightbox) return;
    lightbox.classList.remove("is-open"); lightbox.setAttribute("aria-hidden", "true");
    lightboxImg.src = "";
    lightboxVideo.pause(); lightboxVideo.removeAttribute("src"); lightboxVideo.load(); lightboxVideo.hidden = true;
  }
  document.addEventListener("click", function (e) {
    if (Date.now() - lastDragEnd < 200) return; // ignore click that ends a drag
    var vid = e.target.closest("[data-video]");
    if (vid) { openVideo(vid.getAttribute("data-video")); return; }
    var trigger = e.target.closest("[data-full]");
    if (trigger) { openLightbox(trigger.getAttribute("data-full"), trigger.getAttribute("aria-label")); return; }
    if (e.target === lightbox || e.target === lightboxClose) closeLightbox();
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeLightbox();
    if ((e.key === "Enter" || e.key === " ") && document.activeElement && document.activeElement.classList.contains("car-card__media")) {
      e.preventDefault(); openLightbox(document.activeElement.getAttribute("data-full"), document.activeElement.getAttribute("aria-label"));
    }
  });

  /* ------------------------- 8) ENQUIRY FORM ------------------------- */
  var form = document.getElementById("enquiryForm");
  var status = document.getElementById("formStatus");
  var formWa = document.getElementById("formWhatsapp");
  function readForm() {
    return {
      name: (document.getElementById("f-name") || {}).value || "",
      phone: (document.getElementById("f-phone") || {}).value || "",
      car: (document.getElementById("f-car") || {}).value || "",
      message: (document.getElementById("f-msg") || {}).value || ""
    };
  }
  function toWhatsApp(d) {
    var lines = ["Hello Shreya Auto!", d.name && "Name: " + d.name, d.phone && "Phone: " + d.phone, d.car && "Interested in: " + d.car, d.message && "Message: " + d.message].filter(Boolean);
    return "https://wa.me/" + WHATSAPP_PRIMARY + "?text=" + encodeURIComponent(lines.join("\n"));
  }
  function setStatus(msg, ok) { if (!status) return; status.textContent = msg; status.className = "form__status " + (ok ? "is-ok" : "is-err"); }
  if (formWa) formWa.addEventListener("click", function () {
    var d = readForm();
    if (!d.name || !d.phone) { setStatus(currentLang === "np" ? "कृपया नाम र फोन भर्नुहोस्।" : "Please add your name and phone first.", false); return; }
    window.open(toWhatsApp(d), "_blank", "noopener");
  });
  if (form) form.addEventListener("submit", function (e) {
    var d = readForm();
    if (!d.name || !d.phone) { e.preventDefault(); setStatus(currentLang === "np" ? "कृपया नाम र फोन भर्नुहोस्।" : "Please add your name and phone number.", false); return; }
    var action = form.getAttribute("action") || "";
    if (action.indexOf("REPLACE_WITH") !== -1) {
      e.preventDefault(); setStatus(currentLang === "np" ? "व्हाट्सएप खुल्दैछ…" : "Opening WhatsApp…", true);
      window.open(toWhatsApp(d), "_blank", "noopener"); return;
    }
    e.preventDefault(); setStatus(currentLang === "np" ? "पठाउँदै…" : "Sending…", true);
    fetch(action, { method: "POST", body: new FormData(form), headers: { Accept: "application/json" } })
      .then(function (r) {
        if (r.ok) { form.reset(); setStatus(currentLang === "np" ? "धन्यवाद! हामी छिट्टै सम्पर्क गर्नेछौं।" : "Thank you! We'll get back to you shortly.", true); }
        else setStatus(currentLang === "np" ? "केही गडबड भयो — व्हाट्सएप प्रयोग गर्नुहोस्।" : "Something went wrong — please use WhatsApp.", false);
      })
      .catch(function () { setStatus(currentLang === "np" ? "नेटवर्क त्रुटि — व्हाट्सएप प्रयोग गर्नुहोस्।" : "Network error — please use WhatsApp.", false); });
  });

  /* ------------------------- 9) MAP (load on demand) ------------------------- */
  var mapLoad = document.getElementById("mapLoad");
  var mapHolder = document.getElementById("mapHolder");
  if (mapLoad && mapHolder) mapLoad.addEventListener("click", function () {
    var iframe = document.createElement("iframe");
    iframe.title = "Shreya Auto Enterprises location map";
    iframe.src = mapHolder.getAttribute("data-map");
    iframe.loading = "lazy"; iframe.referrerPolicy = "no-referrer-when-downgrade";
    mapHolder.innerHTML = ""; mapHolder.appendChild(iframe);
  });

  /* ------------------------- 10) STACKED PHOTOS (tap to fan out on touch) ------------------------- */
  var stack = document.getElementById("stack");
  if (stack && !pointerFine) {
    stack.addEventListener("click", function () { stack.classList.toggle("is-spread"); });
  }

  /* ------------------------- 11) PREMIUM MOTION ------------------------- */
  var STRIP = /[^\p{L}\p{N}]/gu;

  // kinetic headline — wrap each word for a masked, staggered reveal
  function splitWords() {
    document.querySelectorAll(".split-words").forEach(function (el) {
      var accent = (currentLang === "np" ? el.getAttribute("data-accent-np") : el.getAttribute("data-accent-en")) || "";
      var words = el.textContent.trim().split(/\s+/);
      el.textContent = "";
      words.forEach(function (w, i) {
        var word = document.createElement("span"); word.className = "word";
        if (accent && w.replace(STRIP, "") === accent) word.classList.add("is-accent");
        var inner = document.createElement("span"); inner.textContent = w;
        if (!reduceMotion) inner.style.transitionDelay = (i * 60) + "ms";
        word.appendChild(inner); el.appendChild(word); el.appendChild(document.createTextNode(" "));
      });
    });
  }

  // scroll text-reveal — words brighten sequentially as the line scrolls through
  var statementWords = [];
  function splitReveal() {
    statementWords = [];
    document.querySelectorAll(".split-reveal").forEach(function (el) {
      var accent = (currentLang === "np" ? el.getAttribute("data-accent-np") : el.getAttribute("data-accent-en")) || "";
      var words = el.textContent.trim().split(/\s+/);
      el.textContent = "";
      words.forEach(function (w) {
        var s = document.createElement("span"); s.className = "w";
        if (accent && w.replace(STRIP, "") === accent) s.classList.add("accentw");
        s.textContent = w; el.appendChild(s); el.appendChild(document.createTextNode(" "));
        statementWords.push(s);
      });
    });
  }
  function updateStatement() {
    if (reduceMotion || !statementWords.length) return;
    var el = document.querySelector(".split-reveal"); if (!el) return;
    var r = el.getBoundingClientRect(), vh = window.innerHeight;
    var p = (vh * 0.82 - r.top) / (vh * 0.82 - vh * 0.32 + r.height);
    p = Math.max(0, Math.min(1, p));
    var lit = Math.round(p * statementWords.length);
    statementWords.forEach(function (s, i) { s.classList.toggle("lit", i < lit); });
  }
  // Drive the word-lighting with an rAF loop while the line is on screen, so it
  // never depends on scroll events firing (robust + smooth).
  function initStatementReveal() {
    var el = document.querySelector(".split-reveal");
    if (!el || reduceMotion || !("IntersectionObserver" in window)) return;
    var visible = false, looping = false;
    function loop() { if (!visible) { looping = false; return; } updateStatement(); requestAnimationFrame(loop); }
    new IntersectionObserver(function (es) {
      es.forEach(function (e) { visible = e.isIntersecting; if (visible && !looping) { looping = true; requestAnimationFrame(loop); } });
    }, { threshold: 0 }).observe(el);
  }

  // tactile cards — 3D tilt + cursor spotlight (desktop pointers only)
  function initTilt() {
    if (reduceMotion || !pointerFine) return;
    document.querySelectorAll(".car-card").forEach(function (card) {
      if (card._tilt) return; card._tilt = true;
      var media = card.querySelector(".car-card__media");
      card.addEventListener("pointermove", function (e) {
        if (grid && grid.classList.contains("is-dragging")) return;
        var r = card.getBoundingClientRect();
        var px = (e.clientX - r.left) / r.width, py = (e.clientY - r.top) / r.height;
        card.style.setProperty("--ry", ((px - 0.5) * 7).toFixed(2) + "deg");
        card.style.setProperty("--rx", ((0.5 - py) * 7).toFixed(2) + "deg");
        card.style.setProperty("--ty", "-6px");
        if (media) { media.style.setProperty("--mx", (px * 100).toFixed(1) + "%"); media.style.setProperty("--my", (py * 100).toFixed(1) + "%"); }
      });
      card.addEventListener("pointerleave", function () {
        card.style.setProperty("--rx", "0deg"); card.style.setProperty("--ry", "0deg"); card.style.setProperty("--ty", "0");
      });
    });
  }

  // magnetic CTAs — accent buttons gently follow the cursor
  function initMagnetic() {
    if (reduceMotion || !pointerFine) return;
    document.querySelectorAll(".btn--accent").forEach(function (b) {
      b.addEventListener("pointermove", function (e) {
        var r = b.getBoundingClientRect();
        var x = ((e.clientX - r.left) / r.width - 0.5) * 12, y = ((e.clientY - r.top) / r.height - 0.5) * 12;
        b.style.transform = "translate(" + x.toFixed(1) + "px," + y.toFixed(1) + "px)";
      });
      b.addEventListener("pointerleave", function () { b.style.transform = ""; });
    });
  }

  // stats count-up — numbers tick from 0 to their value when scrolled into view
  function initStats() {
    var statsEl = document.getElementById("stats");
    if (!statsEl) return;
    var items = [];
    statsEl.querySelectorAll(".odo").forEach(function (o) {
      var m = o.textContent.trim().match(/^([\d,]+)(.*)$/);
      var num = m ? parseInt(m[1].replace(/,/g, ""), 10) : 0;
      var suf = m ? m[2] : "";
      o.setAttribute("role", "img");
      o.setAttribute("aria-label", o.textContent.trim());
      o.style.display = "inline-block";
      o.style.minWidth = (num + suf).toString().length + "ch";
      items.push({ el: o, num: num, suf: suf });
    });
    if (reduceMotion || !("IntersectionObserver" in window)) return; // keep final values
    items.forEach(function (p) { p.el.textContent = "0" + p.suf; });
    function run() {
      var t0 = null, dur = 1600;
      function frame(t) {
        if (t0 === null) t0 = t;
        var prog = Math.min((t - t0) / dur, 1);
        var e = 1 - Math.pow(1 - prog, 3); // easeOutCubic
        items.forEach(function (p) { p.el.textContent = Math.round(e * p.num) + p.suf; });
        if (prog < 1) requestAnimationFrame(frame);
      }
      requestAnimationFrame(frame);
    }
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { run(); io.disconnect(); } });
    }, { threshold: 0.35 });
    io.observe(statsEl);
    setTimeout(function () { items.forEach(function (p) { p.el.textContent = p.num + p.suf; }); }, 12000); // failsafe
  }

  // custom cursor — instant dot + trailing ring; ring blooms over interactive elements
  function initCursor() {
    if (reduceMotion || !pointerFine) return;
    var dot = document.createElement("div"); dot.className = "cur-dot";
    var ring = document.createElement("div"); ring.className = "cur-ring";
    document.body.appendChild(dot); document.body.appendChild(ring);
    document.body.classList.add("cursor-on");
    var INTERACTIVE = "a, button, .chip, [data-full], .car-card, .stack, input, textarea, select";
    var x = 0, y = 0, rx = 0, ry = 0, scale = 1, running = false;
    function loop() {
      rx += (x - rx) * 0.18; ry += (y - ry) * 0.18;
      ring.style.transform = "translate(" + (rx - 18) + "px," + (ry - 18) + "px) scale(" + scale + ")";
      if (Math.abs(x - rx) > 0.2 || Math.abs(y - ry) > 0.2) requestAnimationFrame(loop);
      else running = false;
    }
    document.addEventListener("pointermove", function (e) {
      if (e.pointerType !== "mouse") return;
      x = e.clientX; y = e.clientY;
      dot.style.transform = "translate(" + (x - 3) + "px," + (y - 3) + "px)";
      document.body.classList.add("cursor-live");
      var t = e.target.closest(INTERACTIVE);
      var isField = t && /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName);
      dot.classList.toggle("is-hidden", !!isField);
      ring.classList.toggle("is-hidden", !!isField);
      ring.classList.toggle("is-link", !!t && !isField);
      scale = t && !isField ? 1.55 : 1;
      if (!running) { running = true; requestAnimationFrame(loop); }
    }, { passive: true });
    document.addEventListener("pointerleave", function () { document.body.classList.remove("cursor-live"); });
    document.documentElement.addEventListener("mouseleave", function () { document.body.classList.remove("cursor-live"); });
  }

  // choreographed intro
  function hidePreloader() { document.body.classList.add("loaded"); }

  /* ------------------------- 11b) PARTNERS  —  in the Flask app these come from the
        admin panel (data/partners.json), injected as window.SHREYA_PARTNERS.
        order = position (lower shows first); the first one is the lead, shown larger on top. ------------------------- */
  var PARTNERS = (window.SHREYA_PARTNERS && window.SHREYA_PARTNERS.length) ? window.SHREYA_PARTNERS : [
    { name: "Shambhu Shahi", role: "Partner", img: "assets/img/team/team-1.webp", order: 1 },
    { name: "Pradeep Rana", role: "Partner", img: "assets/img/team/team-2.webp", order: 2 },
    { name: "Sachit Kuinkel", role: "Partner", img: "assets/img/team/team-3.webp", order: 3 },
    { name: "Somraj Dangi", role: "Partner", img: "assets/img/team/team-4.webp", order: 4 },
    { name: "Dhruba Pandey", role: "Partner", img: "assets/img/team/partner-5.webp", order: 5 }
  ];
  function partnerFigure(p, lead) {
    var role = p.role || "Partner";
    var roleNp = role === "Partner" ? "साझेदार" : role;   // keep the role label for non-partners (e.g. Supervisor)
    var r = esc(role), rNp = esc(roleNp), nm = esc(p.name);
    return '<figure class="member reveal-pop' + (lead ? " member--lead" : "") + '">' +
      '<img src="' + esc(p.img) + '" loading="lazy" decoding="async" alt="' + nm + ' — ' + r + ' at Shreya Auto Enterprises" />' +
      '<figcaption><span data-en="' + r + '" data-np="' + rNp + '">' + r + "</span><strong>" + nm + "</strong></figcaption>" +
      "</figure>";
  }
  function renderPartners() {
    var wrap = document.getElementById("teamGrid");
    if (!wrap || !PARTNERS.length) return;
    var ordered = PARTNERS.slice().sort(function (a, b) {
      return (a.order != null ? a.order : 999) - (b.order != null ? b.order : 999);
    });
    wrap.innerHTML =
      partnerFigure(ordered[0], true) +
      '<div class="team__row">' + ordered.slice(1).map(function (p) { return partnerFigure(p, false); }).join("") + "</div>";
    applyLang(currentLang);
    observeReveals();
  }

  /* ------------------------- 11c) REVIEWS  —  approved reviews come from the admin
        (data/reviews.json) as window.SHREYA_REVIEWS. The list below is only a fallback
        for opening the file directly without the server. ------------------------- */
  var REVIEWS = (window.SHREYA_REVIEWS && window.SHREYA_REVIEWS.length) ? window.SHREYA_REVIEWS : [
    { name: "Ramesh Shrestha", rating: 5, location: "Kathmandu", time: "2026-06-18", text: "Bought a used SUV here and the whole process was honest and easy. Fair price, no pressure, and they explained everything about the car." },
    { name: "Anita Gurung", rating: 5, location: "Bishalnagar", time: "2026-05-30", text: "Exchanged my old car for a newer one. Transparent valuation and they helped with the paperwork and financing. Trustworthy service." },
    { name: "Bibek Thapa", rating: 4, location: "Kathmandu", time: "2026-04-22", text: "Good selection of well-maintained cars and genuine people to deal with. Sold my car through them and got a fair deal." }
  ];

  function starRow(n) {
    n = Math.max(0, Math.min(5, Math.round(n || 0)));
    return '<span class="stars" aria-hidden="true"><span class="stars__on">' + "★".repeat(n) + '</span>' + "☆".repeat(5 - n) + "</span>";
  }
  function reviewCard(r) {
    var el = document.createElement("article");
    el.className = "review-card reveal-pop";
    var initial = esc((String(r.name || "?").trim().charAt(0) || "?").toUpperCase());
    var meta = [r.location, r.time].filter(Boolean).map(esc).join(" · ");
    el.innerHTML =
      '<div class="review-card__top">' +
        '<span class="review-card__avatar" aria-hidden="true">' + initial + "</span>" +
        '<span class="review-card__id"><span class="review-card__name">' + esc(r.name) + "</span>" +
          (meta ? '<span class="review-card__meta">' + meta + "</span>" : "") + "</span>" +
        '<span class="review-card__quote" aria-hidden="true">&ldquo;</span>' +
      "</div>" +
      '<div class="review-card__stars" aria-label="' + (r.rating || 0) + ' out of 5">' + starRow(r.rating) + "</div>" +
      '<p class="review-card__text">' + esc(r.text) + "</p>";
    return el;
  }
  function renderReviews() {
    var wrap = document.getElementById("reviewsGrid");
    if (!wrap) return;
    wrap.innerHTML = "";
    REVIEWS.forEach(function (r) { wrap.appendChild(reviewCard(r)); });
    var empty = document.getElementById("reviewsEmpty");
    if (empty) empty.hidden = REVIEWS.length > 0;
    var cnt = REVIEWS.length;
    var cntEl = document.getElementById("revCount"), avgEl = document.getElementById("revAvg"), avgStars = document.getElementById("revAvgStars");
    if (cntEl) cntEl.textContent = cnt;
    if (cnt) {
      var avg = REVIEWS.reduce(function (s, r) { return s + (+r.rating || 0); }, 0) / cnt;
      if (avgEl) avgEl.textContent = avg.toFixed(1);
      if (avgStars) avgStars.innerHTML = starRow(avg);
    } else {
      if (avgEl) avgEl.textContent = "—";
      if (avgStars) avgStars.innerHTML = "";
    }
    applyLang(currentLang);
    observeReveals();
  }

  // "Write a review" toggle + star picker + submit
  (function initReviewForm() {
    var openBtn = document.getElementById("openReviewForm");
    var panel = document.getElementById("reviewPanel");
    if (openBtn && panel) {
      openBtn.addEventListener("click", function () {
        panel.hidden = !panel.hidden;
        if (!panel.hidden) {
          observeReveals();
          var first = panel.querySelector("input, textarea"); if (first) first.focus();
          panel.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "center" });
        }
      });
    }
    var starsWrap = document.getElementById("rvStars");
    var ratingInput = document.getElementById("rv-rating");
    function paint(v) {
      if (!starsWrap) return;
      starsWrap.querySelectorAll(".rv-star").forEach(function (s) {
        s.classList.toggle("is-on", (+s.getAttribute("data-val")) <= v);
      });
    }
    if (starsWrap) {
      starsWrap.addEventListener("click", function (e) {
        var b = e.target.closest(".rv-star"); if (!b) return;
        var v = +b.getAttribute("data-val"); if (ratingInput) ratingInput.value = v; paint(v);
      });
      starsWrap.addEventListener("mouseover", function (e) { var b = e.target.closest(".rv-star"); if (b) paint(+b.getAttribute("data-val")); });
      starsWrap.addEventListener("mouseleave", function () { paint(ratingInput ? +ratingInput.value : 5); });
    }
    var rform = document.getElementById("reviewForm");
    var rstatus = document.getElementById("reviewStatus");
    function rSet(msg, ok) { if (!rstatus) return; rstatus.textContent = msg; rstatus.className = "form__status " + (ok ? "is-ok" : "is-err"); }
    if (rform) rform.addEventListener("submit", function (e) {
      e.preventDefault();
      var nm = (document.getElementById("rv-name") || {}).value || "";
      var tx = (document.getElementById("rv-text") || {}).value || "";
      if (!nm.trim() || !tx.trim()) { rSet(currentLang === "np" ? "कृपया नाम र समीक्षा लेख्नुहोस्।" : "Please add your name and a review.", false); return; }
      var action = rform.getAttribute("action") || "";
      if (action.indexOf("REPLACE_WITH") !== -1) {   // static demo (no server): acknowledge locally
        rSet(currentLang === "np" ? "धन्यवाद! तपाईंको समीक्षा प्राप्त भयो।" : "Thank you! Your review has been received.", true);
        rform.reset(); if (ratingInput) ratingInput.value = 5; paint(5); return;
      }
      rSet(currentLang === "np" ? "पठाउँदै…" : "Sending…", true);
      fetch(action, { method: "POST", body: new FormData(rform), headers: { Accept: "application/json" } })
        .then(function (r) {
          if (r.ok) { rform.reset(); if (ratingInput) ratingInput.value = 5; paint(5); rSet(currentLang === "np" ? "धन्यवाद! जाँचपछि तपाईंको समीक्षा देखिनेछ।" : "Thank you! Your review will appear once it's approved.", true); }
          else rSet(currentLang === "np" ? "केही गडबड भयो — फेरि प्रयास गर्नुहोस्।" : "Something went wrong — please try again.", false);
        })
        .catch(function () { rSet(currentLang === "np" ? "नेटवर्क त्रुटि — फेरि प्रयास गर्नुहोस्।" : "Network error — please try again.", false); });
    });
  })();

  /* ------------------------- 12) INIT ------------------------- */
  var yearEl = document.getElementById("year");
  if (yearEl) yearEl.textContent = new Date().getFullYear();

  buildFilters();             // brand chips from the real cars
  renderCars("all");          // builds cards + applyLang (which splits words) + observeReveals + initTilt
  renderPartners();           // builds the lead-on-top partner layout (sorted by order) with staggered spring reveal
  renderReviews();            // builds the customer review cards + rating summary
  applyLang(currentLang);
  observeReveals();
  initMagnetic();
  initStatementReveal();
  initStats();
  initCursor();
  updateStatement();
  [1500, 3500, 7000].forEach(function (t) { setTimeout(revealSweep, t); }); // belt-and-suspenders on slow devices

  if (reduceMotion) hidePreloader();
  else {
    if (document.readyState === "complete") setTimeout(hidePreloader, 300);
    else window.addEventListener("load", function () { setTimeout(hidePreloader, 300); });
    setTimeout(hidePreloader, 2600); // failsafe so the intro can never get stuck
  }
})();
