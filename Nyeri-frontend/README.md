# Nyeri Accountability Platform — Frontend

React + Vite frontend for the AI-Powered Nyeri Governance Accountability Platform.
All screens are now wired to the real Flask API (no mock data).

## Styling Updates

The frontend UI has been enhanced with:
- Crystal white background (#FFFFFF) replacing the previous off-white
- Bolder, more vibrant color palette with increased contrast
- Improved card styling with more visible borders and deeper shadows
- Enhanced text colors for better readability (pure black text)
- Refined forest greens, clay reds/browns, and gold accents
- Pitch dark header and footer backgrounds for all pages
- Changed font to Inter with improved letter spacing and line height for better readability

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
  services/       API service layer (src/services/api.js)
  hooks/          Custom React hooks (useAsyncData, etc.)
  App.jsx         All routes
  main.jsx        Entry point
```

## API Integration

All pages now fetch data from the Flask API via `src/services/api.js`:
- Constituencies, allocations, audit findings, and scores
- Governor profile, county finances, departments
- AI-powered anomalies (MP AI, GNN, Governor risk analysis)
- PDF report generation

Configure the API base URL via `.env`:
```
VITE_API_BASE_URL=http://localhost:5000/api
```

## Building for production

```
npm run build
```

Output goes to `dist/`. Serve that folder with any static host, or point
Flask at it.
