# CRAM Presentation UI

This presentation layer is a visual enhancement only. It does not change the approved CRAM roadmap, module sequence, API contracts, permissions, data-governance lifecycle, or scientific-methodology gates.

## Visual direction

- Primary palette: light green, white and light blue.
- Application shell: persistent module navigation, FCC context header, environment status and user profile access.
- Presentation hierarchy: executive landing view, consistent page headings, cards, tables, status pills, forms and responsive layouts.
- Climate modules: dedicated visual navigation for Heat, Flood, Trees and Vulnerability while preserving the existing route and API structure.
- Governance: Data Catalogue, Approvals and Audit remain clearly visible as first-class CRAM capabilities.
- GIS: map workspace styling preserves maximum map area while aligning the controls with the shared design language.
- Accessibility: high-contrast primary text, visible focus states, semantic HTML structure and responsive mobile navigation.

## Color tokens

The UI uses CSS design tokens in `apps/web/src/index.css`. The principal colors are `--green`, `--blue`, `--green-soft`, `--blue-soft`, white surfaces, and low-contrast blue/green borders. No dark-mode override is used for presentation consistency.
