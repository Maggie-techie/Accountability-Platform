# Nyeri Accountability Platform — Frontend

React + Vite frontend for the AI-Powered Nyeri Governance Accountability Platform.
All 19 screens from the design brief are implemented with mock data, ready to be
wired up to the real Flask API.

## Styling Updates

The frontend UI has been enhanced with:
- Crystal white background (#FFFFFF) replacing the previous off-white
- Bolder, more vibrant color palette with increased contrast
- Improved card styling with more visible borders and deeper shadows
- Enhanced text colors for better readability (pure black text)
- Refined forest greens, clay reds/browns, and gold accents

## Requirements

- Node.js 18+ (check with `node -v`)

## Setup

```
npm install
npm run dev
```

Then open the URL it prints (usually http://localhost:5173).

- Public site: http://localhost:5173/
- Admin panel: http://localhost:5173/admin/login (any email/password works — it's a demo login, not wired to real auth yet)

## Project structure

```
src/
  components/     Reusable UI pieces (buttons, cards, tables, charts, etc.)
  layouts/        PublicLayout (navbar+footer) and AdminLayout (sidebar)
  pages/          One file per public screen
  pages/admin/    One file per admin screen
  data/           mockData.js - stands in for the Flask API responses
  App.jsx         All routes
  main.jsx        Entry point
```

## Connecting to the real backend

Every page currently imports data from `src/data/mockData.js`. To connect to
your Flask API:

1. Add a `.env` file with `VITE_API_URL=http://localhost:5000`
2. Replace the imports from `mockData.js` in each page with `fetch(...)` calls
   to your Flask endpoints (e.g. `fetch(`${import.meta.env.VITE_API_URL}/constituency`)`)
3. The shape of the mock data objects in `mockData.js` is designed to match
   what your MongoDB collections look like, so the fields should line up
   closely with what your API already returns.

## Building for production

```
npm run build
```

Output goes to `dist/`. Serve that folder with any static host, or point
Flask at it.
