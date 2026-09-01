# 🏖️ JustRelax ERP - Luxury Travel & Hospitality Management Platform

![Python](https://img.shields.io/badge/Python-3.11-blue.svg)
![Django](https://img.shields.io/badge/Django-5.0-emerald.svg)
![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-38bdf8.svg)
![License](https://img.shields.io/badge/License-MIT-amber.svg)

**JustRelax** is a full-featured, enterprise-grade Travel ERP, Hospitality Booking Engine, and B2B Agent Management Platform built with **Django** and modern glassmorphism web technology. Inspired by MakeMyTrip, it empowers travel agencies, hotel suppliers, agents, and retail customers with seamless booking workflows, dynamic pricing markups, rich gallery management, and automated booking receipts.

---

## ✨ Key Features

### 🛒 1. MakeMyTrip-Style B2C Storefront
- **Dynamic Hero Search Widget**: Instant tab switching between Flights, Hotels, and Holiday Packages with background video playback.
- **Flight Booking Engine**: One-way and Round-trip flight search with seat selection, baggage options, and instant fare breakdown.
- **Hotel Booking & Room Inventory**: Search top-rated luxury hotels, view interactive photo galleries, filter by star rating & amenities, and select room categories.
- **Holiday Packages**: Curated tour packages with day-wise itineraries, daily breakfast, airport transfers, and highlight tags.

### 🏢 2. B2B Agent Portal (`/agent/`)
- **Agent Dashboard**: Real-time sales metrics, recent bookings, wallet balance, and commission earnings.
- **Custom Markup Engine**: Agents can set custom percentage markups for hotels and holiday packages.
- **Agent Wallet**: Instant wallet top-ups, transaction ledger, and automated booking deductions.
- **PDF & E-Tickets**: Generate co-branded customer vouchers with agent logo and agency contact info.

### 👑 3. SuperAdmin ERP Portal (`/admin-panel/`)
- **Inventory Management**: Full CRUD for Master Hotels, Room Categories, Holiday Packages, and Flights.
- **Interactive Gallery Folder Manager**: Manage hotel and package photo galleries with live drag-and-drop preview, cover image assignment, and instant delete triggers.
- **User & Agent Management**: Manage customer accounts, approve B2B agent applications, adjust credit limits, and view user audit history.
- **Financial Ledger & Analytics**: System-wide revenue metrics, agent commissions, and booking status controls.

### ⚡ 4. High Performance & Optimized Media Engine
- **Media Compression**: Automated FFmpeg video compression (H.264/VP9) reducing hero videos by over **86%**.
- **Aggressive Browser Caching**: Custom `MediaCacheMiddleware` providing 1-year HTTP caching and byte-range video streaming.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.11, Django 5.0 framework
- **Database**: SQLite (Development) / PostgreSQL (Production ready)
- **Frontend**: HTML5, Vanilla JavaScript (ES6+), Tailwind CSS, Phosphor Icons
- **Media & Processing**: Pillow (PIL), FFmpeg (`imageio-ffmpeg`)
- **Authentication**: Custom Django User model (`CustomUser`) with Role-Based Access Control (Customer, B2B Agent, Staff Admin, SuperAdmin)

---

## 📁 Repository Structure

```
justrelax/
├── apps/
│   ├── accounts/          # Authentication, User Profiles & Storefront Home
│   ├── agents/            # B2B Agent Portal & Wallet Management
│   ├── bookings/          # Flight/Hotel/Package Booking Engine & Receipts
│   ├── dashboard_admin/   # Admin ERP Portal & Inventory Management
│   ├── flights/           # Flight Search & Airline Inventory
│   ├── hotels/            # Hotel Properties & Room Categories
│   ├── packages/          # Holiday Packages & Itinerary Builder
│   ├── promotions/        # Coupons, Offers & Customer Reviews
│   └── wallet/            # Financial Ledger & Agent Transactions
├── core/
│   ├── middleware.py      # Browser Caching & Byte Range Middleware
│   ├── settings.py        # Django Configuration
│   └── urls.py            # Main URL Routing
├── media/                 # Compressed Media Storage (Hotels, Packages, Hero Videos)
├── templates/             # HTML Templates (Storefront, Admin, Agent)
├── manage.py
├── requirements.txt
└── README.md
```

---

## 🚀 Quickstart & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/rathod-vaibhav/justrelax.git
cd justrelax
```

### 2. Set Up Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Apply Database Migrations
```bash
python manage.py migrate
```

### 5. Create Superuser (Admin Account)
```bash
python manage.py createsuperuser
```

### 6. Run Local Development Server
```bash
python manage.py runserver
```

Open your browser and navigate to:
- **B2C Storefront**: `http://127.0.0.1:8000/`
- **Admin ERP Portal**: `http://127.0.0.1:8000/admin-panel/`
- **B2B Agent Portal**: `http://127.0.0.1:8000/agent/`

---

## 📄 License
Distributed under the **MIT License**. See `LICENSE` for more details.
