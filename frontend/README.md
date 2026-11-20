# Xaiote — Frontend Web Console

[![Next.js 15.2](https://img.shields.io/badge/next.js-15.2.0-black.svg)](https://nextjs.org/)
[![React 19](https://img.shields.io/badge/react-19.2.8-blue.svg)](https://react.dev/)
[![Tailwind CSS 4](https://img.shields.io/badge/tailwindcss-v4-06B6D4.svg)](https://tailwindcss.com/)
[![AWS Amplify](https://img.shields.io/badge/aws-amplify-FF9900.svg)](https://aws.amazon.com/amplify/)

The Xaiote web console is an enterprise Next.js 15 (App Router) application providing factory operators and plant leadership with real-time operational visibility, incident investigation workflows, work order risk forecasting, and master data management.

Hosted on **AWS Amplify Hosting** in Mumbai (`ap-south-1`) at [https://xaiote.com](https://xaiote.com), communicating securely with the backend API at `https://api.xaiote.com`.

---

## 1. Frontend Architecture & Features

- **Route Groups:**
  - `(auth)`: Login and multi-tenant registration.
  - `(marketing)`: Public product marketing pages, pilot onboarding modal.
  - `(dashboard)`: Authenticated console shell (Overview, Command Center, Manufacturing Events, Incidents, Work Orders, Risk, Machines, Plants, Customers, Vendors, Imports, Settings).
- **Edge Route Protection (`src/middleware.ts`):** Validates the lightweight `xaiote_auth=1` cookie signal to redirect unauthenticated requests before rendering dashboard components.
- **Resilient API Client (`src/lib/api.ts` & `src/lib/auth.ts`):** Centralized `fetchApi` wrapper attaching Bearer tokens, automatically refreshing expired tokens on HTTP 401 via `/api/auth/refresh`, and retrying requests seamlessly.
- **Production Assertion:** Enforces a build-time and runtime check preventing `NEXT_PUBLIC_API_URL` from pointing to `localhost` in production.
- **Industrial Dark-Mode UI:** Built with Tailwind CSS v4, Lucide React icons, and TanStack React Query caching.

---

## 2. Directory Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── (auth)/              # /login, /register
│   │   ├── (marketing)/         # Landing page, features, pricing, pilot
│   │   ├── (dashboard)/         # Protected operator/executive console
│   │   ├── layout.tsx           # Root HTML layout and global styles
│   │   └── globals.css          # Tailwind CSS v4 imports
│   ├── components/
│   │   ├── layout/              # Sidebar, Header, Breadcrumbs
│   │   ├── marketing/           # Landing page interactive sections
│   │   ├── providers/           # AuthProvider, ReactQueryProvider
│   │   ├── timeline/            # Operational & Evidence timelines
│   │   └── ui/                  # UncertaintyBadge, ObservabilityPanel
│   └── lib/
│       ├── api.ts               # Core fetch client & base URL resolver
│       └── auth.ts              # Token storage, login, refresh handlers
├── public/                      # Static branding assets and icons
├── amplify.yml                  # AWS Amplify Hosting CI/CD configuration
├── Dockerfile                   # Node 20-alpine container
└── package.json                 # Dependencies (Next.js 15.2, React 19.2)
```

---

## 3. Local Development Quick Start

### 1. Prerequisites
- Node.js 20.x LTS
- npm 10.x+

### 2. Install Dependencies
```powershell
cd c:\Xaiote\frontend
npm ci
```

### 3. Environment Configuration
```powershell
Copy-Item .env.local.example .env.local
```
Set `NEXT_PUBLIC_API_URL` for local development:
```ini
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### 4. Start Development Server
```powershell
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 4. Quality Checks & Production Build

```powershell
# Run ESLint validation
npm run lint

# Run Next.js production type-check and build
npm run build
```

For complete technical documentation, refer to the root [README.md](../README.md) and [docs/](../docs/).
