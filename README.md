# Thueman Coke Limited — Technology Platform

Production starter for **https://thuemancokelimited.com**

## Architecture

- Frontend: React + Vite, published with GitHub Pages
- Backend: FastAPI on Railway
- Database: PostgreSQL on Railway
- DNS / domain: HostGator remains authoritative
- Production frontend: `https://thuemancokelimited.com`
- Production API: `https://api.thuemancokelimited.com`

## Repository layout

```text
thuemancoke-technology-platform/
├─ .github/workflows/deploy-pages.yml
├─ backend/
│  ├─ app/
│  │  ├─ __init__.py
│  │  ├─ db.py
│  │  ├─ main.py
│  │  ├─ models.py
│  │  ├─ schemas.py
│  │  └─ settings.py
│  ├─ .env.example
│  ├─ Dockerfile
│  ├─ railway.json
│  └─ requirements.txt
├─ frontend/
│  ├─ public/
│  │  ├─ images/thueman-coke-logo.png
│  │  ├─ CNAME
│  │  ├─ favicon.svg
│  │  ├─ robots.txt
│  │  └─ sitemap.xml
│  ├─ src/
│  │  ├─ App.jsx
│  │  ├─ data.js
│  │  ├─ main.jsx
│  │  └─ styles.css
│  ├─ .env.example
│  ├─ index.html
│  ├─ package.json
│  └─ vite.config.js
├─ scripts/
│  ├─ dev.ps1
│  ├─ dev.sh
│  └─ smoke-test.ps1
└─ .gitignore
```

## Local development

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000
```

Health: http://localhost:8000/api/health
Docs: http://localhost:8000/docs

### Frontend

Open a second terminal:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open http://localhost:5173

## GitHub

Create a repository called `thuemancoke-technology-platform`.

```powershell
git init
git add .
git commit -m "Initial Thueman Coke Limited technology platform"
git branch -M main
git remote add origin https://github.com/YOUR-GITHUB-USERNAME/thuemancoke-technology-platform.git
git push -u origin main
```

Then:

1. GitHub repository → Settings → Pages.
2. Build and deployment → GitHub Actions.
3. Custom domain → `thuemancokelimited.com`.
4. Settings → Secrets and variables → Actions → Variables.
5. Add `VITE_API_URL` = `https://api.thuemancokelimited.com`.

## Railway

1. Create New Project → Deploy from GitHub repo.
2. Select this repository.
3. Set the API service Root Directory to `/backend`.
4. Add a PostgreSQL service.
5. In the API service, add:
   - `APP_ENV=production`
   - `DATABASE_URL=${{Postgres.DATABASE_URL}}`
   - `ALLOWED_ORIGINS=https://thuemancokelimited.com,https://www.thuemancokelimited.com`
6. Optional email variables:
   - `CONTACT_TO_EMAIL`
   - `FROM_EMAIL`
   - `SMTP_HOST`
   - `SMTP_PORT`
   - `SMTP_USERNAME`
   - `SMTP_PASSWORD`
   - `SMTP_USE_SSL`
7. Generate a Railway domain and test `/api/health`.
8. Add custom domain `api.thuemancokelimited.com`.
9. Railway will show a CNAME target. Use that exact value in HostGator DNS.

## HostGator DNS

Keep HostGator nameservers and email MX records.

Apex website records:

```text
A  @  185.199.108.153
A  @  185.199.109.153
A  @  185.199.110.153
A  @  185.199.111.153
```

WWW:

```text
CNAME  www  YOUR-GITHUB-USERNAME.github.io
```

API:

```text
CNAME  api  <EXACT RAILWAY CNAME TARGET>
```

Do not change MX, SPF, DKIM or DMARC simply to move the website.

## Verify from Windows

```powershell
Resolve-DnsName thuemancokelimited.com -Type A
Resolve-DnsName www.thuemancokelimited.com -Type CNAME
Resolve-DnsName api.thuemancokelimited.com -Type CNAME

curl.exe https://api.thuemancokelimited.com/api/health
curl.exe -I https://thuemancokelimited.com
```

## Recommended go-live order

1. Test locally.
2. Push to GitHub.
3. Deploy Railway backend.
4. Add Railway PostgreSQL.
5. Configure `api.thuemancokelimited.com`.
6. Confirm API HTTPS.
7. Enable GitHub Pages.
8. Configure GitHub custom domain.
9. Change apex/www DNS at HostGator.
10. Enable GitHub Enforce HTTPS after certificate provisioning.
11. Test site, form, mobile, DNS and email.
12. Keep the old HostGator website backup until the new site is confirmed stable.
