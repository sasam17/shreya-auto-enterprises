"""
db.py — the database layer for Shreya Auto Enterprises.

DUAL-ENGINE: the SAME code runs on SQLite (local, a file) or MySQL (production),
chosen by config.DATABASE_URL. All records live here: users, buyers, cars,
gallery photos, partners, inquiries, reviews, sales and an audit log.

Prices are internal (admin-only) — the public site never shows them.
Passwords are stored only as PBKDF2 hashes (werkzeug), never in plain text.
"""
import json
import os
from datetime import datetime, timezone

from sqlalchemy import (create_engine, String, Integer, Text, Boolean, DateTime,
                        select, delete, func, text)
from sqlalchemy.orm import (DeclarativeBase, Mapped, mapped_column,
                            sessionmaker, scoped_session)
from werkzeug.security import generate_password_hash, check_password_hash

import config

DATABASE_URL = config.DATABASE_URL
_IS_SQLITE = DATABASE_URL.startswith("sqlite")

if _IS_SQLITE:
    _path = DATABASE_URL.replace("sqlite:///", "", 1)
    if _path:
        os.makedirs(os.path.dirname(_path), exist_ok=True)
    engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True,
                           connect_args={"check_same_thread": False})
else:
    # MySQL / server databases: use a tuned connection pool.
    engine = create_engine(
        DATABASE_URL, future=True, pool_pre_ping=True,
        pool_size=config.DB_POOL_SIZE,
        max_overflow=config.DB_MAX_OVERFLOW,
        pool_recycle=config.DB_POOL_RECYCLE,
    )

SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False,
                                           expire_on_commit=False, future=True))


class Base(DeclarativeBase):
    pass


def _now():
    return datetime.now(timezone.utc)


# ── Models ───────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"
    id:            Mapped[int] = mapped_column(Integer, primary_key=True)
    username:      Mapped[str] = mapped_column(String(60), unique=True, index=True)
    email:         Mapped[str] = mapped_column(String(120), default="")
    password_hash: Mapped[str] = mapped_column(String(255), default="")
    full_name:     Mapped[str] = mapped_column(String(120), default="")
    role:          Mapped[str] = mapped_column(String(30), default="sales_rep")  # superadmin|manager|sales_rep
    is_active:     Mapped[bool] = mapped_column(Boolean, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at:    Mapped[datetime] = mapped_column(DateTime, default=_now)
    last_login:    Mapped[datetime] = mapped_column(DateTime, nullable=True)

    def as_dict(self):
        return {"id": self.id, "username": self.username, "email": self.email,
                "full_name": self.full_name, "role": self.role,
                "is_active": self.is_active, "must_change_password": self.must_change_password,
                "created_at": (self.created_at or _now()).strftime("%Y-%m-%d"),
                "last_login": self.last_login.strftime("%Y-%m-%d %H:%M") if self.last_login else ""}


class Buyer(Base):
    __tablename__ = "buyers"
    id:        Mapped[int] = mapped_column(Integer, primary_key=True)
    name:      Mapped[str] = mapped_column(String(120), index=True)
    phone:     Mapped[str] = mapped_column(String(40), index=True, default="")
    email:     Mapped[str] = mapped_column(String(120), default="")
    address:   Mapped[str] = mapped_column(String(255), default="")
    id_number: Mapped[str] = mapped_column(String(60), default="")   # Citizenship / PAN / License
    notes:     Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    def as_dict(self):
        return {"id": self.id, "name": self.name, "phone": self.phone, "email": self.email,
                "address": self.address, "id_number": self.id_number, "notes": self.notes,
                "created_at": (self.created_at or _now()).strftime("%Y-%m-%d")}


class Car(Base):
    __tablename__ = "cars"
    id:      Mapped[int] = mapped_column(Integer, primary_key=True)
    brand:   Mapped[str] = mapped_column(String(100), index=True, default="")
    name:    Mapped[str] = mapped_column(String(150), default="")
    year:    Mapped[str] = mapped_column(String(20), default="")
    price:   Mapped[str] = mapped_column(String(60), default="")     # internal only
    badge:   Mapped[str] = mapped_column(String(50), default="In stock")
    status:  Mapped[str] = mapped_column(String(30), index=True, default="available")  # available|sold|reserved
    fuel_type:    Mapped[str] = mapped_column(String(40), index=True, default="")
    transmission: Mapped[str] = mapped_column(String(40), index=True, default="")
    specs_json:   Mapped[str] = mapped_column(Text, default="[]")
    km:      Mapped[str] = mapped_column(String(60), default="")
    engine:  Mapped[str] = mapped_column(String(60), default="")
    colour:  Mapped[str] = mapped_column(String(60), default="")
    desc:    Mapped[str] = mapped_column("descr", Text, default="")
    video:   Mapped[str] = mapped_column(String(255), default="")
    img:     Mapped[str] = mapped_column(String(255), default="")
    full:    Mapped[str] = mapped_column(String(255), default="")
    fit:     Mapped[str] = mapped_column(String(20), default="cover")
    accent:  Mapped[str] = mapped_column(String(30), default="#37b2ea")
    seller_id:    Mapped[int] = mapped_column(Integer, index=True, default=0)
    seller_name:  Mapped[str] = mapped_column(String(120), default="")
    seller_phone: Mapped[str] = mapped_column(String(40), default="")
    bought_price: Mapped[str] = mapped_column(String(60), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    def as_dict(self, gallery=None):
        try:
            specs = json.loads(self.specs_json or "[]")
        except (ValueError, TypeError):
            specs = []
        return {"id": self.id, "brand": self.brand, "name": self.name, "year": self.year,
                "price": self.price, "badge": self.badge, "status": self.status,
                "fuel_type": self.fuel_type, "transmission": self.transmission,
                "specs": specs, "km": self.km, "engine": self.engine, "colour": self.colour,
                "desc": self.desc, "video": self.video, "img": self.img, "full": self.full,
                "fit": getattr(self, "fit", "cover"),
                "accent": getattr(self, "accent", "#37b2ea"),
                "seller_id": getattr(self, "seller_id", 0) or 0,
                "seller_name": getattr(self, "seller_name", "") or "",
                "seller_phone": getattr(self, "seller_phone", "") or "",
                "bought_price": getattr(self, "bought_price", "") or "",
                "gallery": gallery if gallery is not None else []}


class CarGallery(Base):
    __tablename__ = "car_gallery"
    id:         Mapped[int] = mapped_column(Integer, primary_key=True)
    car_id:     Mapped[int] = mapped_column(Integer, index=True)
    src:        Mapped[str] = mapped_column(String(255))
    cat:        Mapped[str] = mapped_column(String(50), default="exterior")  # exterior|interior|angle|document
    label:      Mapped[str] = mapped_column(String(100), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    def as_dict(self):
        return {"id": self.id, "car_id": self.car_id, "src": self.src,
                "cat": self.cat, "label": self.label, "sort_order": self.sort_order}


class Partner(Base):
    __tablename__ = "partners"
    id:         Mapped[int] = mapped_column(Integer, primary_key=True)
    name:       Mapped[str] = mapped_column(String(120), default="")
    role:       Mapped[str] = mapped_column(String(80), default="Partner")
    img:        Mapped[str] = mapped_column(String(255), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    def as_dict(self):
        return {"id": self.id, "name": self.name, "role": self.role, "img": self.img,
                "order": self.sort_order}


class Inquiry(Base):
    __tablename__ = "inquiries"
    id:      Mapped[int] = mapped_column(Integer, primary_key=True)
    name:    Mapped[str] = mapped_column(String(120))
    phone:   Mapped[str] = mapped_column(String(40))
    car:     Mapped[str] = mapped_column(String(120), default="")
    message: Mapped[str] = mapped_column(Text, default="")
    status:  Mapped[str] = mapped_column(String(30), default="new")  # new|contacted|test_drive|closed|lost
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    def as_dict(self):
        return {"id": self.id, "name": self.name, "phone": self.phone, "car": self.car,
                "message": self.message, "status": self.status or "new",
                "time": (self.created_at or _now()).strftime("%Y-%m-%d %H:%M")}


class Review(Base):
    __tablename__ = "reviews"
    id:       Mapped[int] = mapped_column(Integer, primary_key=True)
    name:     Mapped[str] = mapped_column(String(80))
    rating:   Mapped[int] = mapped_column(Integer, default=5)
    text:     Mapped[str] = mapped_column(Text)
    location: Mapped[str] = mapped_column(String(60), default="")
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    def as_dict(self):
        return {"id": self.id, "name": self.name, "rating": self.rating, "text": self.text,
                "location": self.location, "approved": self.approved,
                "time": (self.created_at or _now()).strftime("%Y-%m-%d")}


class Sale(Base):
    __tablename__ = "sales"
    id:            Mapped[int] = mapped_column(Integer, primary_key=True)
    car_id:        Mapped[int] = mapped_column(Integer, default=0)
    buyer_id:      Mapped[int] = mapped_column(Integer, index=True, default=0)
    car_desc:      Mapped[str] = mapped_column(String(200), default="")
    buyer_name:    Mapped[str] = mapped_column(String(120), default="")
    buyer_phone:   Mapped[str] = mapped_column(String(40), default="")
    price:         Mapped[str] = mapped_column(String(60), default="")   # internal only
    payment_method: Mapped[str] = mapped_column(String(50), default="")  # Cash|Bank Transfer|Loan/Finance|Cheque
    notes:         Mapped[str] = mapped_column(Text, default="")
    sold_on:       Mapped[datetime] = mapped_column(DateTime, default=_now)

    def as_dict(self):
        return {"id": self.id, "car_id": self.car_id, "buyer_id": self.buyer_id,
                "car_desc": self.car_desc, "buyer_name": self.buyer_name,
                "buyer_phone": self.buyer_phone, "price": self.price,
                "payment_method": self.payment_method, "notes": self.notes,
                "sold_on": (self.sold_on or _now()).strftime("%Y-%m-%d")}


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id:          Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id:     Mapped[int] = mapped_column(Integer, default=0)
    username:    Mapped[str] = mapped_column(String(60), default="")
    action:      Mapped[str] = mapped_column(String(100), default="")
    target_type: Mapped[str] = mapped_column(String(60), default="")
    target_id:   Mapped[int] = mapped_column(Integer, default=0)
    details:     Mapped[str] = mapped_column(Text, default="")
    ip_address:  Mapped[str] = mapped_column(String(60), default="")
    created_at:  Mapped[datetime] = mapped_column(DateTime, default=_now)

    def as_dict(self):
        return {"id": self.id, "user_id": self.user_id, "username": self.username,
                "action": self.action, "target_type": self.target_type,
                "target_id": self.target_id, "details": self.details,
                "ip_address": self.ip_address,
                "time": (self.created_at or _now()).strftime("%Y-%m-%d %H:%M")}


def init_db():
    """Create any missing tables & columns. Safe to call on every startup."""
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        for col_def in [
            ("accent", "VARCHAR(30) DEFAULT '#37b2ea'"),
            ("seller_id", "INTEGER DEFAULT 0"),
            ("seller_name", "VARCHAR(120) DEFAULT ''"),
            ("seller_phone", "VARCHAR(40) DEFAULT ''"),
            ("bought_price", "VARCHAR(60) DEFAULT ''")
        ]:
            try:
                conn.execute(text(f"ALTER TABLE cars ADD COLUMN {col_def[0]} {col_def[1]}"))
            except Exception:
                pass




# ── Users / auth ─────────────────────────────────────────────────────────────
VALID_ROLES = ("superadmin", "manager", "sales_rep")


def authenticate_user(username, password):
    """Return the user dict on a correct login (and active account), else None."""
    s = SessionLocal()
    try:
        u = s.execute(select(User).where(User.username == username)).scalars().first()
        if not u or not u.is_active or not u.password_hash:
            return None
        if not check_password_hash(u.password_hash, password):
            return None
        u.last_login = _now()
        s.commit()
        return u.as_dict()
    finally:
        s.close()


def create_user(username, password, role="sales_rep", full_name="", email="",
                must_change=False):
    """Create a user. Returns (dict, None) or (None, error_message)."""
    role = role if role in VALID_ROLES else "sales_rep"
    s = SessionLocal()
    try:
        if s.execute(select(User).where(User.username == username)).scalars().first():
            return None, "That username already exists."
        u = User(username=username.strip(), role=role, full_name=full_name.strip(),
                 email=email.strip(), is_active=True, must_change_password=must_change,
                 password_hash=generate_password_hash(password))
        s.add(u); s.commit()
        return u.as_dict(), None
    finally:
        s.close()


def update_user(user_id, full_name=None, email=None, role=None, password=None,
                is_active=None, clear_must_change=False):
    s = SessionLocal()
    try:
        u = s.get(User, user_id)
        if not u:
            return None
        if full_name is not None: u.full_name = full_name.strip()
        if email is not None:     u.email = email.strip()
        if role in VALID_ROLES:   u.role = role
        if is_active is not None: u.is_active = bool(is_active)
        if password:
            u.password_hash = generate_password_hash(password)
            u.must_change_password = False
        if clear_must_change:
            u.must_change_password = False
        s.commit()
        return u.as_dict()
    finally:
        s.close()


def delete_user(user_id):
    s = SessionLocal()
    try:
        s.execute(delete(User).where(User.id == user_id)); s.commit()
    finally:
        s.close()


def all_users():
    s = SessionLocal()
    try:
        rows = s.execute(select(User).order_by(User.id.asc())).scalars().all()
        return [u.as_dict() for u in rows]
    finally:
        s.close()


def get_user(user_id):
    s = SessionLocal()
    try:
        u = s.get(User, user_id)
        return u.as_dict() if u else None
    finally:
        s.close()


def count_users():
    s = SessionLocal()
    try:
        return s.execute(select(func.count()).select_from(User)).scalar() or 0
    finally:
        s.close()


def ensure_superadmin(username, password):
    """Seed ONE superadmin if there are no users yet. The seeded account is flagged
    must_change_password so the first login forces a fresh password."""
    if count_users() > 0:
        return False
    create_user(username, password, role="superadmin",
                full_name="Super Admin", must_change=True)
    return True


# ── Buyers ───────────────────────────────────────────────────────────────────
def get_or_create_buyer(name, phone, email="", address="", id_number="", notes=""):
    """Find a buyer by phone (or name if no phone), else create one. Returns dict."""
    s = SessionLocal()
    try:
        u = None
        if phone:
            u = s.execute(select(Buyer).where(Buyer.phone == phone)).scalars().first()
        if not u and name:
            u = s.execute(select(Buyer).where(Buyer.name == name)).scalars().first()
        if not u:
            u = Buyer(name=name or "", phone=phone or "")
            s.add(u)
        # fill in any newly provided detail fields
        if email:     u.email = email
        if address:   u.address = address
        if id_number: u.id_number = id_number
        if notes:     u.notes = (u.notes + "\n" + notes).strip() if u.notes else notes
        s.commit()
        return u.as_dict()
    finally:
        s.close()


def all_buyers():
    """Every buyer with derived metrics: cars bought + trade-in cars sold to dealership."""
    s = SessionLocal()
    try:
        buyers = s.execute(select(Buyer).order_by(Buyer.name.asc())).scalars().all()
        out = []
        for b in buyers:
            sales = s.execute(select(Sale).where(Sale.buyer_id == b.id)).scalars().all()
            trade_ins = s.execute(select(Car).where(Car.seller_id == b.id)).scalars().all()
            total_spent = sum(_price_to_int(x.price) for x in sales)
            total_trade_in = sum(_price_to_int(x.bought_price) for x in trade_ins)
            d = b.as_dict()
            d["purchases"] = len(sales)
            d["trade_ins_count"] = len(trade_ins)
            d["total_spent"] = total_spent
            d["total_trade_in"] = total_trade_in
            d["total_fmt"] = f"Rs. {total_spent:,}" if total_spent else "—"
            d["trade_in_fmt"] = f"Rs. {total_trade_in:,}" if total_trade_in else "—"

            history = []
            for sl in sales:
                history.append({
                    "type": "purchase",
                    "label": f"🛒 BOUGHT FROM US: {sl.car_desc}",
                    "date": sl.sold_on or "",
                    "price": sl.price or "—",
                    "details": f"Payment: {sl.payment_method or '—'}"
                })
            for tr in trade_ins:
                desc = f"{tr.brand} {tr.name} ({tr.year})".strip()
                created = tr.created_at.strftime("%Y-%m-%d") if tr.created_at else ""
                history.append({
                    "type": "trade_in",
                    "label": f"🔄 TRADED IN / SOLD TO US: {desc}",
                    "date": created,
                    "price": tr.bought_price or "—",
                    "details": f"Status: {tr.status.capitalize()}"
                })
            history.sort(key=lambda x: x["date"], reverse=True)
            d["history"] = history
            out.append(d)
        return out
    finally:
        s.close()



def get_buyer_by_id(buyer_id):
    s = SessionLocal()
    try:
        b = s.get(Buyer, buyer_id)
        return b.as_dict() if b else None
    finally:
        s.close()


def get_buyer_sales(buyer_id):
    s = SessionLocal()
    try:
        rows = s.execute(select(Sale).where(Sale.buyer_id == buyer_id)
                         .order_by(Sale.id.desc())).scalars().all()
        return [r.as_dict() for r in rows]
    finally:
        s.close()


def delete_buyer(buyer_id):
    s = SessionLocal()
    try:
        s.execute(delete(Buyer).where(Buyer.id == buyer_id)); s.commit()
    finally:
        s.close()


def _price_to_int(price):
    digits = "".join(ch for ch in (price or "") if ch.isdigit())
    return int(digits) if digits else 0


# ── Cars (inventory) + gallery ───────────────────────────────────────────────
def _car_gallery(session, car_id):
    rows = session.execute(select(CarGallery).where(CarGallery.car_id == car_id)
                           .order_by(CarGallery.sort_order.asc(), CarGallery.id.asc())
                           ).scalars().all()
    return [g.as_dict() for g in rows]


def all_cars_db():
    s = SessionLocal()
    try:
        cars = s.execute(select(Car).order_by(Car.id.asc())).scalars().all()
        return [c.as_dict(gallery=_car_gallery(s, c.id)) for c in cars]
    finally:
        s.close()


def get_car_db(car_id):
    s = SessionLocal()
    try:
        c = s.get(Car, car_id)
        return c.as_dict(gallery=_car_gallery(s, c.id)) if c else None
    finally:
        s.close()


def _apply_car_fields(c, data):
    c.brand = data.get("brand", c.brand or "")
    c.name = data.get("name", c.name or "")
    c.year = data.get("year", "")
    c.price = data.get("price", "")
    c.badge = data.get("badge", "In stock") or "In stock"
    c.status = data.get("status", "available")
    c.fuel_type = data.get("fuel_type", "")
    c.transmission = data.get("transmission", "")
    specs = data.get("specs", [])
    c.specs_json = json.dumps(specs, ensure_ascii=False)
    c.km = specs[0] if len(specs) > 0 else ""
    c.engine = specs[1] if len(specs) > 1 else ""
    c.colour = specs[2] if len(specs) > 2 else ""
    c.desc = data.get("desc", "")
    c.video = data.get("video", "")
    if data.get("img"):
        c.img = data["img"]
    if data.get("full"):
        c.full = data["full"]
    c.fit = data.get("fit", c.fit or "cover")
    c.accent = data.get("accent", c.accent or "#37b2ea")

    seller_id = int(data.get("seller_id", c.seller_id or 0))
    seller_name = data.get("seller_name", c.seller_name or "").strip()
    seller_phone = data.get("seller_phone", c.seller_phone or "").strip()
    if not seller_id and (seller_name or seller_phone):
        sb = get_or_create_buyer(seller_name, seller_phone)
        if sb:
            seller_id = sb["id"]
            seller_name = sb["name"]
            seller_phone = sb["phone"]
    c.seller_id = seller_id
    c.seller_name = seller_name
    c.seller_phone = seller_phone
    c.bought_price = data.get("bought_price", c.bought_price or "").strip()



def save_car_db(data):
    """Insert (no id) or update (with id) a car. Returns the car dict."""
    s = SessionLocal()
    try:
        c = s.get(Car, data["id"]) if data.get("id") else None
        if not c:
            c = Car()
            s.add(c)
        _apply_car_fields(c, data)
        s.commit()
        return c.as_dict(gallery=_car_gallery(s, c.id))
    finally:
        s.close()


def delete_car_db(car_id):
    s = SessionLocal()
    try:
        s.execute(delete(CarGallery).where(CarGallery.car_id == car_id))
        s.execute(delete(Car).where(Car.id == car_id))
        s.commit()
    finally:
        s.close()


def add_car_gallery_photo(car_id, src, cat="exterior", label=""):
    s = SessionLocal()
    try:
        n = s.execute(select(func.count()).select_from(CarGallery)
                      .where(CarGallery.car_id == car_id, CarGallery.cat == cat)).scalar() or 0
        g = CarGallery(car_id=car_id, src=src, cat=cat,
                       label=label or f"{cat.capitalize()} {n + 1}", sort_order=n + 1)
        s.add(g); s.commit()
        return g.as_dict()
    finally:
        s.close()


def delete_car_gallery_photo(car_id, src):
    s = SessionLocal()
    try:
        s.execute(delete(CarGallery).where(CarGallery.car_id == car_id,
                                           CarGallery.src == src))
        s.commit()
    finally:
        s.close()


def next_car_id_db():
    s = SessionLocal()
    try:
        m = s.execute(select(func.max(Car.id))).scalar()
        return (m or 0) + 1
    finally:
        s.close()


# ── Partners ─────────────────────────────────────────────────────────────────
def all_partners_db():
    s = SessionLocal()
    try:
        rows = s.execute(select(Partner).order_by(Partner.sort_order.asc(),
                                                   Partner.id.asc())).scalars().all()
        return [p.as_dict() for p in rows]
    finally:
        s.close()


def add_partner_db(name, role="Partner", img="", order=None):
    s = SessionLocal()
    try:
        if order is None:
            m = s.execute(select(func.max(Partner.sort_order))).scalar()
            order = (m or 0) + 1
        p = Partner(name=name, role=role or "Partner", img=img, sort_order=order)
        s.add(p); s.commit()
        return p.as_dict()
    finally:
        s.close()


def update_partner_db(partner_id, name=None, role=None, order=None):
    s = SessionLocal()
    try:
        p = s.get(Partner, partner_id)
        if not p:
            return None
        if name is not None: p.name = name
        if role is not None: p.role = role or "Partner"
        if order is not None: p.sort_order = order
        s.commit()
        return p.as_dict()
    finally:
        s.close()


def delete_partner_db(partner_id):
    s = SessionLocal()
    try:
        s.execute(delete(Partner).where(Partner.id == partner_id)); s.commit()
    finally:
        s.close()


# ── Inquiries (CRM leads) ────────────────────────────────────────────────────
def add_inquiry(name, phone, car="", message=""):
    s = SessionLocal()
    try:
        row = Inquiry(name=name, phone=phone, car=car, message=message, status="new")
        s.add(row); s.commit()
        return row.as_dict()
    finally:
        s.close()


def all_inquiries():
    s = SessionLocal()
    try:
        rows = s.execute(select(Inquiry).order_by(Inquiry.id.desc())).scalars().all()
        return [r.as_dict() for r in rows]
    finally:
        s.close()


VALID_LEAD_STATUS = ("new", "contacted", "test_drive", "closed", "lost")


def update_inquiry_status(inquiry_id, status):
    if status not in VALID_LEAD_STATUS:
        return
    s = SessionLocal()
    try:
        row = s.get(Inquiry, inquiry_id)
        if row:
            row.status = status; s.commit()
    finally:
        s.close()


def delete_inquiry(inquiry_id):
    s = SessionLocal()
    try:
        s.execute(delete(Inquiry).where(Inquiry.id == inquiry_id)); s.commit()
    finally:
        s.close()


# ── Reviews ──────────────────────────────────────────────────────────────────
def add_review(name, rating, text, location=""):
    s = SessionLocal()
    try:
        row = Review(name=name, rating=rating, text=text, location=location, approved=False)
        s.add(row); s.commit()
        return row.as_dict()
    finally:
        s.close()


def all_reviews():
    s = SessionLocal()
    try:
        rows = s.execute(select(Review).order_by(Review.approved.asc(),
                                                  Review.id.desc())).scalars().all()
        return [r.as_dict() for r in rows]
    finally:
        s.close()


def approved_reviews():
    s = SessionLocal()
    try:
        rows = s.execute(select(Review).where(Review.approved.is_(True))
                         .order_by(Review.id.desc())).scalars().all()
        return [r.as_dict() for r in rows]
    finally:
        s.close()


def approve_review(review_id):
    s = SessionLocal()
    try:
        row = s.get(Review, review_id)
        if row:
            row.approved = True; s.commit()
    finally:
        s.close()


def delete_review(review_id):
    s = SessionLocal()
    try:
        s.execute(delete(Review).where(Review.id == review_id)); s.commit()
    finally:
        s.close()


def add_sale(car_id=0, car_desc="", buyer_name="", buyer_phone="", price="",
             payment_method="", notes="", buyer_email="", buyer_address="",
             buyer_id_number="", buyer_id=0):
    """Record a sale and auto-link (or create) the matching Buyer profile."""
    buyer = None
    if buyer_id:
        buyer = get_buyer_by_id(buyer_id)
    if not buyer and (buyer_name or buyer_phone):
        buyer = get_or_create_buyer(buyer_name, buyer_phone, email=buyer_email,
                                    address=buyer_address, id_number=buyer_id_number,
                                    notes=notes)
    b_name = buyer_name or (buyer["name"] if buyer else "")
    b_phone = buyer_phone or (buyer["phone"] if buyer else "")
    s = SessionLocal()
    try:
        row = Sale(car_id=car_id, buyer_id=(buyer["id"] if buyer else 0),
                   car_desc=car_desc, buyer_name=b_name, buyer_phone=b_phone,
                   price=price, payment_method=payment_method, notes=notes)
        s.add(row); s.commit()
        return row.as_dict()
    finally:
        s.close()



def all_sales():
    s = SessionLocal()
    try:
        rows = s.execute(select(Sale).order_by(Sale.id.desc())).scalars().all()
        return [r.as_dict() for r in rows]
    finally:
        s.close()


def delete_sale(sale_id):
    s = SessionLocal()
    try:
        s.execute(delete(Sale).where(Sale.id == sale_id)); s.commit()
    finally:
        s.close()


def sales_total():
    s = SessionLocal()
    try:
        rows = s.execute(select(Sale.price)).scalars().all()
        return sum(_price_to_int(p) for p in rows)
    finally:
        s.close()


# ── Audit log ────────────────────────────────────────────────────────────────
def log_audit(user_id=0, username="", action="", target_type="", target_id=0,
              details="", ip_address=""):
    s = SessionLocal()
    try:
        s.add(AuditLog(user_id=user_id, username=username, action=action,
                       target_type=target_type, target_id=target_id,
                       details=details, ip_address=ip_address))
        s.commit()
    finally:
        s.close()


def all_audit_logs(limit=300):
    s = SessionLocal()
    try:
        rows = s.execute(select(AuditLog).order_by(AuditLog.id.desc())
                         .limit(limit)).scalars().all()
        return [r.as_dict() for r in rows]
    finally:
        s.close()


# ── Diagnostics + counts ─────────────────────────────────────────────────────
def _has_rows(model):
    s = SessionLocal()
    try:
        return s.execute(select(model)).scalars().first() is not None
    finally:
        s.close()


def count_rows():
    return {"inquiries": _has_rows(Inquiry), "reviews": _has_rows(Review),
            "cars": _has_rows(Car), "partners": _has_rows(Partner)}


def check_db_status():
    """A tiny health check for the admin: engine + connectivity + row counts."""
    engine_name = "MySQL" if not _IS_SQLITE else "SQLite"
    info = {"engine": engine_name, "connected": False, "counts": {}}
    s = SessionLocal()
    try:
        for label, model in (("users", User), ("cars", Car), ("partners", Partner),
                             ("inquiries", Inquiry), ("reviews", Review),
                             ("buyers", Buyer), ("sales", Sale), ("audit_logs", AuditLog)):
            info["counts"][label] = s.execute(select(func.count()).select_from(model)).scalar() or 0
        info["connected"] = True
    except Exception as e:  # noqa: BLE001 — report any DB error to the admin, don't crash
        info["error"] = str(e)
    finally:
        s.close()
    return info


# ── One-time JSON → DB migrations ────────────────────────────────────────────
def _parse_dt(value, fmt):
    try:
        return datetime.strptime(str(value), fmt)
    except (ValueError, TypeError):
        return _now()


def _guess_fuel(specs):
    for s in specs:
        for f in ("Petrol", "Diesel", "Electric", "Hybrid"):
            if f.lower() in s.lower():
                return f
    return ""


def _guess_transmission(specs):
    for s in specs:
        if "automatic" in s.lower():
            return "Automatic"
        if "manual" in s.lower():
            return "Manual"
    return ""


def bulk_import_cars_from_json(items):
    s = SessionLocal()
    try:
        for it in items:
            specs = it.get("specs", []) or []
            c = Car(
                id=it.get("id") or None,
                brand=it.get("brand", ""), name=it.get("name", ""), year=str(it.get("year", "")),
                price=it.get("price", ""), badge=it.get("badge", "In stock") or "In stock",
                status=it.get("status", "available") or "available",
                fuel_type=it.get("fuel_type", "") or _guess_fuel(specs),
                transmission=it.get("transmission", "") or _guess_transmission(specs),
                specs_json=json.dumps(specs, ensure_ascii=False),
                km=it.get("km", "") or (specs[0] if len(specs) > 0 else ""),
                engine=it.get("engine", "") or (specs[1] if len(specs) > 1 else ""),
                colour=it.get("colour", "") or (specs[2] if len(specs) > 2 else ""),
                desc=it.get("desc", ""), video=it.get("video", ""),
                img=it.get("img", ""), full=it.get("full", ""),
                fit=it.get("fit", "cover") or "cover", accent=it.get("accent", "#37b2ea"))
            s.add(c)
            s.flush()   # get c.id for the gallery rows
            for i, g in enumerate(it.get("gallery", []) or []):
                s.add(CarGallery(car_id=c.id, src=g.get("src", ""),
                                 cat=g.get("cat", "exterior"),
                                 label=g.get("label", ""), sort_order=i + 1))
        s.commit()
    finally:
        s.close()


def bulk_import_partners_from_json(items):
    s = SessionLocal()
    try:
        for i, it in enumerate(items):
            s.add(Partner(id=it.get("id") or None, name=it.get("name", ""),
                          role=it.get("role", "Partner") or "Partner",
                          img=it.get("img", ""),
                          sort_order=it.get("order", i + 1) if it.get("order") is not None else i + 1))
        s.commit()
    finally:
        s.close()


def bulk_import_inquiries(items):
    s = SessionLocal()
    try:
        for it in items:
            s.add(Inquiry(name=(it.get("name") or "")[:120], phone=(it.get("phone") or "")[:40],
                          car=(it.get("car") or "")[:120], message=(it.get("message") or "")[:3000],
                          status=it.get("status", "new") or "new",
                          created_at=_parse_dt(it.get("time", ""), "%Y-%m-%d %H:%M")))
        s.commit()
    finally:
        s.close()


def bulk_import_reviews(items):
    s = SessionLocal()
    try:
        for it in items:
            try:
                rating = int(it.get("rating", 5) or 5)
            except (ValueError, TypeError):
                rating = 5
            s.add(Review(name=(it.get("name") or "")[:80], rating=max(1, min(5, rating)),
                         text=(it.get("text") or "")[:1000], location=(it.get("location") or "")[:60],
                         approved=bool(it.get("approved", False)),
                         created_at=_parse_dt(it.get("time", ""), "%Y-%m-%d")))
        s.commit()
    finally:
        s.close()
