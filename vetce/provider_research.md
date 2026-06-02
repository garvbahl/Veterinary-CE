## Radimal

URL: https://radimal.ai/pages/webinar-mastering-small-animal-pulmonary-radiographs
Requires sign in so does not work

## VetAndTech (vetandtech.com)

- URL: https://vetandtech.com/webinars
- Shape: A (catalog) — possibly JavaScript-rendered (needs verification)
- Recommended by: [vet expert] — strong filtering UI (date, subject)
- Source: Phase 3+ target. Likely needs Playwright if JS-rendered.
- Decision: Add to scraping queue AFTER first 2-3 lightweight scrapers in place.
- Note: Strong sign that filter-by-date / filter-by-subject are real user needs —
  validates current schema design (starts_at, subject_category, topics columns).

## AAHA (pathlms.com/aaha)

- URL: https://www.pathlms.com/aaha/courses
- Shape: A (catalog) — JS-rendered via Elasticsearch + InstantSearch
- Hosted on PathLMS (3rd-party LMS, also hosts other orgs' CE)
- Catalog size: 57 courses in "AAHA Guidelines Certificates" alone, more total
- Has paid + free, ratings, pagination
- Decision: SKIP for first base-class iteration. Revisit in Phase 4+ via:
  (a) Playwright, OR
  (b) directly calling their Elasticsearch endpoint (preferred — faster, cleaner)
- The ES URL and public API key are visible in page source.

## NAVTA (ce.navta.net)

- URL: https://ce.navta.net/
- Shape: A (catalog) — static HTML with embedded JSON in `var courseData`
- 13 courses in the JSON (UI groups them as 2 program cards)
- Detail pages: login-walled, but all metadata is on listings page already
- Different extraction: parse JS variable + nested JSON, not CSS selectors
- Audience: technicians only (vs VetMedTeam's mixed audience)
- Has sponsor field (Zoetis, Merck) — possible new schema column later
- Has multi-module programs (OA, Itchy Dog) — listings are individual modules
- Decision: GOOD second-scraper candidate. Differs meaningfully from VetMedTeam.
