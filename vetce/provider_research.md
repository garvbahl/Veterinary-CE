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

## Tufts Cummings School CE

- URL: https://vet.tufts.edu/events?trumbaEmbed=filterview%3DDepArea-ContEd (events calendar)
- URL: https://vet.tufts.edu/continuing-education-programs (programs hub - pending check)
- Shape: A — events embedded via Trumba (3rd party)
- Events calendar: JS-rendered, skip for now
- Has real dates, multi-day events, mix of free/paid — high-value target
- Decision: SKIP for now. Revisit in Phase 4+ via Playwright OR Trumba RSS feed
  (try https://www.trumba.com/calendars/tufts-vet.rss or similar)

  ## Cornell Sim Lab (cornellsimlab.org)

- URL: https://www.cornellsimlab.org/courses-vets
- URL: https://www.cornellsimlab.org/courses-techs
- URL: https://www.cornellsimlab.org/upcoming
- Linked from: vet.cornell.edu CE page (separate property)
- Shape: A — needs static/JS check
- Decision: Phase 3.5+ candidate. Different stack from main Cornell page.
  Likely another university-hosted catalog. Worth a 10-min recon later.
