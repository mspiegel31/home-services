# AVM & Market-Data Tools for Selling a Home (2026 state of play)

Research date: 2026-09-04. All API-availability claims were checked against the vendor's own
docs/portal pages where possible; claims resting on third-party scans are marked `[SECONDARY]`.

## Comparison table

| Tool | Valuation / market data | API posture (2026) | Pricing | What a dev can pull |
|---|---|---|---|---|
| **Zillow** (Zestimate) | Zestimate (AVM) ~100M properties; Rent Zestimate; market indices (ZHVI, ZORI); sale stats | Legacy self-serve public API (ZWSID keys) **retired Sept 30, 2021** `[SECONDARY]` (see Zillow section below). Today: gated **Zestimate API** via Zillow Group's Bridge Interactive data platform — "Request Access" flow, no public pricing, commercial/enterprise orientation. Free **Zillow Research CSVs** (market-level, no key) still exist | Zestimate API: custom/commercial (not published). Research CSVs: free | AVM value (property-level, gated), Rent Zestimate (gated); ZHVI/ZORI/sale-to-list/inventory/days-on-market CSVs (free, region-level only — **no property-level Zestimate in the free tier**) |
| **HouseCanary** | 122M+ AVMs, 105M+ rental valuations, 136M+ properties; monthly-updated AVMs + 36-month value forecasts; comps, land value, LTV, confidence scores | **Real REST API** (Property Analytics API, Market Pulse API, Property Estimate API, etc.), API-key auth; documented on vendor site | Subscription tiers; API calls usage-based on top. Basic ≈ $190/mo (no API), Pro ≈ $790/mo (incl. core API, usage-based calls), Teams ≈ $1,990/mo; per-call rates ≈ $0.30–$0.50 (basic endpoints), $2.50–$6 (premium), $7–$10 per AVM PDF report | AVM value + confidence + comps + forecasts (Pro+), market trends (Teams+), bulk data/Property Explorer/Value Check APIs (Enterprise only) |
| **ATTOM Data Solutions** | 160M+ properties; ATTOMIZED AVM (with `scr` confidence attribute), assessed values, sales history (10 yrs), sale trends, ownership, schools, area/POI data | **Real public REST API**, self-serve. Free API key at api.developer.attomdata.com; single `APIKey` header auth; JSON or XML; documented endpoint structure `https://api.gateway.attomdata.com/propertyapi/v1.0.0/...`; only 200 responses bill | Per-API-Report billing (1 report = 1 property returned, not per call). Free trial key (30-day), start-up plan, then custom/enterprise quotes. Support FAQ example: $1,000/mo plan ≈ 100,000 reports ≈ **$0.10/report**; overages billed at unit rate | AVM value + confidence (`/attomavm`), ZIP-level sale trends (`/salestrend`), last sale + 10-yr sales history (`/sale`, `/saleshistory`), assessments/tax, property detail — everything needed for a single-home pipeline |
| **RealVision** | — | **No such market-data vendor found.** Nearest matches: Realvision Inc. (real.vision, Toronto) = real-estate photography/3D-tour marketing, no data API `[SECONDARY]`; "Real Vision Media" (Quebec) = listing video capsules. No REST API, no AVM product | — | Nothing programmatically usable |
| **Offerpad** | (historically) iBuyer market analytics | **No public API.** Private transaction backend (helix.offerpad.com, Okta OAuth2) not accessible to third parties; no developer portal; `/api`, `/docs`, OpenAPI all 404 `[SECONDARY]` (API Evangelist systematic scan) | — | Nothing. Third-party Offerpad scrapers exist but carry ToS/data-rights risk |
| **Redfin** | Market-level stats (their Data Center); per-property data shown only on-site | **No public/developer API** `[SECONDARY]` (multiple 2026 sources agree; no developer portal or key flow exists). Sanctioned surface: **Redfin Data Center** — free downloadable aggregate market CSVs (weekly/monthly/quarterly updates). ToU (Sept 2025) disallows automated scraping `[SECONDARY]` | Data Center CSVs: free | Market trends only (price indices, inventory, etc.) at metro/ZIP level; **no property-level AVM API, no rent comps API** |
| **RealEstateAPI.com** (not in original list — relevant) | Lender-Grade AVM API (`POST /v2/PropertyAvm`), `estimatedValue` on property search/detail, comps (`v3/PropertyComps`), county assessed values | **Real documented REST API**, API-key auth, OpenAPI-style docs on developer.realestateapi.com | Subscription tiers (not fetched — verify at realestateapi.com) | AVM value, comps, property attributes, tax/assessed data |
| **New 2025–2026 entrants** (vendor pages, not fetched line-by-line — treat depth claims as `[VENDOR-PAGE]`) | | | | |
| **Tortus** (tortus.io/developers) | AVM valuations with estimated value, confidence interval, and comparables; 85M+ properties, 35+ states | REST, single `x-api-key` (scoped), `sk_live_*`/`sk_test_*` keys, sandbox; MCP-compatible for AI agents | Usage-based, "announced soon" (early-access stage as of listing) | `POST /api/v1/avm/estimate` (value + CI + comps), property/transaction search, risk signals |
| **PropX402** (propx402.xyz) | Property report: value estimate (low/high), rent estimate, flood risk, walk score, demographics, risk score; aggregates 14 sources | x402 pay-per-query protocol (0.05 USDC on Base) — **no keys/accounts**, JSON <8s | 0.05 USDC/query; 0.25 USDC for the fat `/property-full` endpoint | Single normalized JSON report per query; fully scriptable (HTTP + payment) |
| **HomeAnalytics** (homeanalytics.ai) | AVM valuation, property details, mortgage data, comps, market trends (unified US property data) | REST API per vendor page | Not fetched — vendor quote | AVM + comps + trends in one API |
| **RentCast** (rentcast.io/api) | AVM + rent estimates, 150M+ properties, market trends, listing stats | REST API per vendor page | Not fetched | Property value, rent comps, market trends |
| **Stream.Estate** (stream.estate) | 50M+ listings deduped from 1,500+ sources; AVMs, valuations, market insights | REST API per vendor page | Not fetched | Listings, valuations, market data |

## Zillow — what is actually available to developers in 2026

Verified against primary sources (all zillowgroup.com / zillow.com):

1. **The old public Web Services API is gone.** The ZWSID-keyed public endpoints
   (`GetZestimate`, `GetDeepSearchResults`, `GetComps`, `GetSearchResults`, etc.) were
   deprecated and shut down **September 30, 2021** `[SECONDARY]`
   (api-evangelist/zillow apis.yml: https://github.com/api-evangelist/zillow/blob/main/apis.yml;
   supergood.ai: https://supergood.ai/api-report-card/zillow). Corroborated by multiple 2025–2026 sources.
2. **What exists now** (https://www.zillowgroup.com/developers/api/zestimate/zestimates-api/,
   page last updated 2025-05-05): a Zestimate API described as "for commercial use cases by
   businesses," serving Property/Rental/Foreclosure Zestimates for ~100M US properties. Access is
   via a **"Request Access" (help-button) flow — not self-serve**. Per that page's own spec table:
   - Documentation: https://bridgedataoutput.com/docs/platform/#zestimates (Zillow's Bridge Interactive platform)
   - Auth: **password + access token**; RESTful; URI query string; JSON; agreement: TOS.
   - No pricing is published; effective model is a commercial/enterprise license (in practice
     MLS-affiliated/IDX/partner channels — `[SECONDARY]` Zillapi/APIllow 2026 writeups).
   - The same portal lists ~20 gated APIs (MLS listings, mortgage rates, public records,
     neighborhood data, rentals feeds) — all partner-oriented.
3. **The free developer path is market-level data, not property-level Zestimates.**
   https://www.zillow.com/research/data/ (updated 2026-07-10) publishes free CSV downloads with
   "looser Terms of Use for storing and manipulating" the data:
   - **ZHVI / ZHVF** (home value index + month/quarter/year forecasts), top- and bottom-tier cuts
   - **ZORI / ZORDI / ZORF** (observed rent index, renter demand, rent forecasts)
   - Sale metrics: sales count (nowcast), median/mean sale price, total transaction value,
     sale-to-list ratio, % above/below list
   - Listing metrics: for-sale inventory, new listings, median list price, days-to-pending,
     days-to-close, price cuts
   - Affordability metrics, market heat index, new-construction stats
   - Cadence: monthly data updates the 16th, most weekly data updates Tuesdays; **CSV URLs are
     stable and scriptable** (page warns paths change occasionally). Region-level (national/MSA/
     metro/county/ZIP), **not property-level**. This is the only free Zillow data a script can
     legitimately pull.
4. **Zestimate/Zillow API Terms of Use** (https://www.zillowgroup.com/developers/terms/,
   page last modified 2024-04-04; copyright line 2006–2014 — note it is an old-dated document that
   still governs the current API):
   - License is personal, tied to a unique **ZWSID** (or, in the current Bridge world, a
     per-credential account); affiliates need their own license.
   - **1,000 calls/day** cap on Home Valuations API and Property Details API (higher limits only
     after audit/review).
   - Data must be shown **transactionally only — no bulk access**, no user bulk export.
   - **No retention of copies**; direct server-to-server pass-through to your end users only.
   - Cannot be the primary functionality of a mobile app; no direct-marketing use; address
     information may not be separated from the Zestimate; max 20 properties displayed per page
     (Property Details API).
   - "As-is, with all faults," full liability disclaimer, sole-remedy = discontinue use;
     WA state law / King County venue; Zillow may terminate any time.
   - Bottom line for a single home sale: even if you got this API, **you may not store the
     Zestimate**, may not build a tool whose main function is Zillow data, and you'd get ~3
     property-level calls before hitting the daily cap. It is not a fit for a home-seller's
     automation pipeline; the free Research CSVs + a third-party AVM is.

## HouseCanary — API pricing (checked directly on housecanary.com/pricing)

- Plans (monthly; annual-billed equivalents listed on the same page): **Basic** (1 user, 2 custom
  valuation reports/mo, **no Property Analytics API**, no portfolio monitoring), **Pro** (1 user,
  15 custom valuation + 15 AVM PDF reports, 25 monitored properties, **core API with
  usage-based costs**, full CanaryAI), **Teams** (10 users, 40+40 reports, 50 monitored, adds
  Market Pulse API, Property Estimate API, Interactive Value Check), **Enterprise** (custom; adds
  Bulk Property Data, Nationwide Bulk Price/Rental Forecasts, Property Explorer API, Value Check
  API, SSO).
- API call rates visible in the plan comparison (per successful call, scale by plan):
  Property Analytics API basic endpoints ≈ $0.30–$0.50; premium ≈ $2.50–$4; premium-plus ≈ $6;
  AVM PDF reports ≈ $7–$10; custom valuation reports ≈ $9–$12; extra seat ≈ $10/user/mo.
- A separate **agent plan exists from ~$19/mo** (housecanary.com/pricing/real-estate-agents) but
  it is report-focused (2 custom valuations/mo) and does not include the core API.
- Product depth (housecanary.com/products/data-explorer): monthly-updated AVMs with value
  forecasts up to 36 months out, HPI-adjusted values, block→state time series, land value, LTV,
  confidence metrics, comp/neighborhood context, environmental/weather risk indicators.
- Verdict: the strongest documented AVM API in the list, but the entry price for API access
  (Pro tier, ~$790/mo + usage) is enterprise-shaped — expensive for a single home.

## ATTOM — API posture (checked directly on api.developer.attomdata.com)

- **Self-serve developer platform**: free trial API key at /signup (30-day trial per support
  FAQ), documented at /docs with interactive docs.
- Auth: single **`APIKey` header** + `Accept: application/json|application/xml`. All endpoints
  require the key; only HTTP-200 responses count against monthly allowances.
- Endpoint shape: `https://api.gateway.attomdata.com/propertyapi/v1.0.0/{Resource}/{Package}?{params}`
  (e.g. `.../property/detail?id=1234`); paged results, default max 1,000 reports/call.
- Property API resources (160M+ properties): `/property` (detail incl. mortgage/owner/school
  packages), `/attomavm` (**AVM value with `scr` = confidence score**; works even when
  property attributes are missing, at the cost of lower confidence), `/salestrend` (2 years of
  ZIP-level avg/median sale price + counts, monthly/quarterly/yearly), `/sale` (last sale),
  `/saleshistory` (10 years, single property), `/allevents` (assessments+AVM+sales combined),
  `/assessment`, `/school`.
- Billing model (support.attomdata.com FAQ, fetched via search — page was 404 on direct fetch, so
  treat numbers as `[SECONDARY-of-primary]`): **per API Report** (each property in a response = 1
  report, not per call); overages billed at the contracted unit rate. Documented example: a
  $1,000/mo plan ≈ 100,000 reports ≈ **$0.10/report**. Free key for development; "start-up plan"
  for early usage; enterprise via sales (800-462-5125).
- Verdict: best cost-to-scriptability ratio for property-level AVM + comps + market trends in one
  REST surface. A single home (AVM + sale trend + sales history + assessment ≈ 4–5 reports)
  costs on the order of pennies-to-dollars per month even on the smallest paid plan.

## Cheapest scriptable valuation pipeline for a single home

All data you actually need for "is my house worth X and what's my market doing" comes from three
scriptable sources; total cash cost ≈ **$0/mo (free tier + trials) to ~$10/mo (ATTOM start-up)**:

1. **Free market context (no key, no auth):** monthly cron that downloads the stable CSV URLs from
   https://www.zillow.com/research/data/ for your metro/county/ZIP — ZHVI (value index + trend),
   ZHVF (value forecasts), ZORI (rent index — your "what would it rent for" number), sale-to-list
   ratio, median list price, days-to-pending, price-cut share, inventory. Redfin Data Center
   CSVs (https://www.redfin.com/news/data-center/) give a second independent market-trend source
   for the same $0.
2. **Free property-level valuation (trial/free):** county assessor data — most US counties
   publish assessed value + parcel records (often CSV/GeoJSON or an assessor API, e.g. via
   open-data portals); ATTOM's free trial key gives the same shape plus their AVM.
3. **Property-level AVM + comps (pay-as-you-go):** ATTOM with a trial/start-up key —
   `GET .../propertyapi/v1.0.0/attomavm/...` (AVM + confidence), `/salestrend` (your ZIP's 2-yr
   sale trend), `/saleshistory` (your own home's 10-yr sales), `/assessment`. ≈$0.10/report makes
   a full single-home report a few cents. If you want a second opinion AVM without a subscription,
   HouseCanary's one-off reports or the early-access entrants (Tortus usage-based, or PropX402 at
   0.05 USDC/query if you're comfortable paying on-chain) are the fallbacks.

Pipeline sketch (the actual shape):

```
cron (monthly, 17th)
├─ zillow_research.py  → download ZHVI/ZORI/sale CSVs for your metro+ZIP → SQLite
├─ redfin_datacenter.py → download matching metro CSV → SQLite (cross-check)
├─ attom_pipeline.py   → /attomavm, /salestrend, /saleshistory, /assessment → SQLite
└─ report.py           → render: AVM ± confidence, my sale history, ZIP trend vs ZHVI,
                        rent comp (ZORI vs RentCast if you want a second rent number)
```

Why not the alternatives: Zillow's Zestimate API is gated, unpriced, and its ToU forbids
retaining data — pointless for one property. HouseCanary's API is excellent but ~$790/mo entry —
overkill by ~50×. Redfin/Offerpad have no property-level API at all. Scraper wrappers of
Zillow/Redfin violate ToU and break constantly.

## Caveats & data recency

- Zillow API ToU document is dated 2006–2014 (page last modified 2024-04-04) — the rate limit
  and usage restrictions are from that vintage; the current Bridge-platform agreement may differ
  in details. The 2021 shutdown date and "no public Zestimate API" status are `[SECONDARY]`
  (2025–2026 sources agreeing; Zillow's own portal corroborates by simply not offering a
  self-serve Zestimate signup).
- HouseCanary pricing figures are from the live plan-comparison page at fetch time (Sept 2026);
  annual-billing numbers and per-call rates are as displayed and can change.
- New-entrant rows (Tortus, PropX402, HomeAnalytics, RentCast, Stream.Estate) are from vendor
  marketing/developer pages seen via search (not fetched line-by-line) — verify pricing and
  coverage before committing; several are pre-pricing/early-access.
- ATTOM support-FAQ billing numbers were retrieved via search-index snapshot (direct URL 404'd at
  fetch time); the primary developer portal confirms the free-key/trial/start-up/enterprise
  structure directly.
