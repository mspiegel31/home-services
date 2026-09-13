# 2026 US Home-Selling Economics & the Rules Governing a Seller's Automation

Research slice 5 of the home-sale tools investigation. Target reader: experienced dev, self-hosting homelab, cost- and privacy-sensitive. All commission figures are post-settlement (effective Aug 17, 2024) — this landscape changed materially in 2024–2026.

**Naming correction up front (important):** The assignment references "Hardesty v. NAR / DRE litigation." No NAR commission case named *Hardesty* exists in the docket. The actual case is **Burnett v. National Association of Realtors, 4:19-cv-00332-SRB (W.D. Mo.)** — the "Sitzer-Burnett" seller-side class action — with final judgment entered **Jan 15, 2025**. ("Hardesty v. Sacramento County" is an unrelated civil-rights case; the "DRE" reference in the assignment corresponds to the **California Dept. of Real Estate** advisories on the settlement's effect, detailed in §1.3.) All settlement facts below trace to the court's Final Judgment, the executed Settlement Agreement, and official NAR statements.

---

## 1. Post-settlement commission landscape (2024–2026)

### 1.1 What the settlement actually changed — traceable to court documents

**Sitzer-Burnett v. NAR (Burnett v. NAR, 4:19-cv-00332-SRB, W.D. Mo.)**
- Settlement Agreement executed **March 15, 2024**: NAR pays **$418 million over ~4 years** in exchange for a nationwide release of home-seller commission claims. [Settlement Agreement (executed, hosted by blocksandlots): https://blocksandlots.com/wp-content/uploads/2024/03/Realtors-NAR-Settlement-EXECUTED.pdf ; NAR's own statement of terms: https://www.nar.realtor/sites/default/files/documents/nar-settlement-faq-2024-05-05.pdf]
- **Final Judgment entered Jan 15, 2025** (Doc. 1673): class = "all persons who sold a home listed on an MLS anywhere in the US where a commission was paid to any brokerage," with per-MLS date ranges running back to 2014–2019; the injunction/release **extends to any MLS nationwide "regardless of affiliation with NAR," explicitly including NWMLS, WPMLS, REBNY/RLS**. [Court PDF: https://www.mow.uscourts.gov/sites/mow/files/ca/19-cv-332-1673FinalJudgment-NAR.pdf]
- Release scope: NAR, 1M+ members, all state/local REALTOR associations, all REALTOR MLSs, and brokerages with ≤$2B 2022 residential volume. **HomeServices of America was NOT released** — it struck its own **$250M settlement (April 26, 2024)**; large brokerages/MLSs could opt in via a formula or mediation. Total industry payout in these cases ≈ **$876M–$943M+**. [NAR FAQ: https://www.nar.realtor/sites/default/files/documents/nar-settlement-faq-2024-04-19.pdf ; AP: https://apnews.com/article/real-estate-commission-lawsuit-homeservices-warren-buffett-f933f5997d8e1e1d90549c00af84493e]
- **Practice changes (effective Aug 17, 2024)** — these are the rules that actually constrain a seller's automation: [NAR Settlement FAQs, May 5 2024, Q20 & Q45: https://www.nar.realtor/sites/default/files/documents/nar-settlement-faq-2024-05-05.pdf]
  1. **No offers of compensation on the MLS.** All broker-compensation fields removed; MLSs may not provide any compensation field, "Yes/No" field, or agent-remark workaround.
  2. **No off-MLS compensation platforms built on MLS data.** A broker may publish its *own* comp offer on its own website/IDX, but using MLS feeds to run a multi-broker compensation platform is prohibited (MLS terminates access if found).
  3. **Written buyer-broker agreements required before a buyer tours** (any tour, including a virtual one the agent initiates). Agreed compensation must be "objectively ascertainable and not open-ended" — and it caps what the buyer's agent may take from *any* source.
  4. **Seller concessions remain allowed on the MLS** (e.g., "offering $10,000 toward closing costs") **only if not conditioned on payment to a buyer broker.**
  5. Non-filtering of listings by comp/brokerage is reaffirmed (pre-2021 Policy 8.5, clarified).

**What this means in plain terms for a seller:** the seller's own commission with the listing broker is fully negotiable and was always negotiable (settlement FAQ Q32/Q34 — NAR concedes it did not "make" commissions negotiable). What died is the *pipeline*: the buyer's-agent commission is no longer published on the listing, so it is now set between the buyer and their agent, with the seller optionally conceding money. Post-settlement, most buyers still end up with a seller-funded buyer's-agent comp (see 2025 data below) — the money moved, it did not disappear.

### 1.2 Current typical commission ranges (2025–2026 data — fresh, not stale)

| Metric | Value | Source | Recency |
|---|---|---|---|
| Average *total* commission (buyer+seller side) 2025 | **5.44%** (up from 5.32% in 2024); on a $367,711 median home = $20,003 ($10,186 listing side @ 2.77%, $9,818 buyer side @ 2.67%) | Clever Real Estate survey of 806 agents, PR Newswire, Jun 17 2025: https://www.prnewswire.com/news-releases/agent-commissions-edge-higher-in-2025-one-year-after-landmark-nar-settlement-302483289.html | 2025 |
| Average *total* commission 2026 | **5.70%** (survey of 533 agents; highest since 2021; 64% of sellers pay a 2.5–3% listing fee) | Clever 2026, updated Aug 20 2026: https://listwithclever.com/real-estate-blog/6-percent-real-estate-commission-explained/ | 2026 |
| Buyer's-agent commission, Q1 2025 | **~2.40%** (flat vs. Q4 2024's 2.37%) | Redfin, via HousingWire: https://www.housingwire.com/articles/redfin-buyers-agent-commissions-largely-unchanged-after-nar-settlement/ | Q1 2025 |
| Pre-settlement baseline (buyer side) | ~3% in late 1990s → ~2.7% by 2022; 2022 distribution still mode=3%; 2024 BEA: commissions+related costs ≈ **$170B/yr (0.6% of GDP)** | Federal Reserve FEDS Note, May 12 2025 (CoreLogic data): https://www.federalreserve.gov/econres/notes/feds-notes/commissions-and-omissions-trends-in-real-estate-broker-compensation-20250512.html | 2025 |
| Share of sellers paying a full 6% | ~14% paid exactly 6%; ~16% paid 6%+; average total ~4.7% [SECONDARY — attributed to NAR 2025 Profile but the full Profile is paywalled; primary NAR highlights PDF omits the commission chapter] | https://listwithclever.com/real-estate-blog/6-percent-real-estate-commission-explained/ | 2025 |

**Fed staff's bottom line (May 2025):** post-settlement, buyer-agent commissions "may have declined some but have remained at relatively high levels"; local norms are sticky — low-commission listings historically get less cooperation from other brokers and sell for less. [Fed note, Conclusion]

**NAR 2025 Profile (transactions Jul 2024–Jun 2025, published Nov 4 2025):** 91% of sellers used an agent (record high); FSBO at an all-time-low 5%; 88% of buyers used an agent. [NAR highlights PDF: https://www.nar.realtor/sites/default/files/2025-11/2025-profile-of-home-buyers-and-sellers-highlights-11-04-2025.pdf]

### 1.3 State layer: California DRE advisories + AB 2992 (the "DRE" part of the assignment)

- **CA DRE Licensee Advisory (Dec 12, 2024, amended):** post-settlement, "sellers and their listing agents no longer will determine compensation for the buyer's agent." The signed buyer-broker agreement sets the **maximum** the agent may receive from any source; DRE will not enforce settlement terms themselves but enforces AB 2992 + the Real Estate Law. https://dre.ca.gov/Licensees/Advisories/Advisory_2024_11_14_Changes_to_Buyer_Representation.html
- **AB 2992 (eff. Jan 1, 2025, signed Sep 24 2024):** buyer's agent must have a signed representation agreement with compensation, services, payment timing, and a max 3-month term no later than offer execution.
- DRE-identified practices that get licensees in trouble: verbal compensation changes, claiming a "standard" rate (commissions are fully negotiable under CA law), undisclosed dual agency, advance fees without DRE no-objection.
- Other states: 15+ states had pre-existing buyer-rep-agreement laws; 8 had buyer-rebate bans (Fed note Table 1 — e.g., Alabama, Kansas, Missouri, Tennessee). A Feb 2025 FCC rule change pushed real-estate telemarketing toward one-to-one consent requirements (see §4.2).

---

## 2. What FSBO actually saves in 2026 (realistic numbers)

### 2.1 The savings, itemized

Commission savings on the seller side: **2.5–3%** (the listing-fee component you no longer pay), i.e. **$10,600–$12,750 on a $425,000 home**. Post-settlement, you additionally *choose* how much, if anything, to offer the buyer's agent (pre-settlement this was forced via the MLS).

### 2.2 The offset: FSBO sells for less

**NAR 2025 data (primary): median FSBO sale price $360,000 vs $425,000 agent-assisted — an 18% ($65,000) gap.** NAR itself notes this is not a controlled experiment (FSBO skews to cheaper/rural/mobile-home segments). [NAR: "FSBOs Reach All-Time Low," https://www.nar.realtor/news/real-estate-news/fsbos-reach-all-time-low-more-sellers-rely-on-agents] *(Possibly stale for 2026 pricing — data window is Jul 2024–Jun 2025; the gap direction has been stable for decades in prior Profiles.)*

Second-party math check: [SECONDARY] HomeLight works an example where a $339k FSBO nets *less* than a $400k agent-assisted sale after commissions; Opendoor's iBuyer-published cost guide puts total FSBO outlay at $10k–$20k for a median-priced home. (Both have commercial motives — Opendoor buys houses, HomeLight leads agents — treat as directional.)

### 2.3 Realistic 2026 net-savings estimate

| Scenario | $425k home |
|---|---|
| Listing-commission saved (2.5–3%) | +$10,625 … +$12,750 |
| DIY marketing/transaction out-of-pocket (see §5) | −$2,500 … −$6,000 |
| Buyer-agent comp you choose to offer (1.5–2.5% post-settlement) | −$6,375 … −$10,625 |
| Price effect: selling at the NAR-observed median FSBO discount (−15…18%) vs agent-assisted | −$63,750 … −$76,500 *(if the discount materializes on your home)* |
| **Gross savings, no price effect** | **~$2,000 … +$4,000 (before buyer-agent comp; ~+$12k if you offer zero buyer comp and it still sells)** |
| **Net after price effect** | **−$50k … −$75k** |

**Bottom line:** FSBO "saves" 2.5–3% on commission but the observed median price gap is ~18% — an order of magnitude larger. The realistic expected value of FSBO is *negative* unless your property is unusually easy to sell (high-demand market, distinctive property, cash-buyer-likely) or you accept a longer time-on-market. The credible middle path in 2026 is a **flat-fee/limited-service broker** (§3): you pay $500–$1,500 for MLS entry + cooperation handling and keep 2.5–3% minus the price risk of an unlisted-by-agent home. Clever's 2025 survey: 9% of sellers used a discount/flat-fee broker.

---

## 3. MLS participation rules — can an FSBO get on the MLS?

**Verified against two real MLS rulebooks (primary sources), plus NAR/FTC material:**
- **CWMLS "MINI" Handbook** (Central Wisconsin MLS; rules amended as recently as Apr 15 2025): https://www.cwbr.org/clientuploads/PDFs/CWMLS/CWMLS_MINI.pdf
- **Canopy MLS support docs** (limited-service listings): https://support.canopymls.com/kb/article/76-limited-service-listings/
- NAR 2015 Multiple Listing Policy Handbook [SECONDARY host — Inman archive]: https://assets.inman.com/wp-content/uploads/2015/02/2015-NAR-MLS-Policy-Handbook.pdf
- Realcomp v. FTC (2009) & 6th Cir. (2011): https://www.ftc.gov/sites/default/files/documents/cases/2009-11-091102realcompopinion.pdf

### 3.1 The answer

**An owner cannot enter their own home on a real MLS. MLS entry is a subscriber service for licensed brokers; every MLS entry in the CWMLS rulebook is a *listing taken by a Participant* under a listing contract, entered via "broker load."** FSBO records (CWMLS "One-Party"/"FSBO (One Party/BA)" fields) are entered **only after closing** (within 30 days of close, IDX excluded) — i.e., for sold-data purposes, not for marketing.

The 2026 route to MLS exposure for an owner: **hire a licensed broker on a limited-service/flat-fee contract.** Verified mechanics (CWMLS §1.2.3, Canopy):
- The broker signs a listing agreement with you and is the party of record; they may contractually *omit* services: arranging showings, accepting/presenting offers, advising on offers, counteroffers, negotiating — the listing is then coded "LS/LR" in the MLS so cooperating brokers know they'll deal with you directly.
- Requirements you inherit as the owner: all MLS data fields complete and accurate ($100 + $5/day fines for bad data), at least one representative photo (listings without photos get deleted), signed listing contract uploaded to the MLS system, cooperation with cooperating brokers (they may show and present offers directly to you under an LS listing).
- Canopy adds: listing must sit under a broker-in-charge with affiliated agents; the listing agent must be an **active MLS subscriber**; MLSs prefer attorney-drafted limited-service agreements over standard forms.
- MLSs **cannot** charge/require specific commission rates (CWMLS §1.9 is explicit: "shall not fix, control, recommend, suggest, or maintain commission rates or fees... or the division of commissions") — so a $0 comp offer to cooperating brokers is legal to list.
- Post-settlement, MLS listings carry **no compensation fields at all**; your comp offer (if any) goes off-MLS (your own listing page / brokerage IDX — permitted for the listing broker's own listings, NAR FAQ Q46).
- **Clear Cooperation** still bites: once you (or your broker) publicly market, the listing must be in the MLS (CWMLS: same calendar day for yard signs; 1 business day after any other public marketing) — fines $500→$5,000 escalating. You cannot quietly "pocket-list" an FSBO and run your own marketing.
- **Office-exclusive** option: broker takes the listing but does not publicly market or disseminate it (must still be filed with the MLS; no public advertising of any kind while office-exclusive).
- FTC/Realcomp background: MLSs may not exclude limited-service (formerly "exclusive agency") listings from IDX/public feeds — that practice was ruled an antitrust violation, so a flat-fee LS listing does syndicate to Realtor.com/Zillow feeds like a full-service one.

### 3.2 What MLS rules restrict (cheat sheet for an automation project)

| Restriction | Source |
|---|---|
| Only licensed-broker subscribers may input listings; owner-direct entry not possible | CWMLS "Listing Procedures"; NAR MLS Handbook |
| No compensation data on the MLS (all forms) | NAR settlement practice change, eff. 8/17/2024 |
| No compensation-conditional seller concessions on the MLS | NAR settlement FAQ Q69 |
| Accuracy + completeness of data; photo required; contract filed | CWMLS §1.2, photo rule, "Filing Listing Contracts" |
| Clear Cooperation timing (public marketing ⇒ MLS entry) | CWMLS Listing Procedures (2025 update) |
| Status/price changes must be reported in writing within 3 business days | CWMLS §1.4 |
| Limited-service listings must be coded and disclosed to cooperating brokers | CWMLS §1.2.3 |
| Open listings and net listings not accepted | CWMLS "Listing Procedures" |
| Local MLSs may set their own flat-fee/LS participation rules and fees | CWMLS Note 2; Canopy |

---

## 4. Legal/technical feasibility of "automate my home sale" in the US

### 4.1 Scraping real-estate data (Zillow/Realtor.com)

- **Zillow Terms of Service prohibit automated access/scraping.** I attempted to fetch https://www.zillow.com/terms/ directly to quote the clause; the site serves 403/bot-blocks to non-browser fetchers and the Wayback CDX was rate-limited, so the exact text is cited from secondary commentary: Zillow's ToU prohibits automated queries and data scraping, with narrow fair-use/search-engine carve-outs [SECONDARY: https://zillowscraper.com/is-it-legal-to-scrape-data-from-zillow/ ; legal analysis: Fordham IPLJ, "Data Scraping as a Cause of Action," https://ir.lawnet.fordham.edu/cgi/viewcontent.cgi?article=1705&context=iplj]. **Verify against the live ToS in a browser before relying on this.**
- **Realtor.com Terms of Use (primary, fetched):** explicitly prohibits copying/scraping Content by "robots, scripts, spiders" or any automated means, data mining, and use for ML/AI training, with civil/criminal liability asserted: https://www.realtor.com/terms-of-use/
- **MLS terms similarly prohibit automated extraction** (e.g., NWMLS ToS bans robots/spiders/data mining — https://www.nwmls.com/terms-of-use/).
- **Legal posture:** post-*Van Buren* (2021), the CFAA is unlikely to reach scraping of data you're authorized to view; the real risks are **breach of contract (ToS), copyright (if data fields are protectable), and state trespass-to-chattels theories**, plus certain IP bans. For a self-hosted automation, the compliant path is: (a) use your *own* listing data (photos, price, disclosures) which you own; (b) pull **county assessor/records data** (public, often open APIs or open-data portals); (c) for market data, buy licensed feeds (CoreLogic, MLS IDX under a licensed entity) or use vendor APIs with written permission. Scraping Zillow to auto-price or auto-monitor comps is a ToS breach on every serious platform — not a clean automation primitive.

### 4.2 CAN-SPAM / TCPA — responding to buyer inquiries

- **Inbound inquiries (buyer emails/calls/DMs you):** responding one-to-one to a person who initiated contact is the low-risk zone. An **automated email reply** that is "commercial" must still satisfy CAN-SPAM: truthful subject lines, identify the message as an ad where applicable, include your **valid physical postal address**, and provide a **functioning opt-out honored within 10 business days** (mechanism live ≥30 days). [FTC CAN-SPAM guide: https://www.ftc.gov/business-guidance/resources/can-spam-act-compliance-guide-business ; 16 C.F.R. Part 316: https://www.govinfo.gov/content/pkg/CFR-2025-title16-vol1/pdf/CFR-2025-title16-vol1-part316.pdf]
- **Outbound automation is where TCPA lives:**
  - **FCC 24-17 (Feb 2, 2024, declaratory ruling — primary): AI-generated voices, including voice cloning, are "artificial or prerecorded voice" under the TCPA.** Calls using them require **prior express consent** of the called party; telemarketing adds a **prior express *written* consent** requirement (47 C.F.R. § 64.1200(a)(2)–(3)); every such message needs responsible-entity identification and opt-out. https://www.dwt.com/-/media/files/2024/02/fcc2417a1.pdf
  - Practical consequence: **an AI voicebot or auto-dialed/robotext outreach to prospective buyers = prior express (written) consent + opt-out + identity disclosure.** A chat-style, human-initiated text conversation with a lead who gave their number for that purpose is lower-risk, but the 2023–2025 FCC rulemaking cycle (DNC applies to texts; one-to-one consent for ATDS) makes *cold* automated outreach to wireless numbers a $500–$1,500-per-violation liability class-action magnet (statutory damages, state AG enforcement). NAR publishes its own compliance guidance: https://www.nar.realtor/telemarketing-cold-calling
- **Design conclusion for a seller automation:** a *reactive* stack (inquiry form → stored lead → human/AI-drafted replies you send or a chat window the buyer opens) is defensible; an *aggressive proactive* stack (auto-texting your Zillow lead list, AI voice calls) is not — and every message still needs CAN-SPAM postal address + opt-out plumbing.

### 4.3 State licensing — who may "market" and "list"

The unlicensed-activity line is state-by-state but follows one pattern, verified against two primary regulatory texts:

- **Texas (TREC, 22 TAC § 535.4 — primary):** a license is required to **solicit listings, negotiate listings, show property, and — for compensation — advertise property for sale, handle inquiries from such ads, or refer inquiries**. TREC's unlicensed-assistant guidance is the practical rulebook: an unlicensed person (including an owner's automated assistant service) may do ministerial work under a licensed broker's supervision, but compensated solicitation/negotiation/showing is licensed activity. https://www.law.cornell.edu/regulations/texas/22-Tex-Admin-Code-SS-535-4 ; https://www.trec.texas.gov/article/use-unlicensed-assistants-real-estate-transactions
- **Arkansas (REC license law — primary):** unlicensed activity includes selling, listing, or negotiating for another for compensation; civil penalties up to **$5,000** plus disgorgement; **owner exemption** covers persons dealing in *their own* real property. https://arec.arkansas.gov/wp-content/uploads/AR-Real-Estate-License-Law-July-2022-Final.pdf
- **California (DRE):** licensee-side duties from the advisory above; CA also requires written comp agreements and DRE no-objection for advance fees.
- **Indiana HB 1068 (eff. Jul 1, 2024 — primary):** new statute specifically regulating **unlicensed real-estate solicitors** — evidence states are closing the "unlicensed lead-gen" gap. https://iga.in.gov/pdf-documents/123/2024/house/bills/HB1068/HB1068.05.ENRS.pdf

**Where "automate my home sale" legally lands:**
1. **You, the owner, selling your own home:** universally exempt (owner exemption). Your own scripts, own website, own chatbot, own marketing — legal. You are not a "broker" because you deal in your own property.
2. **Automating the transaction mechanics** (e-sign, showing scheduler, offer inbox, comps dashboard, disclosure checklists): fine for your own property; e-sign is governed by ESIGN/UETA and state closing requirements, not licensing.
3. **Selling the automation as a repeatable service to other sellers** (SaaS "auto-list + auto-respond + negotiate" product): the moment you (unlicensed) handle third-party sellers' inquiries-for-compensation, negotiate, or list on their behalf, you are likely doing **unlicensed brokerage** in most states. The lawful shape is: (a) a licensed broker entity does the licensed acts (your "broker partner of record" on every transaction — this is exactly the flat-fee model's structure), or (b) you sell pure software that the *owner* operates (the owner keeps all decision authority; your tool doesn't "negotiate"). This is why every serious AI-seller startup (Ridley, Opendoor, etc.) either employs licensed brokers or structures as an iBuyer/brokerage.
4. **MLS data + IDX**: no self-hosting path to MLS feeds without a licensed-entity agreement; MLS ToS prohibit scraping, and settlement rules prohibit repackaging MLS data into compensation platforms.

---

## 5. Cost breakdown: agent route vs DIY route, 2026, itemized

Reference home: **$425,000** (NAR 2025 agent-assisted median). Seller-side costs only; buyer's closing costs excluded. Commission data 2025–2026 (current); title/escrow ranges are standard market norms [SECONDARY — aggregate of HomeLight/Opendoor/industry sources; actuals vary ±50% by state].

| Item | Agent route (full service) | DIY route (FSBO + flat-fee MLS broker) | Source |
|---|---|---|---|
| Listing-side commission | 2.5–3% = **$10,625–$12,750** | **$0** (you keep it) | NAR 2025 Profile (agent norm); Clever 2026 |
| Buyer's-agent compensation (seller-offered, off-MLS post-settlement) | ~2.4–2.7% = **$10,200–$11,475** (or buyer pays own agent) | 0–2.5% = **$0–$10,625** (your choice; 1.5–2% typical to stay competitive) | Clever PR 6/17/25; Redfin Q1 2025; NAR settlement FAQ Q30–31 |
| Flat-fee MLS listing / limited-service broker | included | **$299–$1,500** (one-time; local MLS flat-fee varies) | Opendoor cost guide; HomeLight; CWMLS/Canopy (flat-fee broker required) |
| Professional photos + 3D/matterport tour | included | **$300–$800** (photos $200–500; virtual tour $150–500) | [SECONDARY] market norms, 2025 |
| Marketing (sign, flyers, paid ads) | included | **$200–$800** | [SECONDARY] Opendoor/HomeLight |
| Pricing (CMA/AVM research) | included | **$0–$100** (AVM free; paid CMA from another broker often free for sellers) | [SECONDARY] |
| Transaction/e-sign platform | included | **$0–$500** (DocuSign-class per-deal; title cos often include) | [SECONDARY] |
| Contract review / legal (non-attorney states) | included (agent review) | **$500–$2,500** one-time attorney review (more in attorney-closing states) | [SECONDARY] |
| Title insurance (owner's policy) + escrow/settlement | ~0.5–1.5% (state-dependent) = **$2,100–$6,400** (split/shifted by local custom) | Same: **$2,100–$6,400** (you cannot skip this) | [SECONDARY] 1–3% closing-cost norms |
| Transfer tax / recording | state-dependent | same | [SECONDARY] |
| **Total (commission-bearing path)** | **≈ $23,000–$30,600** (5.4–5.7% + closing) | | Clever 2026 (5.70%); NAR |
| **Total (DIY, offering 2% buyer comp)** | | **≈ $12,000–$19,500** ($650–$3,300 out-of-pocket + 2% buyer comp) | |
| **Gross savings, before price effect** | | **≈ $11,000–$18,000** | |
| **Expected price effect** | baseline | NAR-observed median FSBO discount ≈ 18% ≈ **−$63,750** (Jul'24–Jun'25 window; possibly stale for 2026, direction stable) | NAR 2025 Profile |
| **Net expected value of DIY** | | **≈ −$45k to −$53k vs agent route** if the median gap materializes | |

**The decision rule:** the DIY route wins only if your home sells within ~10% of the comparable agent-assisted price (high-demand market, distinctive property, cash-likely buyer pool) — i.e., exactly the homes where an automation stack (own site, chat inbox, showing scheduler, e-sign, comps script) is feasible to run. On a median home in a median market, the commission savings are noise against the price gap. The **flat-fee MLS listing ($500–$1,500) is the highest-leverage single purchase** in the DIY column: it buys back the full buyer-broker pool (IDX syndication) without a 3% fee.

---

## Source appendix (primary first)

1. Final Judgment, Burnett v. NAR, 4:19-cv-00332-SRB (W.D. Mo.), Doc. 1673, Jan 15 2025 — https://www.mow.uscourts.gov/sites/mow/files/ca/19-cv-332-1673FinalJudgment-NAR.pdf
2. NAR Settlement Agreement (executed 3/15/2024) — https://blocksandlots.com/wp-content/uploads/2024/03/Realtors-NAR-Settlement-EXECUTED.pdf
3. NAR Settlement FAQs (4/19/2024 & 5/5/2024) — https://www.nar.realtor/sites/default/files/documents/nar-settlement-faq-2024-05-05.pdf
4. NAR 2025 Profile of Home Buyers & Sellers (highlights, 11/4/2025) — https://www.nar.realtor/sites/default/files/2025-11/2025-profile-of-home-buyers-and-sellers-highlights-11-04-2025.pdf
5. NAR "FSBOs Reach All-Time Low" — https://www.nar.realtor/news/real-estate-news/fsbos-reach-all-time-low-more-sellers-rely-on-agents
6. CA DRE Licensee Advisory (12/12/2024, amended) — https://dre.ca.gov/Licensees/Advisories/Advisory_2024_11_14_Changes_to_Buyer_Representation.html
7. Fed FEDS Note "Commissions and Omissions" (5/12/2025) — https://www.federalreserve.gov/econres/notes/feds-notes/commissions-and-omissions-trends-in-real-estate-broker-compensation-20250512.html
8. FCC 24-17 Declaratory Ruling (AI voice / TCPA, 2/2/2024) — https://www.dwt.com/-/media/files/2024/02/fcc2417a1.pdf
9. CWMLS MINI Handbook (rules through 4/15/2025) — https://www.cwbr.org/clientuploads/PDFs/CWMLS/CWMLS_MINI.pdf
10. Canopy MLS Limited-Service Listings — https://support.canopymls.com/kb/article/76-limited-service-listings/
11. Realtor.com Terms of Use — https://www.realtor.com/terms-of-use/
12. FTC CAN-SPAM compliance guide + 16 CFR Part 316 — https://www.ftc.gov/business-guidance/resources/can-spam-act-compliance-guide-business ; https://www.govinfo.gov/content/pkg/CFR-2025-title16-vol1/pdf/CFR-2025-title16-vol1-part316.pdf
13. Texas 22 TAC § 535.4 + TREC unlicensed assistants — https://www.law.cornell.edu/regulations/texas/22-Tex-Admin-Code-SS-535-4 ; https://www.trec.texas.gov/article/use-unlicensed-assistants-real-estate-transactions
14. Arkansas Real Estate License Law — https://arec.arkansas.gov/wp-content/uploads/AR-Real-Estate-License-Law-July-2022-Final.pdf
15. Indiana HB 1068 (unlicensed solicitors, eff. 7/1/2024) — https://iga.in.gov/pdf-documents/123/2024/house/bills/HB1068/HB1068.05.ENRS.pdf
16. Realcomp v. FTC (2009/2011) — https://www.ftc.gov/sites/default/files/documents/cases/2009-11-091102realcompopinion.pdf
17. Clever commission surveys (6/17/2025 PR; 2026 updated 8/20/2026) — https://www.prnewswire.com/news-releases/agent-commissions-edge-higher-in-2025-one-year-after-landmark-nar-settlement-302483289.html ; https://listwithclever.com/real-estate-blog/6-percent-real-estate-commission-explained/
18. Redfin buyer-commission reports (Q4 2024 / Q1 2025) — https://www.housingwire.com/articles/redfin-buyers-agent-commissions-largely-unchanged-after-nar-settlement/
19. [SECONDARY] AP on HomeServices $250M settlement — https://apnews.com/article/real-estate-commission-lawsuit-homeservices-warren-buffett-f933f5997d8e1e1d90549c00af84493e
20. [SECONDARY] Opendoor & HomeLight FSBO cost guides (commercial bias noted) — https://www.opendoor.com/articles/is-for-sale-by-owner-worth-it ; https://www.homelight.com/blog/how-much-does-it-cost-to-sell-house-by-owner/
21. [SECONDARY] Zillow ToS scraping prohibition (live page bot-blocked at fetch time; verify in browser) — https://zillowscraper.com/is-it-legal-to-scrape-data-from-zillow/
