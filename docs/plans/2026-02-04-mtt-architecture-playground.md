# MTT Architecture Playground Design

## Goal

Interactive single-file HTML playground that visualizes the entire MTT Container Terminal Management System for junior developers. After 10 minutes of exploring, a junior should understand: how all pieces connect, what every endpoint does, and how data flows through the system.

## Views

### 1. Architecture (default)
5 horizontal layers: Frontend → API → Services → Models → DB. ~25 nodes with colored arrows between layers. Layer toggles to show/hide.

### 2. Container Lifecycle
Left-to-right animated flow: Gate Entry → Container Created → Position Assigned → Crane Op → On Terminal → Exit. Each step shows relevant endpoints, services, models.

### 3. Billing Cycle
Flow from Tariff Setup → Cost Calculation → fork into Monthly Statements vs On-Demand Invoices → Finalize → Pay → Export. Highlights the exclusion logic.

### 4. API Explorer
~65 endpoints grouped by app (auth, terminal, vehicles, billing, files, customer). Click group to expand, click endpoint for detail panel. Search box filters across all groups. Color by HTTP method.

## Interaction
- Click node → detail panel in sidebar (name, file path, purpose, code pattern)
- Layer toggles (architecture view)
- Search box (API explorer)
- Zoom +/- buttons
- Animated dashed arrows on flow views

## Technical
- Single HTML file, all CSS/JS inlined, no dependencies
- Dark theme, SVG canvas, ~2500-3000 lines
- State object drives all rendering
- No external API calls — all data hardcoded from codebase analysis
