# Home-Sale Tooling — Slice 3: Marketing & Media Automation

Audience lens: experienced dev running a self-hosted homelab. Focus: real APIs/webhooks, self-hostable/open-source options, total cost, privacy/data control, what is actually scriptable.
Research date: 2026-09-04. Sources cited inline; `[SECONDARY]` marks claims only verifiable via non-official sources. Pricing in USD.

---

## 1. Virtual Staging

| Option | Cost | Turnaround | Quality | Developer hooks |
|---|---|---|---|---|
| **Virtuance** (human + AI hybrid, national photography service) | Bundled per-listing; e.g. "Virtual Tour Essentials" = 25 ground images + 1 Matterport tour; individual images $6/image after 2025 price cut (was $10) — https://support.virtuance.com/support/solutions/articles/26000057820 (2025, possibly stale) | 24–48h typical; paid rush delivers by 12:00 PM next day — https://www.virtuance.com/residential-real-estate/ | Marketing-grade, MLS-ready; human retouch, Blue Sky Guarantee | Web order portal + account dashboard; **no public API**. Scriptable only via browser automation. Rights: you get marketing usage rights, Virtuance retains copyright |
| **VirtualStaging.com** (human designers, per-image) | $24 flat/image regardless of rooms in photo — https://virtualstaging.com/blog/virtual-staging-cost-ultimate-guide/ (vendor blog; pricing may change) | Days, per vendor | High (hand-staged, photoreal) | Upload-and-download; no API mentioned |
| **Market baseline (human virtual staging)** | $25–$75/room typical 2026; full vacant home ~$200–$600; premium designer staging $100–$400/room — https://homecostlab.com/guides/home-staging-cost-guide/ [SECONDARY], https://currentcost.org/virtual-staging-cost-price-u-s-buyers/ [SECONDARY] | 1–5 days | Varies by vendor | None; email/portal workflows |
| **RoomGPT / AI HomeDesign** (consumer AI restyling) | RoomGPT credit packs: $9/30 credits, $19/100, $29/200, free tier 1 design — https://rightaichoice.com/tools/roomgpt [SECONDARY]. AI HomeDesign: $19/mo (30 photos ≈ $0.63/img), $29/mo (80 ≈ $0.36), $49/mo (200 ≈ $0.24) — https://aihomedesign.com/blog/head-to-head/roomgpt/ (vendor blog) | Seconds, unlimited-ish | Consumer-grade "what-if" previews, not MLS-ready; RoomGPT flagged as lacking bulk/MLS workflow — https://aiandrealtors.com/review-roomgpt [SECONDARY] | Web UI; no public API; no bulk queue |

**Key take:** for a single home you're selling, commercial human staging ($200–600) is the "buy" ceiling; AI SaaS ($0.24–3/img) is the "good enough" band; the credible "build" option is local SDXL (below).

### SaaS vs self-hosted — virtual staging
| | SaaS (AI: RoomGPT/AI HomeDesign) | SaaS (human: VirtualStaging.com et al.) | Self-hosted (SDXL + ControlNet) |
|---|---|---|---|
| Cost per home (6–10 rooms) | ~$5–30 | ~$150–600 | $0 marginal (electricity) |
| Quality vs MLS bar | Borderline; fine for listing photos, not luxury print | MLS-safe, guaranteed | Good-but-variable; needs tuning + QA pass |
| Scriptable? | No API | No API | Fully — CLI/GPU pipeline, batch, queueable |
| Privacy | Photos to vendor | Photos to vendor | Local only |
| Feasibility on 72GB GPU | n/a | n/a | **Practical**: SDXL/SD3 inpainting + depth/canny ControlNet runs at high batch rates. Research-grade repos: `mithunparab/virtual-staging` (modular SD+ControlNet+SAM+GroundingDINO pipeline, training recipes) — https://github.com/mithunparab/virtual-staging; `Trgtuan10/Interior-stable-difusion` (SD for interior styling/object swap) — https://github.com/Trgtuan10/Interior-stable-difusion; RoomDiffusion paper (industry-tuned interior diffusion, better aesthetic evals vs SDXL baselines) — https://arxiv.org/abs/2409.03198. **Honest note:** the repos are research/assembly-grade, not productized; expect 1–2 days to wire a "empty room photo in → staged photo out" pipeline, plus a SAM2 segmentation step for defurnishing (segment furniture mask → inpaint). No open-source model currently matches the commercial photorealism guarantee; a dev will ship a usable result, but should budget QA time |

---

## 2. 3D Tours / Virtual Tours

| Option | Cost | Turnaround | Quality | Developer hooks |
|---|---|---|---|---|
| **Matterport** (dominant player) | Subscription by "Active Spaces": Free (1 space); Starter 5–20 spaces; Professional 20–150 spaces — https://matterport.com/plans. Per-space prices on the official support price list: e.g. Professional 25 = $85, 30 = $99, 50 = $159, 150 = $429 (annual) — https://support.matterport.com/s/article/Matterport-Price-List (page is JS-rendered; figures via index, verify with sales). Third-party: "professional $55–309/mo + hardware" — https://www.thefuture3d.com/blog/matterport-pricing-guide-2026/ [SECONDARY]. Hardware: Pro3/Pro2/Pro1 cameras required for full features (Starter = limited camera support). Cloud capture services in 200+ cities (paid add-on) | 2–8h cloud processing per space [SECONDARY — thefuture3d.com]; floor plans 24h (Express 6h) on Professional | The benchmark: true 3D mesh, dollhouse view, auto floor plans, measurements, MLS embeds, Google Street View publishing | **API/SDK exists but Enterprise-tier** ("robust APIs/SDKs" listed only under Enterprise — https://matterport.com/plans). Free/Starter embeds are scriptable (iframe/URL). Data lives on Matterport cloud; no self-host |
| **Kuula** (360-photo tours, budget) | Free plan (up to 100 public tours, Kuula branding); paid ~$9.99–$36/mo — https://www.saasworthy.com/product/kuula-co [SECONDARY; official pricing page 404'd at research time] | Near-instant upload (photos, not LiDAR) | 360° photo tours with hotspots; **no** true 3D, no dollhouse, no measurements, no auto floor plans — https://www.thefuture3d.com/equipment/compare/matterport-vs-kuula/ [SECONDARY] | Web + mobile editor; **API available** per [SECONDARY] listings; works with any 360 camera/phone |
| **"Kuix"** | — | — | — | **Flag: not a 3D tour vendor.** kuix.com is a Budapest web/UI studio (kuix design s.r.o.) and its cert is expired; kuix.hu is a separate design studio. No "Kuix 3D" product surfaced in any reliable source. Treat this name as a non-option. |
| **Cupix** (Korean, 360 tours, Series A 2017) | Subscription, US HQ now Cedar Park TX — https://tracxn.com/d/companies/cupix [SECONDARY] | — | 360 photo tours, camera partners (Insta360, Ricoh Theta); construction/mapping focus more than residential | SaaS; integrations with Autodesk Construction Cloud, Revizto [SECONDARY] |
| **Epic RealityScan** (photogrammetry, capture tool not tour host) | **Free** for individuals and businesses <$1M/yr revenue; paid seats above — https://www.realityscan.com/api-ref/download. Mobile app free | Hours (desktop GPU: needs NVIDIA CUDA, 8GB+ VRAM on Linux — fits a 72GB setup easily) | High-fidelity textured meshes from phone photos; **not** a tour host — export GLB/OBJ and host yourself (e.g. Sketchfab). Mobile EULA: data may train Epic's models **by default, with opt-out** — privacy flag — https://aeco.digital/polycam-realityscan-photogrammetry/ [SECONDARY on EULA terms; verify in-app] | **CLI automation + masking docs exist** (documented in official tutorials) — this is the most scriptable commercial-ish capture tool |

### SaaS vs self-hosted — 3D tours
| | Matterport (SaaS) | Kuula/360 (SaaS) | Self-hosted |
|---|---|---|---|
| Cost per home | ~$99–159/yr for 30–50 spaces + camera (Pro3 hardware is a real capital cost, 4-figure [INFERENCE from "plus hardware" references; not verified on an official page]) | ~$0–432/yr, one home | $0 |
| Tour quality | Best-in-class spatial 3D | Good for 360 walkthrough only; weakest spatial fidelity | Depends on route (below) |
| MLS embeddable | Yes, first-class | Yes (hosted URL) | Yes if you serve it (see below) |
| Privacy | Cloud, Matterport | Cloud, Kuula | **Full local control** |
| Self-host route | Not available | Not available | Two viable paths: **(a) 360-panorama tour (production-grade, weekend project):** capture with any 360 camera/phone, serve with **Pannellum** (open-source WebGL 360 viewer) or a three.js viewer — fully scriptable, embed anywhere, zero per-tour cost. This is the pragmatic "sell my own house" answer. **(b) Gaussian splat / photogrammetry tour (research-adjacent):** COLMAP (BSD) for SfM + OpenSplat (AGPLv3) or `aman-24052001/SceneForge` (MIT wrapper, CPU-capable, self-contained HTML viewer, even an MCP server) — https://github.com/aman-24052001/SceneForge. Splat quality can beat 360 tours visually but indoor capture is hard (textureless floors/walls, motion blur); treat as 1–2 weeks of tuning, not a turnkey product. Meshroom (AliceVision, node-based, Apache-2.0) — https://github.com/alicevision/Meshroom — is mature photogrammetry to mesh but outputs models, not tours; you still need a viewer. **VRoom** (https://github.com/EzzCode/VRoom) is a full COLMAP+SAM+gSplat pipeline with a companion app — research-grade, heavy dependency surface |

**Honest feasibility verdict:** for one house, buy/rent a 360 camera (or use phone), capture, and either host on Kuula's free tier ($0, external dependency) or self-host Pannellum on the homelab (fully owned, ~1 day of work). Matterport is only worth it if the *buyer's* agents expect it as a market norm and you want floor plans/measurements embedded in MLS.

---

## 3. AI Photo Enhancement / Color Correction

| Option | Cost | Turnaround | Quality | Developer hooks |
|---|---|---|---|---|
| **Aftershoot** | Flat-fee, **no per-image fees**: AI Culling from $10/mo (annual), AI Editing from $30/mo, AI Retouching from $20/mo, full cull+edit+retouch $45/mo — https://aftershoot.com/start-your-free-trial/, https://account.aftershoot.com/pricing ($120/yr cull, $360/yr edit, $240/yr retouch) | Minutes per gallery, **runs offline on local Windows/macOS** | Trained on your style; strong for interiors/exterior real estate galleries; Lightroom Classic/CC integration | Desktop app (local processing, local file storage); exports to Lightroom/Bridge; not a web API — scriptable via Lightroom's own scripting/Lua bridge, not via Aftershoot's API |
| **Virtuance processing** (bundled with their shoots) | Included in image packages ($6/image à la carte) | With delivery | "HDReal" processing, Blue Sky Guarantee (sky replacement), twilight shots | Order portal only; no API |
| **DIY: Lightroom/ACR + manual presets** | $10–12/mo Adobe subscription [INFERENCE: standard Adobe pricing, not re-verified] | Manual | Full manual control, industry standard for RE photography | LR Classic has CLI-adjacent workflows (XMP sidecars, Lua); batchable; photos never leave your machine |

### SaaS vs self-hosted — photo enhancement
| | Aftershoot (SaaS, local runtime) | Self-hosted stack |
|---|---|---|
| Cost | $45/mo flat | $0 |
| Culling | AI, learns your style | **darktable** (GPL, fully open, CLI: `darktable-cli` runs import/export non-interactively) — usable for batch pipeline; "AI culling" per se not the strength (focal blur/similarity ranking exists but is basic). **Real-ESRGAN** (open source, GPU) for upscaling weak phone shots — very feasible on 72GB. HDR bracket merge: darktable/hugin CLI. |
| Verdict | The SaaS is actually *local software* — privacy is fine; cost is the only argument against. For a one-off home sale, a good Lightroom preset + a few hours beats any of these | Fully self-hostable and scriptable (darktable CLI + Real-ESRGAN in a cron/queue). Feasibility: **high** — no research-grade pieces, all production-grade open source. This is the easiest self-host win in the whole slice |

---

## 4. Drone / Aerial Photography

| Option | Cost (per listing, 2026) | Turnaround | Quality | Developer hooks |
|---|---|---|---|---|
| **Local Part 107 pilot, aerial stills (10–15 edited)** | $100–$250; median ~$225 bundled with interior shoot — https://www.amplifiles.ai/blog/real-estate-drone-photography-pricing [SECONDARY, vendor blog], corroborated by https://rotorrate.com/blog/how-much-do-real-estate-agents-pay-for-drone-footage [SECONDARY] | Same/next day | Good; 8–15 edited stills + MLS licensing typical | **None** — email/portal; deliverables as ZIP. No API, no webhook; you get files |
| **Local pilot, stills + 60–90s video** | $300–$600 | 1–3 days (video edit 2–4h labor) | Cinematic; the current listing-marketing norm | None |
| **DIY with own drone** | ~$0 marginal after hardware (DJI Mini 4 Pro / Air 3, $500–$1,200) + FAA Part 107 cert cost (~$150 exam [INFERENCE: standard FAA pricing, not re-verified]) | Immediate | You own the pipeline: DJI Pilot 2 app, no API for photos (SD card). Scriptable part: post-processing — batch EXIF-sort, upscaling, sky enhancement | Full ownership, but: airspace authorization (LAANC app API actually **does** exist — https://developer.flylaac.com — the only real API in this category, and it's about flight authorization, not images) |

### SaaS vs self-hosted — drone
| | Local pilot service | Own drone + self-processed |
|---|---|---|
| Cost per home | $150–$600 | $0 marginal (+ cert/hardware amortized) |
| Time | 0h (their problem) | ~2–4h: fly + process |
| Data control | Files handoff only | Full |
| Verdict | For one sale, **hire** — a Part 107 pilot's insurance + LAANC process is the real cost, and a crashed drone over your own roof isn't worth DIY for a single shoot. Own-drone only pays off if you shoot multiple properties (neighbors, rentals, repeat listings) |

---

## 5. Open-House / Inquiry Capture

| Option | Cost | Turnaround | Quality/notes | Developer hooks |
|---|---|---|---|---|
| **Ylopo Open House Tool** | Included in Ylopo Suite; Ylopo pricing is custom/quote-only (scales with market + database size; demo-gated) — https://www.ylopo.com/pricing, https://www.ylopo.com/open-house-tool | Instant (branded page at you.com/open-house + QR) | QR touchless sign-in, auto CRM push, tags leads "Open House (Ylopo)", drip campaigns | CRM integrations "with major systems" — but the whole platform is a walled garden; you're renting lead-nurture infra you don't need for one house |
| **Open House App** (openhousesheet.com) | **$0 free plan**: unlimited sign-ins/leads, CSV export, 2 free AI staging images; paid tiers add AI features — https://openhousesheet.com/ | Instant | Web sign-in (no download), branded QR for yard sign/flyers; data "in the browser by default"; they claim they don't sell leads | **CSV export only** — no API. Developer path: CSV → your own pipeline (Airtable/Typeform/DuckDB). Fine for one open house |
| **Curb Hero Open House App** | Free for solo agents — https://curbhe.ro/ | Instant | Offline-capable QR sign-in (works w/o internet — nice for rural), "6000+ CRMs via Zapier/direct" | Zapier = the only real automation surface; no public API claimed |
| **EstatePass / generic form tools** | Free — https://www.estatepass.ai/tools/open-house-signin/ | Instant | QR-linked digital form + print PDF; CSV export | No API |

**The developer answer is boring and correct: skip all of it for a single home sale.** Run a self-hosted form (below), print one QR code to a yard-sign insert, and point it at `your-homelab.example/open-house`. Every lead lands in a table you own. No SaaS in this category is worth it for a one-off.

### SaaS vs self-hosted — open house capture
| | SaaS (Open House App / Curb Hero) | Self-hosted |
|---|---|---|
| Cost | $0–free tier | $0 |
| Lead data ownership | Their DB (export via CSV) | **Yours, from the first row** |
| Scriptability | CSV/Zapier | Full: API, webhooks, SQL, offline-tolerant |
| Recommended self-host | — | **Formbricks** (AGPLv3, community edition = free, unlimited surveys/users, **full API + webhooks included in the open-source core**, Docker one-click, min 1 vCPU/2GB — https://formbricks.com/pricing, https://formbricks.mintlify.dev/docs/self-hosting/overview, https://github.com/formbricks/formbricks). Build one survey (name, email, phone, "what did you think", qualification questions), QR code to the hosted URL, response webhooks → your CRM/SQLite. Enterprise edition (SSO, white-label) is paid; you don't need it. Runner-up if you want lighter weight: plain **NocoBase/SeaTable form** or a 50-line FastAPI form writing to SQLite — genuinely overkill to install anything |

---

## 6. LLM-Generated Listing Descriptions

| Option | Cost | Turnaround | Quality | Developer hooks |
|---|---|---|---|---|
| **ListingAI** | Free; Essential $19/mo; Professional $36/mo (annual: $17/$32.50); Expert $150/mo — https://www.listingai.co/pricing | Seconds | Auto-pulls property facts from public records, configurable model/length/style, Fair Housing compliance flagging, 50+ languages, saved brand rules; MLS/luxury/short formats | Productized for agents; **no public API** found in the docs I could verify — it's a web app. Bulk generation is a Pro-tier feature [INFERENCE: from feature descriptions] |
| **AgentListingAI** | **Free** (no subscription) — https://agentlistingai.com/ | ~30–45s | Property-persona + voice-dictated story → full kit (MLS/social/email copy, open-house scripts, QR codes); Fair Housing checker (self-described, not a legal guarantee) | Web app; output is copy-paste text |
| **Montaic MLS generator** | Inside Montaic agent platform [SECONDARY — https://montaic.com/tools/mls-description-generator, pricing not on the tool page] | ~30s | Voice-matched: trains on 2–3 of your past listings for style | SaaS inside a CRM |
| **Generic LLM + property data (the real developer answer)** | $0 (local LLM) or a few $/mo hosted | Seconds | With structured input (beds, baths, sqft, year built, lot, features, comps) a mid-tier LLM beats the $19/mo tools on specificity and can be prompted for Fair-Housing-safe language | **Fully scriptable** |

**How it's typically done (productized vendors):** address → pull public-record/MLS fields → template + LLM with style/compliance constraints → human review → paste. There is no secret sauce in the paid tools worth paying for on a single listing.

### SaaS vs self-hosted — listing copy
| | SaaS (ListingAI et al.) | Self-hosted |
|---|---|---|
| Cost | $0–36/mo | $0 |
| Privacy | Address + property details to vendor | Local |
| Scriptability | None meaningful | **This is the clearest self-host win of the slice.** 72GB GPU → run a strong quantized LLM via llama.cpp/vLLM (70B-class at Q4–Q6, or a fast MoE), feed it structured facts you scrape from the county assessor API / your own notes / the MLS printout, prompt with Fair Housing constraints (no protected-class references), and you get a listing description, social post, open-house script, and email blast from one JSON. One afternoon's work, zero recurring cost, fully ownable |
| Verdict | Only use the free tiers as *competitor prompts* to calibrate your local output | **Do it.** Pair with slice-5's form webhook for the whole "listing content → open house → leads" loop on one box |

---

## 7. Bottom Line (one-home-sale build/buy matrix)

| Category | Buy (one-off, ~1 house) | Build (self-host) |
|---|---|---|
| Virtual staging | AI SaaS, ~$10–30 for the whole house (AI HomeDesign tier or RoomGPT credits) — or skip | SDXL + depth/canny ControlNet + SAM2 defurnish pipeline; practical but research-grade repos (mithunparab/virtual-staging, Interior-stable-difusion). Build only if you enjoy it |
| 3D tour | Capture once (phone 360 or a rental), host on Kuula free tier, **or** self-host Pannellum | Pannellum = production-grade, ~1 day. Gaussian splat (SceneForge/OpenSplat) = cool, research-grade, 1–2 weeks |
| Photo enhancement | DIY Lightroom presets + a few hours (cheapest and best quality) | darktable CLI + Real-ESRGAN batch pipeline — trivially scriptable |
| Drone | Hire a Part 107 pilot, $150–450 (stills + short video) | Own drone only for repeat shooting; LAANC is the only API in this space |
| Open-house capture | Nothing (one event) | **Formbricks** (AGPLv3, free, full API + webhooks in core) + QR on a yard-sign card |
| Listing copy | Free tiers only | **Local LLM via vLLM/llama.cpp on the 72GB box + county-assessor structured data** — the highest-leverage build in this slice |

**Privacy ranking (best→worst data control):** self-hosted form + local LLM + darktable (fully local) < RealityScan (opt-out of model-training EULA on mobile) < free-tier SaaS (Open House App, Kuula, ListingAI-free) < Matterport/Virtuance/Aftershoot (photos or spaces on vendor cloud; Aftershoot is the exception — it runs on your desktop) < Ylopo (quote-gated, platform lock-in).

**Recency flags:** Matterport per-space numbers from the JS-rendered support price list (verify with sales before committing); Virtuance package structure from 2025 announcements (possibly stale for 2026 market-specific pricing); Kuula pricing from SaaSworthy (official page 404'd); drone pricing from 2026 vendor blogs (secondary but mutually consistent).
