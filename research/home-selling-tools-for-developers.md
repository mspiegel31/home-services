# Home-selling tools for software developers

**Scope.** Survey of the US home-selling tool landscape (2026) through the lens of an experienced developer running a self-hosted homelab: what exists in each category (pricing/AVM, FSBO listing, marketing/media, transaction/e-sign, inquiry/CRM), what has a real API, what is self-hostable, what it costs, and — critically — whether the DIY economics even make sense post-NAR-settlement. Researched 2026-09-04 from primary sources (court documents, NAR policy, MLS rulebooks, vendor pricing/API docs, state regulations). Detailed slice reports live alongside this file; citations there.

## TL;DR

| Pick | Tool | Why |
|---|---|---|
| The single most important fact | **FSBO expected value is negative on a median home** | Post-settlement commission savings (2.5–3%, ~$11k on $425k) are dwarfed by the observed median FSBO price discount (~18%, ~$64k, NAR 2025). DIY only wins on high-demand/distinctive properties — exactly where the automation stack pays off |
| Highest-leverage single purchase | **Flat-fee MLS broker, $299–$1,500** | The only route to buyer-agent/IDX/Realtor.com exposure; MLSs cannot fix commission rates, so a $0-comp listing is legal |
| Pricing/valuation (scriptable) | **Zillow Research CSVs (free) + county assessor + ATTOM trial/start-up key** | Zillow's public API died 2021; Zestimate is now a gated, unpriced, no-retention commercial API. ATTOM gives property-level AVM+comps+10yr history at ~$0.10/report. Full pipeline sketch in the AVM slice |
| Listing | **ZFSBO free + flat-fee MLS filing** | ZFSBO is unlimited photos/video, explicitly exempt from Zillow's MLS-first rules; no FSBO platform offers any API/export — all dashboard-only |
| E-sign (self-host) | **Documenso** (AGPL, 14.9k★, real API+webhooks+SDKs) | The one category where production-grade OSS exists. Hosted fallback: SignWell (25 API docs/mo free, $0.85 after) — DocuSign's API floor is $50/mo, absurd for one sale |
| 3D tour | **Pannellum (self-host) or Kuula free tier** | Production-grade 360 viewer on the homelab, ~1 day; Matterport ($99+/yr) only if floor plans/measurements are a market norm in your area |
| Listing copy | **Local LLM (vLLM/llama.cpp) + county-assessor structured data** | The highest-leverage build in the whole survey; no paid tool ($19–150/mo) has an API or real secret sauce |
| Open-house/inquiry capture | **Formbricks (AGPL, free core: full API + webhooks)** or a 50-line FastAPI form | Every SaaS hides inquiry data by design (it's their monetization); a self-hosted endpoint you own beats all of them for one sale |
| Legal posture | **Reactive automation only** | Owner exemption covers selling your own home; FCC 24-17 makes AI voice/cold text outreach a prior-express-consent liability class; scraping Zillow/Realtor/MLS is a ToS breach everywhere |

## The economics question first (why it's not just a tooling survey)

Post-*Burnett v. NAR* settlement (executed 3/15/2024, Final Judgment 1/15/2025): no compensation fields on the MLS; buyer-broker comp set off-MLS via written buyer-agreement; total avg commission actually *rose* to 5.70% (Clever, 8/20/2026) because norms are sticky. NAR's own 2025 data: median FSBO sale price $360k vs $425k agent-assisted, 91% of sellers used agents, FSBO at an all-time-low 5%.

Itemized ($425k reference home, seller side): agent route ≈ **$23–30.6k** all-in; DIY route (flat-fee MLS + 2% buyer comp + ~$2.5–6k out-of-pocket) ≈ **$12–19.5k** — *before* the price effect, i.e. gross savings of ~$11–18k, which the 18% median FSBO discount (−$64k) swallows entirely. Details + every source: `home-selling-5-economics-rules.md`.

**Decision rule:** run the full DIY stack if your home is in a high-demand market / is distinctive / has a likely cash-buyer pool (price effect won't materialize, time-on-market stays short). Otherwise the flat-fee MLS broker is still the right purchase — the tooling below still helps you price, market, and run the transaction at near-zero marginal cost.

## Category 1: Pricing & market data (AVM)

| Tool | Scriptable surface | Cost | Verdict |
|---|---|---|---|
| **Zillow** | Public API (incl. `GetZestimate`) **dead since 9/30/2021**; current Zestimate API = gated Bridge platform, no public pricing, ToU bans data retention/bulk use. Free **Research CSVs** (ZHVI/ZORI/sale-to-list/inventory) — region-level, stable URLs, explicitly scriptable | Free (CSVs) | CSVs on a monthly cron = market context at $0 |
| **ATTOM** | Self-serve REST API, free trial key, one `APIKey` header: `/attomavm` (AVM + confidence), `/salestrend` (ZIP, 2yr), `/saleshistory` (10yr), `/assessment` | Per-report billing; documented ~$0.10/report | **Best cost-to-scriptability ratio** for property-level AVM |
| **HouseCanary** | The most complete documented AVM API (Property Analytics/Market Pulse/Estimate) | Pro tier ~$790/mo for API entry + per-call $0.30–10 | Enterprise-shaped; ~50× overkill for one home |
| **Redfin / Offerpad** | No property-level API (Redfin Data Center = free market CSVs, second independent source) | — | Market context only |
| **New 2025–26 entrants** | Tortus (x-api-key, AVM+comps+CI, early access), PropX402 (0.05 USDC/query, x402, no keys), HomeAnalytics, RentCast, Stream.Estate | Varies, mostly pre-pricing | Verify before committing; [VENDOR-PAGE] depth |

Cheapest scriptable pipeline (single home, ~$0–10/mo): monthly cron pulling Zillow Research + Redfin Data Center CSVs → SQLite, plus county assessor (public, often open API) and ATTOM trial key for AVM/comps. Full sketch in `home-selling-1-avm-market-data.md`.

## Category 2: FSBO listing platforms

No platform offers seller-facing APIs, webhooks, or data export — all are dashboard-only with gated buyer contacts.

| Platform | Cost | Reach | Notes |
|---|---|---|---|
| **Zillow ZFSBO** | Free; unlimited photos + video | Zillow + Trulia only; no MLS/IDX/Realtor.com | Zillow's own Listing Access Standards (upd. 2026-03) explicitly exempt FSBO from MLS-first rules |
| **ForSaleByOwner.com** | Free DIY plan (single plan on live page) | Own site only | No syndication; Rocket-owned |
| **Redfin / Realtor.com** | N/A — not listing venues | Redfin mirrors FSBO.com/Fizber ~48h late; Realtor.com is MLS-fed only | Reachable only via a broker's MLS filing |
| **HomeLister** (the real "HomeList") | State-dependent flat: Basic $599 total, Premium $1,699, Platinum $2,999 | MLS syndication | (homelist.com is a lamp store; homelist.co is parked) |
| **True-flat MLS services** | Beycome $99, HomeRise $95, Fizber ~$295 | MLS → full portal syndication | Hybrid tiers (Houzeo ~$249+0.5–1.25%, ListWithFreedom ~$89+%): 3–10× more once closing % counts |

Rules that constrain the strategy: owners cannot enter the MLS directly (broker "load" only); **Clear Cooperation (NAR 8.00, eff. 2026-01-01)** requires MLS submission within 1 business day of *any* public marketing — DIY-first sequencing must know this; MLSs **cannot fix commission rates** (CWMLS §1.9), so $0 comp is legal to list; limited-service listings must be coded LS/LR so cooperating brokers know they deal with you directly. Full analysis: `home-selling-2-fsbo-platforms.md` and `home-selling-5-economics-rules.md` §3.

## Category 3: Marketing & media

| Category | Buy (one-off) | Build (self-host on 72GB box) |
|---|---|---|
| Virtual staging | AI SaaS $0.24–3/img (AI HomeDesign, RoomGPT); human $24–75/room | SDXL + ControlNet + SAM2 defurnish — research-grade repos (`mithunparab/virtual-staging`, `Interior-stable-difusion`), 1–2 days to wire + QA |
| 3D tour | Kuula free tier ($0); Matterport ~$99–159/yr + camera | **Pannellum** (production-grade, ~1 day); Gaussian splats (SceneForge/OpenSplat) = research-grade, 1–2 weeks |
| Photo enhancement | DIY Lightroom presets + a few hours | **darktable CLI + Real-ESRGAN** batch pipeline — all production-grade OSS, trivially scriptable (easiest self-host win in the survey) |
| Drone | Hire a Part 107 pilot, $150–600 | Own drone only for repeat shoots; LAANC is the only API in this category (flight authorization, not images) |
| Open-house capture | Nothing worth it for one event | **Formbricks** (AGPL, free core with full API + webhooks, Docker) + QR on yard-sign card |
| Listing copy | Free tiers only (AgentListingAI) | **Local LLM via vLLM/llama.cpp fed structured assessor data** — one afternoon, $0 recurring, the highest-leverage build overall |

Full tables with vendor pricing + honest feasibility notes: `home-selling-3-marketing-media.md`.

## Category 4: Transaction, e-sign, CRM

- **Offer intake:** no OSS exists; Present My Offer ($10/yr after 2 free listings) is the cheapest real tool. Building is not worth it for one sale.
- **E-sign:** DocuSign Developer API floor **$50/mo** (40 envelopes), PandaDoc **$40/mo**, SignWell **25 docs/mo free** — all cloud SaaS. The OSS exception: **Documenso** (AGPL, 14.9k★, Docker+Postgres+S3+SMTP, real REST API/webhooks/SDKs) and **DocuSeal** (AGPL, 18.4k★) are production-viable; OpenSign/WaboSign/Penpact are hobby/research. For a notarized deed: RON-licensed notary regardless of signing stack (45 states + DC have permanent RON; CT excludes real-estate deeds; CA phased via SB 696).
- **Closing tech:** Dotloop/SafeDocs/DocuSign eClose/eOriginal/Pavaso are **lender/title-company loan-doc ecosystems** — you don't buy any of them in a plain sale; the buyer's lender+title company choose, and title/escrow costs (~$600–1500) exist either way. **No open-source closing-workflow engine exists** (searched 8+ term sets; closest real thing = MISMO standards, ~$3,500/yr membership).
- **Buyer-inquiry CRM:** listing portals hide inquiry data by design (zero API). The self-hosting-native answer: own landing page (static/Next.js + POST → Postgres/SQLite + SMTP + cron follow-ups). Ready-made OSS: WPResidence (self-hosted WordPress, forms to your DB).

Full detail + the "what I actually searched" list for the OSS claims: `home-selling-4-transaction-crm.md`.

## Category 5: Legal posture of "automate my home sale"

Verified against primary regulatory texts (TREC 22 TAC §535.4, Arkansas REC law, CA DRE advisory + AB 2992, FCC 24-17, Realtor.com ToS, CWMLS/Canopy rulebooks):

1. **Owner exemption:** selling your own home — own scripts, own site, own chatbot, own marketing — is legal in every state.
2. **Scraping is out:** Zillow, Realtor.com (ToS quoted directly), and MLS ToS all prohibit automated access. Compliant data path = your own listing data + county assessor/open-data + licensed vendor APIs.
3. **Reactive vs proactive communication:** responding one-to-one to inquiries that came to you is the defensible zone (CAN-SPAM: postal address + opt-out in commercial email). FCC 24-17 makes AI voice/voice-cloned calls "artificial or prerecorded voice" under TCPA → prior express (written, for telemarketing) consent + opt-out; cold automated outreach to wireless numbers is $500–1,500/violation territory.
4. **The SaaS trap is unlicensed brokerage:** productizing auto-list/auto-respond/negotiate *for other owners* is the licensed-activity line (up to $5k penalties in AR; Indiana HB 1068 targets exactly this). Owner-operated tooling is fine; "auto-sell-as-a-service" needs a licensed broker of record.

## What a developer would actually build (the concrete stack)

Everything self-hosted runs on the existing Portainer fleet; configs at `/mnt/tank/container-configs/<APP>`:

```
1. valuations/   cron → Zillow Research CSVs + Redfin Data Center + county assessor
                 + ATTOM trial key → SQLite → AVM ± confidence, ZIP trend, 10yr history
2. listing-site/ static/Next.js page (photos, 3D tour embed, disclosures)
                 + POST /inquiry → Postgres + SMTP self-notify + Formbricks open-house form
                 + QR code printed for yard sign / flyers / open-house card
3. media/        darktable-cli + Real-ESRGAN batch pipeline (photos)
                 Pannellum 360 tour served from the box (or Kuula free tier)
                 local LLM (vLLM/llama.cpp) → listing copy, social posts,
                 open-house script from one structured JSON of property facts
4. offers/       Present My Offer link ($10/yr) + Documenso for purchase agreement
                 + RON notary for the deed (state-dependent)
5. pricing/      $299–1,500 flat-fee MLS broker filing (the one non-DIY purchase)
```

Total incremental out-of-pocket (excluding unavoidable title/escrow ~$2.1–6.4k): **under ~$200** — vs $23–30.6k on the agent route, with the honest caveat that the median price gap is the real cost, not the commission.

## Source note

All five slice files carry inline citations with explicit `[SECONDARY]`/recency flags (several vendor pages 404'd or bot-blocked at fetch time; Zillow live ToS flagged for browser verification; commission figures all 2025–2026 except the Fed's pre-settlement baseline). Settlement facts trace to the Final Judgment (Doc. 1673) and the executed Settlement Agreement; MLS rules to CWMLS MINI (through 4/15/2025) and Canopy docs; licensing to TREC/Arkansas/CA/Indiana primary texts.

**Companion files:** `home-selling-1-avm-market-data.md` · `home-selling-2-fsbo-platforms.md` · `home-selling-3-marketing-media.md` · `home-selling-4-transaction-crm.md` · `home-selling-5-economics-rules.md`
