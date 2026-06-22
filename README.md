# PCI SERVER Setup Guide

<!-- ## Prerequisites

- Node.js (18+)
- Postgresql Database
- Prisma ORM
- Google cloud console account (for OAUTH)
- Nodemailer user and password

## Installation Steps

### 1. Initialize Project

```bash
npm install
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env`
and fill in your values:

```bash
cp .env.example .env
```

### 3. Setup Prisma

```bash
# Generate Prisma Client
npx prisma generate

# Run migrations (create tables and relationships)
npx prisma migrate dev --name < name of migration >

# (Optional) Open Prisma Studio
npx prisma studio
```

**Important:**
After Pulling new changes that includes schema updates, always run:

```bash
npx prisma generate #
npx prisma migrate dev --name < name of migration > #
Apply database migrations
```

### 4. Setup Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URIs: `http://localhost:8000/api/auth/google/callback`
6. Copy Client ID and Client Secret to `.env`

### 5. Start Development Server

```bash
npm run dev
```
