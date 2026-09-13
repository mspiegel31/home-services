# S4 — Offer/Transaction Management, E-Signature & CRM (incl. Open Source)

Target: experienced self-hosting developer selling a home (FSBO or agent-assisted). Focus: real APIs, self-hosting, total cost, privacy.

---

## A. Offer tracking / management tools for sellers

No dedicated "open-source offer tracker" exists; this is thin SaaS territory.

| Option | Cost | Dev/API posture | Notes |
|---|---|---|---|
| **Present My Offer** ([site](https://presentmyoffer.com/pricing/)) | 2 free listings, then $10/mo or $100/yr (unlimited listings); buyer agents submit free without accounts | None (web SaaS, no public API) | One submission link per listing; buyer agents upload offer docs; seller dashboard compares offers. Cheapest real offer-intake tool; good enough for a single sale |
| **Houzeo Offers** ([site](https://www.houzeo.com/products/houzeo-offers)) | Free tool, but locked behind Houzeo Gold/Platinum seller packages (Houzeo is a "discount brokerage" listing service, ~$995–1495 flat fee to list) | None | Compare/counter offers (price, closing date, earnest money), H&Best tracking. Only worth it if you buy their listing service |
| **Fizzbo** ([site](https://fizzbo.net/)) | Free to list; one-time flat fee for pro tools (no % commission) | None, consumer app | In-app offer receive/compare/counter, verified-buyer messaging, closing checklists. Consumer product, no developer hooks |
| **Offer2Close** ([site](https://offer2close.piol.ai/for-homeowners)) | $19/mo after 14-day trial, up to 5 properties | None | State-specific closing checklists, document tracking, buyer portal + messaging. Closest thing to a "FSBO transaction coordinator" SaaS |

**Developer verdict:** for one house, Present My Offer ($10/yr) + your own docs covers offer intake. Building a bespoke offer tracker is not worth it unless you're collecting offers programmatically from multiple channels.

---

## B. E-signature with real dev APIs

### Pricing tiers (verified from vendor pricing pages)

**DocuSign Developer API** — [pricing page](https://ecom.docusign.com/plans-and-pricing/developer):

| Plan | Price | Envelopes | API features |
|---|---|---|---|
| Free Developer Account | $0 | sandbox/demo only | full API in sandbox |
| **Starter** | **$50/mo ($600/yr)** | 40/mo starting | SDKs, OAuth, API usage center |
| Intermediate | $300/mo ($3,600/yr) | 100/mo starting | + collaborative commenting, scheduled send, branding |
| Advanced | $480/mo ($5,760/yr) | custom | + PowerForms, Recipient Connect, bulk send |
| Enhanced | custom (5-user min) | custom | SSO, MFA, custom workflows |

Overage: pay-as-you-go per envelope; [overage FAQ](https://support.docusign.com/s/articles/FAQ-Docusign-overage-charges?language=en_US) lists Standard annual at $3.00/subscribe or $3.60/pay-as-you-go envelope. DocuSign also sells consumer **eSignature Personal** at $10/mo (5 envelopes/mo) — but that's web-UI, not an API product. Real Estate plans: Starter $10/mo, Real Estate $25/mo (100 envelopes/user/yr) per [real-estate pricing](https://ecom.docusign.com/plans-and-pricing/real-estate) — again, not the developer API. **Key point: API access has a hard floor of $50/mo regardless of volume; for a single sale that's the cost of the privilege, not usage.**

**PandaDoc API** — [pricing page](https://www.pandadoc.com/developer-api/pricing/):

| Plan | Price | Documents |
|---|---|---|
| Free | $0 | 60 docs/yr, 2 recipients/doc, 5 templates, full sandbox |
| **API Developer** | **$40/mo** | 40 docs/mo, then $4/doc extra |
| Enterprise | custom | volume, CRM integrations, SSO |

Caveat from [PandaDoc help center](https://support.pandadoc.com/en/articles/9714958-pandadoc-api): production API access is tied to their plan/Dev Center; sandbox is free and open. Effectively: **$40/mo minimum for live API use.**

**Cheaper alternatives:**

| Option | Cost | Dev posture |
|---|---|---|
| **SignWell** — [API pricing](https://www.signwell.com/api-pricing/) | First 25 API docs/mo free (credit card required); $0.85/doc after, down to ~$0.20/doc at volume. No monthly minimum | REST API, webhooks, embedded signing, SDKs. Cheapest credible hosted API for low volume: a single home sale = ~free |
| **SignEasy** — [API pricing](https://signeasy.com/pricing/api) | Usage-based per-document (cheaper than DocuSign; exact rates on page) | REST API, webhooks |
| **Adobe Sign / HelloSign legacy** | pricier, enterprise-oriented | full API; rarely the right pick for one sale |

**Developer verdict:** DocuSign is the most complete API (OAuth, webhooks, bulk, connectors, eClose platform) but the $50/mo floor is absurd for one transaction. PandaDoc $40/mo is comparable. **SignWell's free 25 docs/mo is the rational hosted choice for a single home sale** — REST + webhooks + embedded signing, no monthly fee at your volume. All three are cloud SaaS: your documents (contracts = sensitive) live on their servers.

### E-signature legality note
ESIGN Act (federal) + state UETA make e-signatures valid for real-estate purchase agreements, deeds, disclosures. Notarized documents are the exception: if the deed requires a notary (most states do), the notary's act must be wet-ink **or** done via a RON-compliant platform. A purchase agreement between buyer/seller does not need notarization in most states.

---

## C. Transaction/closing tech (US) — what's actually required

**Plain FSBO sale (cash or conventional, no government program):**

1. **What's required:** purchase agreement (e-signature fine), earnest money handling (escrow/title attorney), deed prepared + notarized + recorded with county recorder. That's it. No title company, no loan docs, no "eClosing platform."
2. **What's optional in a plain sale:** Dotloop, SafeDocs, DocuSign eClose, Pavaso, OneSpan, DocMagic — **these are loan-document ecosystems used by title companies/attorneys for financed (mortgage) closings.** They manage loan docs (disclosures, notes, deeds of trust), not FSBO transaction logistics. You'd only "use" them by using a title company/attorney who uses one. In a cash FSBO sale you'd typically just pick a title company or attorney, they run their own workflow, you sign in whatever they give you.
3. **eClosing (full RON closing) requirements** (per [Snapdocs digital-closing guide](https://www.snapdocs.com/resource-center/blog/how-to-know-which-states-accept-digital-closings) and [Stewart title eClosing guide](http://go.stewart.com/rs/067-YWO-436/images/352485842%20AS-%20eClosing%20Guide%20-%20Detailed%20-%20HR.pdf)):
   - A true eClosing needs all four: eSigning + eNotarization (RON) + eNote + eRecording, all digital.
   - Full eClosing requires the county to accept eRecorded remotely-notarized docs; where eRecording is unavailable, "papering out" is required and the closing is only *hybrid*. eRecording covers ~55% of jurisdictions but 86%+ of the US population [SECONDARY: Snapdocs].
   - Title underwriters (Stewart, Fidelity, etc.) must approve the platform; lenders typically dictate which platform is used. In a financed buyer's deal, **your buyer's lender + their title company decide the platform — you as seller have little choice.**
4. **RON state availability:** as of early 2025, **45 states + DC have permanent RON laws** ([MBA RON adoption map](https://www.mba.org/advocacy-and-policy/residential-policy-issues/remote-online-notarization); [notarycam 2025 state list](https://www.notarycam.com/remote-online-notary-laws-which-states-allow-online-notarization-in-2025/)). Connecticut enacted RON but excludes real-estate deeds for it [MBA]. Delaware restricts RON to attorneys. California's RON is phased (SB 696, full by 2030). Verify for your specific state/county before assuming remote notarization of the deed works.

**Platform comparison (for reference, not needed for most FSBO sales):**

| Platform | Positioning | Cost posture | API |
|---|---|---|---|
| **Dotloop** — [pricing](https://www.dotloop.com/products/plans-pricing/) | Loan-doc eClosing for agents | Free (10 loops); Premium $34.99/mo or ~$344/yr | No public self-serve API; agent product |
| **SafeDocs** | Similar, DocuTech family | Per-user/mo, agent product | Closed |
| **DocuSign eClose/Notary** | Enterprise RON + eClosing platform | Sales-quoted per transaction; [DocuSign Notary terms](https://www.docusign.com/legal/terms-and-conditions/schedule-docusign-signature/attachment-notary-ron) require you to obtain the RON-licensed notary | Full API (Notary is an API product), but pricing is custom |
| **eOriginal ClosingCenter** ([WK](https://www.wolterskluwer.com/en/solutions/eoriginal/closing-center)), **Pavaso**, **DocMagic** | Enterprise settlement | custom | limited/closed |

**Adoption context:** Snapdocs 2025 survey: 90% of lenders *offer* digital closings but only 14% close >80% of loans digitally ([press release](https://www.businesswire.com/news/home/20250415362025/en/Snapdocs-Study-Finds-90-of-Lenders-Offer-Digital-Closings-Yet-Only-14-Achieve-High-Adoption)); hybrid eClose is still the most common form.

**Bottom line for a plain sale:** you don't buy any of these. Budget instead for: title company/escrow fees (~$600–1500, split or seller-paid per local custom), attorney if required, and one e-sign account for the purchase agreement.

---

## D. Buyer inquiry / CRM for an FSBO seller

| Option | Cost | Dev posture | Self-host |
|---|---|---|---|
| **WordPress + WPResidence** ([lead-gen forms/CRM](https://wpresidence.net/wpresidence-lead-generation-forms-crm/)) | theme ~$69–149; host your own | Leads stored in your DB; HubSpot sync via single API key; Zapier/hooks for the rest | **Yes** — forms (inquiry, schedule-a-tour) post to your database; you own the data |
| **Property listing platforms with FSBO tiers** (Zillow FSBO, Realtor.com, FSBO-specific: HouseList, FSBO.com) | ~$150–500/90 days | **No API for inquiry data** — leads come as email/phone; Zillow hides contact details to push you to agents | No |
| **Build-your-own landing page** (any static site + form endpoint) | $0 + domain | Full control: POST to your server/webhook, store in SQLite/Postgres, email via your own SMTP, optional chat widget | **Yes** — trivial for a dev; this is the self-hosting-native answer |
| **Follow Up Boss / Pipedrive / HubSpot Free** | $0 (HubSpot free tier) – $45+/mo | REST APIs, webhooks, all standard | No (SaaS; Pipedrive has no self-host; HubSpot free tier is the practical choice) |

**Developer verdict:** Zillow/Realtor.com listings are where buyer traffic lives, and they don't expose inquiry APIs (by design — it's their monetization). The self-hosting-native stack is: Zillow for eyeballs + **your own landing page (Next.js/static + webhook form) as the canonical inquiry endpoint** shared everywhere (open-house QR, yard-sign QR, direct links). Store inquiries in Postgres, email yourself via SMTP. A `follow-up` scheduler (cron) beats any $50/mo CRM for one sale. Houzez/WPResidence are the "ready-made" version of this if you want prebuilt forms; they self-host on your box (WordPress) but are PHP, not a dev API.

---

## E. Open source / self-hostable (honest maturity assessment)

### E-signature — the one area where OSS is actually viable

| Project | License | Maturity | Evidence |
|---|---|---|---|
| **Documenso** ([github](https://github.com/documenso/documenso)) | AGPL-3.0 (enterprise features: SSO, 21 CFR 11, license-key gated) | **Production-viable** | 14.9k stars, pushed 2026-09-05, 234 open issues, active. Real API: [docs](https://docs.documenso.com/docs/developers) — API key auth at `/api/v2`, webhooks, official TS/Python/Go SDKs, embedding. Docker compose with Postgres + S3 + SMTP + signing cert. This is the strongest "self-host DocuSign" option |
| **DocuSeal** ([github](https://github.com/docusealco/docuseal)) | AGPL-3.0 | **Production-viable (community)** | 18.4k stars, pushed 2026-08-31. Rails, WYSIWYG form builder, REST API + webhooks, S3/GCS/Azure storage, 14 signing languages. Some Pro features are paywalled but core self-host is free |
| **OpenSign** ([github](https://github.com/OpenSignLabs/OpenSign)) | AGPL-3.0 | **Hobby/early-production** | 7.0k stars, pushed 2026-08. Node/Mongo/React, docker-compose + Caddy, basic API. Simpler than the two above |
| **WaboSign** ([github](https://github.com/wabolabs/wabosign)) | AGPL-3.0 | **Hobby** | DocuSeal fork, 0 stars, released 2026-06; all features no-paywall. Small community |
| **Penpact** ([github](https://github.com/penpact/penpact)) | AGPL-3.0 core | **Research/pre-1.0** | v0.1.0 (Jun 2026), 2 stars. Embeddable e-sign engine, TS SDK + generated Python/Go/PHP clients — architecturally interesting (signing as a library), not production |
| **esig-suite** ([github](https://github.com/vmvtech/esig-suite)) | open source | **Research/library** | No SaaS, self-issued per-tenant certs, append-only audit log, React UI components. A signing *library* you wire into your own app |
| Others found: goSign (Go+SvelteKit), lifted-sign (SQLite default, ESIGN/UETA framing), DottedSign self-hosted (AGPL, enterprise-oriented) | — | hobby/research | lower traction; listed for completeness |

**Honest verdict:** for a home sale you legally need counterparty trust + tamper evidence, which is exactly where self-hosted OSS is weakest (no trusted timestamping infra, no notary workflow, counterparty has to use your URL). **Documenso or DocuSeal are production-grade enough** to sign a purchase agreement between two adults who both trust you (buyer signs at your link). For notarized docs, use a RON-licensed notary regardless of signing stack.

### Real-estate CRM — OSS exists but is the wrong shape

| Project | Maturity | What it actually is |
|---|---|---|
| **InsulaCRM** ([github](https://github.com/InsulaCRM/InsulaCRM), MIT) | hobby (16 stars, pushed 2026-08, 6 open issues) | Wholesaler CRM (Laravel 12 + MySQL): motivated-seller leads, property pipeline, ARV/MAO calcs, 20-endpoint REST API, embeddable lead-capture form. Closest real OSS "real-estate CRM" with an API, but built for investment-flipping pipelines, not "one house + 50 buyer inquiries" |
| **BrokerOS** ([github](https://github.com/sumamakhan761/BrokerOS), MIT) | hobby (2 stars, pushed 2026-09, 14 open issues) | NestJS/Next.js/Postgres brokerage + channel-partner platform. Overkill, barely a community |
| **liberusoftware/real-estate-laravel** (MIT) | hobby | UK-flavored (Rightmove/Zoopla sync) property team app — wrong market |
| **WPResidence** (WordPress, not OSS core) | production (commercial theme) | see section D |
| **Complete Home Seller Intake** ([github](https://github.com/IfBilal/Complete-Home-Real-Estate-Seller-Intake-Platform)) | research/one-off | Next.js+Supabase seller intake form — a personal project, not a product |

**Honest verdict:** no production open-source CRM exists for the "FSBO seller's 40 buyer leads" problem. The problem is too small (one property, months-long) for an off-the-shelf product — including commercial CRMs. A 30-line web form + Postgres table + cron follow-ups is the correct OSS answer; InsulaCRM is the nearest existing project if you specifically want a REST-API property pipeline and can tolerate a wholesaler-shaped schema.

### Transaction/closing management — **no open-source option exists. Said explicitly.**

**What I searched** (GitHub/web, 2026-09): "open source real estate CRM", "self-hosted real estate CRM", "open source e-signature self-hosted", "eSignGenie open source", "open source transaction coordination closing workflow", "eClosing self-hosted", "transaction management real estate GitHub", "closing workflow open source".

**Findings:** every result in closing/transaction territory is either:
- commercial settlement SaaS (Dotloop, SafeDocs, DocuSign eClose, eOriginal, Pavaso, OneSpan, DocMagic, Black Knight Expedite Close, [Stavvy](https://stavvy.com/real-estate-closing-software)), or
- **standards, not software**: [MISMO](https://www.mismo.org/get-involved/workgroup/title-and-closing) (mortgage data standards, OpenAPI YAML datasets for eMortgage/eNote/closing instructions; Title & Closing Community of Practice; standards membership ~$3,500/yr) — the correct reference for data shapes but no runnable project.

No self-hostable open-source "Dotloop alternative" or closing-workflow engine exists in any production-grade form. Building a closing workflow is also the wrong move: the workflow is dictated by the title company/lender's platform and state recording requirements, not by you.

---

## F. Recommended stack for a self-hosting developer (single home)

| Need | Pick | Cost |
|---|---|---|
| Offer intake | Present My Offer (or just an email alias + Documenso forms) | ~$10 |
| Purchase agreement + disclosures e-sign | **Documenso self-hosted** (Docker: Postgres, S3-compatible object store, SMTP, signing cert) — API + webhooks included, AGPL core; counterparty signs at your URL. Fallback if you don't want to run it: SignWell (first 25 docs/mo free) | $0 (homelab) or ~$0 |
| Notary | RON-licensed notary (state-dependent; 45 states+DC have permanent RON) — wet-ink fallback if your state/county excludes real-estate deeds from RON | notary fee, ~$75–150 |
| Title/escrow/closing | local title company or attorney; they run their own eClosing platform if buyer is financed — you don't choose or pay for Dotloop/SafeDocs | ~$600–1500 (negotiable) |
| Buyer inquiries | Zillow for discovery + own landing page (static/Next.js + POST endpoint → Postgres + SMTP email + cron follow-ups) | $0 |

**Total incremental cost to you: under ~$200**, plus title/escrow fees that would exist anyway.
