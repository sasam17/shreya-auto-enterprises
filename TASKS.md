# 📋 Shreya Auto Enterprises — Development Task Checklist

> **Task List for Team Developers**: Complete checklist covering database architecture, RBAC authentication, executive Admin UI/UX overhaul, buyer purchase history, and premium dealership features.

---

### 🛢️ Phase 1: Database & Configuration (`config.py` & `db.py`)
- [ ] **Configure MySQL Connection**: Update `config.py` to build database connection strings supporting `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DB`, or `SHREYA_DATABASE_URL` with automatic fallback to SQLite for local development.
- [ ] **Set Superadmin Defaults**: Define default `SUPERADMIN_USERNAME` and `SUPERADMIN_PASSWORD` in `config.py`.
- [ ] **Define SQLAlchemy Models in `db.py`**:
  - `User`: `id`, `username`, `email`, `password_hash`, `full_name`, `role` (`superadmin`, `manager`, `sales_rep`), `is_active`, `created_at`, `last_login`.
  - `Buyer`: `id`, `name`, `phone`, `email`, `address`, `id_number` (Citizenship/PAN/License No), `notes`, `created_at`.
  - `Car`: `id`, `brand`, `name`, `year`, `price`, `badge`, `status`, `fuel_type`, `transmission`, `specs_json`, `km`, `engine`, `colour`, `desc`, `video`, `img`, `full`, `fit`, `accent`, `created_at`.
  - `CarGallery`: `id`, `car_id`, `src`, `cat` (`exterior`, `interior`, `angle`, `document`), `label`, `sort_order`.
  - `Partner`: `id`, `name`, `role`, `img`, `sort_order`, `created_at`.
  - `Inquiry`: `id`, `name`, `phone`, `car`, `message`, `status` (`new`, `contacted`, `test_drive`, `closed`, `lost`), `created_at`.
  - `Review`: `id`, `name`, `rating`, `text`, `location`, `approved`, `created_at`.
  - `Sale`: `id`, `car_id`, `buyer_id`, `car_desc`, `buyer_name`, `buyer_phone`, `price`, `payment_method`, `notes`, `sold_on`.
  - `AuditLog`: `id`, `user_id`, `username`, `action`, `target_type`, `target_id`, `details`, `ip_address`, `created_at`.
- [ ] **Implement Database Helper Functions**:
  - **Auth Helpers**: `authenticate_user()`, `create_user()`, `update_user()`, `delete_user()`, `all_users()`.
  - **Buyer Helpers**: `get_or_create_buyer()`, `all_buyers()`, `get_buyer_by_id()`, `get_buyer_sales()`, `delete_buyer()`.
  - **Inventory & Gallery Helpers**: `all_cars_db()`, `get_car_db()`, `save_car_db()`, `delete_car_db()`, `add_car_gallery_photo()`, `delete_car_gallery_photo()`.
  - **CRM Pipeline Helper**: `update_inquiry_status()`.
  - **Audit Log Helper**: `log_audit()`, `all_audit_logs()`.
  - **One-Time JSON Seed Migration**: `bulk_import_cars_from_json()`, `bulk_import_partners_from_json()`.
  - **DB Diagnostics**: `check_db_status()`.

---

### ⚙️ Phase 2: Backend Application & RBAC Routes (`app.py`)
- [ ] **Implement RBAC Security Decorators**: `@admin_required` with 30-min idle sliding session timeout and `@roles_required(*roles)` for privilege enforcement.
- [ ] **Database Bootstrap on Startup**: Run `db.init_db()` and seed `cars`, `partners`, `inquiries`, and `reviews` from JSON files if database tables are empty.
- [ ] **Admin Authentication Routes**:
  - `POST /admin/login`: Verify username and password hash, start RBAC session, record audit log.
  - `GET /admin/logout`: Clear session, record audit log.
- [ ] **Admin Management Routes**:
  - `GET /admin`: Render executive tabbed dashboard with financial stats, inventory, CRM leads, buyers directory, reviews, partners, users (Super Admin), and audit logs (Super Admin).
  - `POST /admin/user/create`, `/update`, `/toggle`, `/delete`: Super Admin user account management.
  - `POST /admin/inquiry/status`: Update lead CRM status (`new`, `contacted`, `test_drive`, `closed`, `lost`).
  - `POST /admin/buyer/delete`: Remove buyer profile.
  - `POST /admin/add`, `/edit`, `/delete`, `/gallery/delete`: Inventory and gallery CRUD.
  - `POST /admin/partner/add`, `/update`, `/delete`: Team & partner CRUD.
  - `POST /admin/review/approve`, `/delete`: Review approval workflow.
  - `GET /admin/export/<kind>`: Export CSV for inquiries, reviews, sales, buyers, cars, and users.
- [ ] **Public Routes**:
  - `GET /car/<int:car_id>/print`: Printable window sticker / spec sheet HTML view.
  - `GET /compare`: Side-by-side vehicle comparison page for up to 3 cars.
  - `GET /sitemap.xml`: Dynamic XML sitemap for search engine SEO indexing.
  - `GET /cars`: Filter inventory by search query (`q`), fuel type (`fuel`), and transmission (`transmission`).

---

### 🎨 Phase 3: Executive Admin Dashboard UI/UX & Templates (`templates/` & `static/`)
- [ ] **Overhaul `templates/admin.html` (Executive UI & UX)**:
  - **Glassmorphic Header Bar**: Dark cinematic header (`#06182e`), brand badge, user role pill (`SUPERADMIN`, `MANAGER`, `SALES_REP`), quick website link, and logout.
  - **Tabbed Dashboard Navigation**:
    - 📊 **Executive Analytics**: Revenue stat cards, sold vehicles count, active inventory metrics, pipeline status, DB health ping.
    - 🚗 **Inventory Grid Cards**: Photo thumbnail, brand/model, price, status badge (`Available`/`Sold`), spec sheet print button, delete button.
    - 💬 **CRM Lead Pipeline**: Table/Kanban view with status dropdown selectors (`🟢 New`, `🔵 Contacted`, `🟣 Test Drive`, `✅ Deal Closed`, `🔴 Lost`) and 1-Click WhatsApp direct chat buttons.
    - 👤 **Buyer Directory & LTV History**: Customer table with total purchase counts, lifetime value (LTV), address, ID number, and purchase timeline drawers.
    - ⭐ **Customer Reviews**: Approval workflow table with star ratings.
    - 👥 **Team & Partners**: Member grid with photo upload and role title inline editor.
    - 🔑 **User Accounts (Super Admin)**: Account creation form, role selector, enable/disable toggle, and password reset.
    - 📜 **Security Audit Logs (Super Admin)**: Action history table tracking user actions, IP addresses, and timestamps.
- [ ] **Create `templates/compare.html`**:
  - Side-by-side comparison table comparing engine, fuel type, transmission, mileage, features, and photos.
- [ ] **Create `templates/print_spec.html`**:
  - Clean, print-optimized window sticker layout for walk-in showroom visitors.
- [ ] **Update `templates/car.html`**:
  - Categorized photo gallery tabs (Exterior, Interior, Angles, Documents).
  - Interactive EMI Loan Calculator widget.
  - Printable Spec Sheet button and Compare Vehicle button.
- [ ] **Update `templates/cars.html`**:
  - Multi-filter bar (Search input, Fuel Type dropdown, Transmission dropdown).
- [ ] **Update `templates/index.html`**:
  - Dark/Light mode theme toggle button and quick EMI calculator preview.
- [ ] **Update `static/assets/css/styles.css` & `main.js`**:
  - Styling for executive admin tabs, glassmorphism cards, status badges, role badges, CRM status tags, EMI calculator, and comparison table.
  - JavaScript logic for EMI calculation math, vehicle comparison state (`localStorage`), and theme switcher.
