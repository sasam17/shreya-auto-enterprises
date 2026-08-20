# 🚀 Technical Architecture & Implementation Plan — Shreya Auto Enterprises

> **Notice for Development Team**: This document outlines the complete technical design, database schemas, access control matrix, executive Admin UI/UX overhaul, and feature specifications required to upgrade **Shreya Auto Enterprises** into a high-converting, enterprise-grade auto dealership platform.

---

## 1. 🛢️ Comprehensive MySQL Database Configuration

### 1.1 Dual Engine Architecture (SQLite Local ↔ MySQL Production)
- **Database Layer**: SQLAlchemy `2.0+` with `PyMySQL` driver.
- **Environment Auto-Detection**:
  - **Local Development**: Default to `sqlite:///data/shreya.db` (zero-config local dev).
  - **Production MySQL**: Auto-detect `SHREYA_DATABASE_URL` or individual `MYSQL_*` environment variables:
    ```ini
    SHREYA_DATABASE_URL=mysql+pymysql://user:password@localhost:3306/shreya_db?charset=utf8mb4
    # OR explicit variables:
    MYSQL_HOST=localhost
    MYSQL_PORT=3306
    MYSQL_USER=shreya_user
    MYSQL_PASSWORD=secure_password
    MYSQL_DB=shreya_db
    ```
- **Connection Pool Tuning (`db.py`)**:
  ```python
  engine = create_engine(
      DATABASE_URL,
      pool_size=10,
      max_overflow=20,
      pool_recycle=3600,
      pool_pre_ping=True
  )
  ```

### 1.2 Relational Database Schema (`db.py`)
Migrate from flat JSON storage (`cars.json`, `partners.json`) to full relational SQLAlchemy models:

1. **`users` Table (RBAC Authentication)**
   - `id`: `INTEGER PRIMARY KEY AUTOINCREMENT`
   - `username`: `VARCHAR(60) UNIQUE INDEX`
   - `email`: `VARCHAR(120)`
   - `password_hash`: `VARCHAR(255)`
   - `full_name`: `VARCHAR(120)`
   - `role`: `VARCHAR(30)` (`superadmin`, `manager`, `sales_rep`)
   - `is_active`: `BOOLEAN DEFAULT TRUE`
   - `created_at`: `DATETIME`
   - `last_login`: `DATETIME NULLABLE`

2. **`buyers` Table (Customer Management & Purchase History)**
   - `id`: `INTEGER PRIMARY KEY AUTOINCREMENT`
   - `name`: `VARCHAR(120) INDEX` (Customer Full Name)
   - `phone`: `VARCHAR(40) INDEX` (Primary Contact Phone)
   - `email`: `VARCHAR(120)` (Email Address)
   - `address`: `VARCHAR(255)` (Address / City)
   - `id_number`: `VARCHAR(60)` (Citizenship / PAN / License No for ownership transfer)
   - `notes`: `TEXT` (Customer preferences, notes)
   - `created_at`: `DATETIME`

3. **`cars` Table (Inventory Management)**
   - `id`: `INTEGER PRIMARY KEY AUTOINCREMENT`
   - `brand`: `VARCHAR(100) INDEX`
   - `name`: `VARCHAR(150)`
   - `year`: `VARCHAR(20)`
   - `price`: `VARCHAR(60)` (Internal only, hidden from public)
   - `badge`: `VARCHAR(50)` (e.g., "In stock", "Hot Deal", "Just Arrived")
   - `status`: `VARCHAR(30) INDEX` (`available`, `sold`, `reserved`)
   - `fuel_type`: `VARCHAR(40) INDEX` (`Petrol`, `Diesel`, `Electric`, `Hybrid`)
   - `transmission`: `VARCHAR(40) INDEX` (`Manual`, `Automatic`)
   - `specs_json`: `TEXT` (Stored JSON list of feature tags)
   - `km`: `VARCHAR(60)`
   - `engine`: `VARCHAR(60)`
   - `colour`: `VARCHAR(60)`
   - `desc`: `TEXT`
   - `video`: `VARCHAR(255)`
   - `img`: `VARCHAR(255)` (Card thumbnail)
   - `full`: `VARCHAR(255)` (High-res photo)
   - `fit`: `VARCHAR(20)` (`cover` / `contain`)
   - `accent`: `VARCHAR(30)`

4. **`car_gallery` Table (Categorized Multi-Photo Gallery)**
   - `id`: `INTEGER PRIMARY KEY AUTOINCREMENT`
   - `car_id`: `INTEGER INDEX` (FK to `cars.id`)
   - `src`: `VARCHAR(255)`
   - `cat`: `VARCHAR(50)` (`exterior`, `interior`, `angle`, `document`)
   - `label`: `VARCHAR(100)`
   - `sort_order`: `INTEGER DEFAULT 0`

5. **`partners` Table (Team Profiles)**
   - `id`: `INTEGER PRIMARY KEY AUTOINCREMENT`
   - `name`: `VARCHAR(120)`
   - `role`: `VARCHAR(80)`
   - `img`: `VARCHAR(255)`
   - `sort_order`: `INTEGER DEFAULT 0`

6. **`inquiries` Table (CRM Leads)**
   - `id`: `INTEGER PRIMARY KEY AUTOINCREMENT`
   - `name`: `VARCHAR(120)`
   - `phone`: `VARCHAR(40)`
   - `car`: `VARCHAR(120)`
   - `message`: `TEXT`
   - `status`: `VARCHAR(30)` (`new`, `contacted`, `test_drive`, `closed`, `lost`)
   - `created_at`: `DATETIME`

7. **`reviews` Table (Customer Reviews)**
   - `id`: `INTEGER PRIMARY KEY AUTOINCREMENT`
   - `name`: `VARCHAR(80)`
   - `rating`: `INTEGER` (1-5)
   - `text`: `TEXT`
   - `location`: `VARCHAR(60)`
   - `approved`: `BOOLEAN DEFAULT FALSE`

8. **`sales` Table (Buyer Capture & Financial Records)**
   - `id`: `INTEGER PRIMARY KEY AUTOINCREMENT`
   - `car_id`: `INTEGER` (FK to `cars.id`)
   - `buyer_id`: `INTEGER INDEX` (FK to `buyers.id`)
   - `car_desc`: `VARCHAR(200)`
   - `buyer_name`: `VARCHAR(120)`
   - `buyer_phone`: `VARCHAR(40)`
   - `price`: `VARCHAR(60)`
   - `payment_method`: `VARCHAR(50)` (`Cash`, `Bank Transfer`, `Loan/Finance`, `Cheque`)
   - `notes`: `TEXT`
   - `sold_on`: `DATETIME`

9. **`audit_logs` Table (Security Audit Trail)**
   - `id`: `INTEGER PRIMARY KEY AUTOINCREMENT`
   - `user_id`: `INTEGER`
   - `username`: `VARCHAR(60)`
   - `action`: `VARCHAR(100)`
   - `target_type`: `VARCHAR(60)`
   - `target_id`: `INTEGER`
   - `details`: `TEXT`
   - `ip_address`: `VARCHAR(60)`
   - `created_at`: `DATETIME`

---

## 2. 🔐 User Authentication & Role-Based Access Control (RBAC)

### 2.1 Password Hashing & Auth Flow
- **Password Security**: Use `werkzeug.security.generate_password_hash` (PBKDF2 with SHA-256).
- **Default Superadmin**: Auto-create default account (`admin` / `admin123`) on initial database creation if `User` table is empty.

### 2.2 Privilege Hierarchy Matrix

| Privilege / Action | Super Admin (`superadmin`) | Manager (`manager`) | Sales Rep (`sales_rep`) |
| :--- | :---: | :---: | :---: |
| **Manage Users & Privileges** | ✅ | ❌ | ❌ |
| **View Audit Logs & DB Health** | ✅ | ❌ | ❌ |
| **Financial Revenue & Sales Totals**| ✅ | ❌ | ❌ |
| **Buyer Directory & Purchase History**| ✅ | ✅ | ✅ |
| **Add / Edit Inventory & Gallery** | ✅ | ✅ | ❌ (View only) |
| **Manage Team / Partners** | ✅ | ✅ | ❌ |
| **Approve / Delete Reviews** | ✅ | ✅ | ❌ |
| **CRM Lead Pipeline & Status** | ✅ | ✅ | ✅ |
| **Record Car Sale / Buyer Data** | ✅ | ✅ | ✅ |

---

## 3. 🎨 Executive Admin Dashboard Redesign Specification (UI/UX Overhaul)

### 3.1 Modern Dashboard Layout Architecture
- **Glassmorphic Header Bar**: Dark cinematic header (`#06182e`) featuring:
  - Shreya Auto Brand Logo & Portal Badge.
  - Active User Pill: Full Name, Username, and Role Badge (`SUPERADMIN`, `MANAGER`, `SALES_REP`).
  - Quick Action Buttons (View Live Website, Export Reports, Logout).
- **Tabbed Executive Dashboard Navigation**:
  - 📊 **Executive Analytics**: Key metric cards (Total Sales Revenue, Available Cars, Sold Cars, Hot Leads, Registered Buyers, DB Status).
  - 🚗 **Inventory Management**: Grid cards with thumbnail, brand/model, price, status badge, and photo upload dropzone.
  - 💬 **CRM Lead Pipeline**: Table/Kanban view with status pill dropdowns (`🟢 New`, `🔵 Contacted`, `🟣 Test Drive`, `✅ Deal Closed`, `🔴 Lost`) and 1-Click WhatsApp direct chat buttons.
  - 👤 **Buyer Directory & LTV History**: Customer table with total purchase counts, lifetime value (LTV), address, ID number, and purchase timeline drawers.
  - ⭐ **Customer Reviews**: Approval workflow table with star ratings.
  - 👥 **Team & Partners**: Member grid with photo upload and role title inline editor.
  - 🔑 **User Accounts (Super Admin)**: RBAC account creation form, role selector, enable/disable toggle, and password reset.
  - 📜 **Security Audit Logs (Super Admin)**: Searchable action log table tracking user activities, IP addresses, and timestamps.

### 3.2 Visual & UX Components
- **Executive Metric Cards**: Large `Space Grotesk` numbers, gradient borders, trend indicators, subtle hover elevation.
- **Glassmorphic Cards**: `background: rgba(255,255,255,0.9)`, `backdrop-filter: blur(12px)`, `border: 1px solid rgba(11,58,119,0.12)`.
- **Status Badges & Chips**:
  - `Available`: Soft green badge (`#e2f6ea`, text `#1ba94c`)
  - `Sold`: Soft red badge (`#fde8e8`, text `#c0392b`)
  - `Super Admin`: Soft purple badge (`#fce8f4`, text `#a91b8a`)
  - `Manager`: Soft blue badge (`#e8f4fc`, text `#0b3a77`)
  - `Sales Rep`: Soft green badge (`#e2f6ea`, text `#1ba94c`)

---

## 4. 👤 Buyer Directory & Customer Purchase History System

### 4.1 Lifetime Value (LTV) & Customer Directory
- **Dedicated Admin Tab**: "👤 Buyers Directory" listing registered dealership clients.
- **Auto-Linking Sales to Buyers**: When a vehicle is marked as "Sold", automatically check if buyer exists by phone/name. If not, create a `Buyer` profile and link the sale transaction.
- **Buyer Metrics**:
  - Total vehicles purchased count.
  - Total money spent (formatted in Rs. / NPR).
  - Citizenship / PAN / ID references for transfer records.
  - Full purchase history timeline per customer.

---

## 5. 🌟 Premium Dealership Features

### 5.1 🧮 Interactive EMI Loan Calculator
- **Inputs**: Vehicle Price (NPR / Rs.), Down Payment (%), Loan Tenure (12–84 Months), Interest Rate (%).
- **Outputs**: Estimated Monthly EMI, Total Interest, Total Payable Amount formatted in Nepali/Indian comma system (`Rs. 48,00,000`).

### 5.2 ⚖️ Side-by-Side Vehicle Comparison Tool
- Compare up to 3 cars simultaneously at `/compare?id=1&id=2`.
- Compare Engine, Fuel Type, Transmission, Mileage, Dimensions, Safety Features, and Photos.

### 5.3 📸 Categorized 360° Photo Gallery & Video Showroom
- Photo categories: Exterior, Interior, Angles, Documents.
- Lightbox modal viewer & embedded YouTube video player.

### 5.4 📈 CRM Lead Pipeline & Instant WhatsApp Integration
- Lead Status Pipeline selector: `New` -> `Contacted` -> `Test Drive Scheduled` -> `Closed` -> `Lost`.
- **1-Click WhatsApp Lead Action**: Direct pre-filled WhatsApp message URL (`wa.me`).

### 5.5 📄 Showroom Printable Spec Sheet / Window Sticker
- Route: `/car/<car_id>/print`
- Print-optimized layout formatted as an official Dealership Window Sticker.

### 5.6 🌓 Dark/Light Cinematic Theme Switcher
- Persistent theme toggle (`data-theme="dark"` / `"light"` saved in `localStorage`).

### 5.7 🔍 SEO Optimization & Rich Snippets
- Dynamic XML Sitemap (`/sitemap.xml`) & Schema.org `Vehicle` / `AutomotiveBusiness` JSON-LD structured data.

---

## 6. 🛠️ Team Developer Implementation Roadmap

### Step 1: Update `config.py`
- Add database URL builder function supporting `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DB`.
- Add `SUPERADMIN_USERNAME` and `SUPERADMIN_PASSWORD` defaults.

### Step 2: Update `db.py`
- Declare SQLAlchemy models: `User`, `Buyer`, `Car`, `CarGallery`, `Partner`, `Inquiry`, `Review`, `Sale`, `AuditLog`.
- Add user authentication helpers (`authenticate_user`, `create_user`, `update_user`, `delete_user`).
- Add buyer history helpers (`get_or_create_buyer`, `all_buyers`, `get_buyer_by_id`, `delete_buyer`).
- Add inventory, gallery, partner, review, sale, and audit logging helpers.

### Step 3: Update `app.py`
- Implement `@admin_required` and `@roles_required(*roles)` decorators.
- Add user management routes (`/admin/user/create`, `/admin/user/update`, `/admin/user/toggle`, `/admin/user/delete`).
- Add inquiry status route (`/admin/inquiry/status`).
- Add buyer delete route (`/admin/buyer/delete`).
- Add print spec sheet route (`/car/<id>/print`), comparison route (`/compare`), and sitemap (`/sitemap.xml`).

### Step 4: Overhaul Admin Dashboard & Templates
- Overhaul `templates/admin.html` to adopt the new Glassmorphic Executive UI layout with Tabbed Navigation, Analytics Cards, CRM Pipeline Status Selectors, WhatsApp Quick Action Links, Buyer Directory Drawers, User Account Roles, and Security Audit Trail tables.
- Create `templates/compare.html`: Vehicle comparison grid.
- Create `templates/print_spec.html`: Window sticker print template.
- Update `templates/car.html`: Photo gallery tabs, EMI loan calculator widget, spec print link.
- Update `templates/cars.html`: Multi-filter bar (search, fuel, transmission).

---

## 7. ✅ Verification Plan

### Automated Verification
- Execute test script to verify DB initialization, table creation, password hashing, and user authentication.

### Manual Verification
- Test login with Super Admin, Manager, and Sales Rep accounts.
- Verify executive admin dashboard layout and responsive tabs.
- Test recording sales and verifying auto-created buyer purchase history profiles.
- Test public features: Live Search filter, EMI calculator math, Vehicle comparison grid, WhatsApp lead generator.
