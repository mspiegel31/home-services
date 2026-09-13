# Workout tools for software developers

**Scope.** Survey of available strength-training tools (2026), weighted by what matters to a developer: program-as-code, data ownership, API/scriptability, self-hosting on our Portainer fleet, and CLI/TUI ergonomics. Researched 2026-09-04 from primary sources (vendor docs, GitHub repos, app store listings) plus recent comparison roundups. Not a general "best fitness app" list — commercial consumer apps are covered only to the extent they interoperate with developer workflows.

## TL;DR

| Pick | Tool | Why |
|---|---|---|
| Overall for a coder | **Liftosaur** | Programs written as text files (Liftoscript), open-source PWA core, REST API, official MCP server, 4.9★ |
| Self-hosted / data ownership | **wger** (mature) or **openGym** (lighter) | Docker Compose, REST API, AGPL; wger has 10 yrs + Flutter/iOS clients, openGym is a single container with passkey sync |
| Terminal purist | **spotr** (Go) | Keyboard-first TUI, local SQLite, Homebrew install, zero account |
| Want the algorithm to coach | **JuggernautAI** (powerlifting) or **Fitbod** (general) | Expert-system / ML programming; weakest data portability |
| Homelab-native pattern | Any of the above + LLM | gymcoach, Claude4Garmin, and the Liftosaur MCP show the emerging "BYO-LLM over your training data" pattern |

---

## Category 1: Program-as-code — Liftosaur (top pick)

The only serious tool explicitly designed for developers (tagline: "weightlifting tracker app for coders").

- **Core model.** A *program* is a plain-text file in **Liftoscript**: exercises by week/day, sets × reps × weight, and progression rules (`lp(5lb)` = linear progression, double progression, custom scripts manipulating weight/reps/RPE/rest even myo-reps and drop sets). The app auto-advances the program after each workout. Built-in programs (5/3/1, GZCLP variants, Texas Method, Starting Strength, PPL, Arnold's Golden Six — 18+ listed, "50+" on the site) are all written in the same language, so "follow a proven program" and "write your own" are the same workflow.
- **Developer surface.**
  - Open-source PWA core: [`astashov/liftosaur`](https://github.com/astashov/liftosaur) (TWA).
  - **REST API** (`https://www.liftosaur.com/api/v1`): CRUD on programs (stored as Liftoscript text, `POST /programs` validates syntax and returns line-numbered `422`), full workout history in a compact human-readable text format, `/playground` endpoint to *simulate* a workout/progression without saving, program stats (weekly volume by muscle, est. duration), measurements, per-exercise config (1RM, rounding, equipment overrides). Auth: Bearer key `lftsk_…` from Settings. **Requires the premium subscription.** ([docs](https://www.liftosaur.com/doc/api))
  - **Official MCP server** — log workouts, look up exercises, generate programs via an LLM agent (already mounted as an MCP device in this session; endpoints cover programs, history, measurements, gyms/equipment, playground simulation).
- **Tracker features.** Set logging with rest timers, plate calculator against your actual bar/plate inventory, 1RM % and RPE-based loading, body-measurement time series, prescribed-vs-actual weekly volume graphs, cloud sync across iOS/Android/web.
- **Pricing (US App Store).** Free tier; premium $4.99/mo, $39.99/yr, ~$99.99 lifetime. (Other regional stores show lower prices, e.g. $19.99–31.99 lifetime.)
- **Weaknesses.** No Apple Watch app; occasional save/setup quirks; the Liftoscript learning curve is the price of the flexibility; the API is paywalled.

## Category 2: Self-hosted / data-owns-you

Relevant to this homelab (Portainer CE, ZFS config mount at `/mnt/tank/container-configs/<APP>`).

| Project | Stack | Notes |
|---|---|---|
| [`wger`](https://github.com/wger-project/wger) (6.8k★, AGPL-3.0) | Python/Django, Postgres, `docker compose up` | The mature option: custom routines with **automatic weight-progression rules**, nutrition (Open Food Facts), body weight, progress gallery, multi-user/gym mode, full REST API, Flutter Android + iOS + F-Droid clients. ~10 years of development. UI is the compromise. |
| [`openGym`](https://github.com/DuarteSantos8/openGym) (AGPL-3.0) | Docker Compose, data in `./data` | Newer, smaller, better UX: body-weight tracking with goal line, routines, guided workouts, rest timers, PR detection, 1,324-exercise library, passkey multi-device sync, Capacitor mobile app, browser-only demo. |
| [`Trajectory`](https://github.com/jumpingmushroom/Trajectory) | Docker, SQLite, offline-first PWA | **Equipment-first**: you model the machines/racks your actual gym has and log sets against *your* equipment rather than a generic catalog. Auto session boundaries, per-equipment top-set tracking, CSV export, multi-user. |
| [`gymcoach`](https://github.com/Julien-Au/gymcoach) | Postgres, self-hosted | Workout tracker with an **integrated AI coach, BYO-LLM** (Claude or any OpenRouter-compatible endpoint). No subscription, no rate limits. The clearest example of the "LLM over your training data" pattern. |
| [`onerep`](https://github.com/an2tha/onerep) | Self-hosted "fitness OS" | Training + nutrition + recovery + AI coach, PWA/Capacitor. Broad but young. |
| Smaller | [`lyftr`](https://github.com/cawlumm/lyftr), [`forge`](https://github.com/bndct-devops/forge), [`ASAP`](https://github.com/asap-open/ASAP), [`FitnessTrack`](https://github.com/Gman0909/FitnessTrack) | Single-file/SQLite loggers, progressive-overload algorithms; fine for personal logging, thin APIs. |

**Fit for this stack.** All of the above are one `docker compose` away on an existing Portainer CE host; media-app rules don't apply (no `/mnt/tank` requirement), but configs would conventionally land under the same mount. wger is the safe, battle-tested pick; openGym if you want minimal surface area; Trajectory if you want the data model to match the physical gym.

## Category 3: CLI / TUI

For logging from the terminal (or SSHing to the box at the gym):

- [`spotr`](https://github.com/yokanater/spotr) — Go, keyboard-first TUI, **local SQLite**, no account, offline. Start (`s`), log exercise (`l`), templates (`t`), command mode (`:`). Homebrew, Go install, or prebuilt binaries (macOS/Linux/Windows). The most polished of the bunch.
- [`lift`](https://github.com/parkerdgabel/lift) — Python (Typer/Rich/DuckDB/Plotext). Interactive set logging with shortcuts (`185 10`, `+5`), RPE/tempo, terminal charts, history/analytics commands.
- [`workout-cli`](https://github.com/gricha/workout-cli), [`lazaro`](https://github.com/misterclayt0n/lazaro), [`repcli`](https://github.com/bcutrell/repcli), [`fitlog`](https://github.com/Jay-Karia/fitlog) — lighter loggers, SQLite backends.
- [`git-fit`](https://github.com/paolopedrigal/git-fit) — web shell with the "git for workouts" metaphor (`fit add` / `fit commit -m` / `fit log --week`). Novelty > utility, but the onboarding for programmers is the best of anything here.
- [`hevycli`](https://github.com/obay/hevycli) — CLI *over the Hevy platform*: full CRUD on workouts/routines/exercises, JSON/table/plain output, interactive TUI sessions, explicitly "AI-agent ready" structured outputs. Notable because **Hevy itself has no official public API** — this rides the unofficial one.

## Category 4: Commercial mainstream (consumer-grade)

| App | Price (2026) | Character | Data portability |
|---|---|---|---|
| **Strong** | ~$4.99/mo, ~$99.99 lifetime | Fastest minimalist barbell logger; *no* built-in programs or progression logic | Clean CSV export; de-facto migration standard (Hevy imports Strong CSV) |
| **Hevy** | ~$2.99/mo, ~$74.99 lifetime | Best free tier; social feed/community; Apple Watch; 400+ exercises | Free CSV export (14-col per-set rows incl. `superset_id`, `rpe`); unofficial API via the `hevy` Rust crate / `hevycli` |
| **JEFIT** | ~$12.99/mo | Deepest analytics, 1,400+ exercise library with videos; plans are day-lists, not real programming | Export only |
| **Fitbod** | $95.99/yr or $15.99/mo | Algorithmic programmer trained on 400M+ logged workouts: recovery heat map, theoretical 1RM, modified Prilepin volume targets, dynamic set/rep/weight adjustment. Closest to "hands-off" | Closed |
| **JuggernautAI** | $34.99/mo, $349.99/yr | Expert-system AI from Juggernaut Training Systems (Chad Wesley Smith): individualized powerlifting/powerbuilding, daily readiness + RPE/RIR feedback drives intra-week load changes, meet-date periodization | Closed; no export |
| **TRAINER (Element 26)** | $14.99/mo, $119.99/yr | DPT/CSCS-engineered plan generation in ~2 min; Pro Builder + desktop portal for overrides | Closed |
| **Caliber** | freemium → paid coaching | Real credentialed human coaches writing/updating your program + free tier with hybrid AI | Closed |
| **SteelRep** | freemium | Program-first: 20 built-in structured programs with progression/deload/periodization rules | — |
| **Ladder** | from $29.99/mo | Home-gym oriented | — |

Takeaways for a developer: the consumer apps are excellent loggers but **closed data stores** (Strong/Hevy are the exceptions, via CSV or unofficial APIs). None offer an API you can build on; Fitbod/JuggernautAI hide their programming logic behind the subscription entirely. If you choose one, choose for UX and accept CSV-export as your escape hatch.

## Category 5: AI × developer patterns (the 2026 trend)

- **Liftosaur MCP** — LLM agents create/simulate programs in Liftoscript against the playground endpoint; programs-as-text means the LLM's output is reviewable in git. This is why it's the best base for an agentic setup.
- [`gymcoach`](https://github.com/Julien-Au/gymcoach) — self-hosted tracker + BYO-LLM coach, no rate limits.
- [`Claude4Garmin`](https://github.com/duvalcyril/Claude4Garmin) — pattern worth stealing regardless of tracker: pull real data (Garmin here), feed an LLM with full context, chat. Translates to any tracker with an API (wger, Liftosaur, Hevy).
- [`FitAI`](https://github.com/x2oreo/FitAI) + [`FitAI-api`](https://github.com/x2oreo/FitAI-api) — the only thing explicitly "for developers": mobile app + AI plan API + **VS Code extension** surfacing health guidance in the coding flow. Young project, MIT, Firebase backend.
- [`fitness-agent`](https://github.com/marcin-codes/fitness-agent) — evidence-based AI advisor for progressive-overload training.
- **Workout Chat** (`workout.chat/api_docs`) — REST API (OAuth 2.1) **and MCP server** for workouts/exercises/injuries/goals; the strongest example of a consumer product with first-party dev surface beyond Liftosaur.
- Corporate-gym side: EGYM Data Hub and Vitruve expose enterprise S2S APIs if a gym membership is in play (not applicable here).

## Recommendation for this environment

1. **Primary tracker: Liftosaur** (premium, ~$40/yr). Programs live in a text DSL (versionable, LLM-draftable), the API + MCP server turn the gym into a scriptable system, and it's already wired into this session's MCP stack. Lifetime if it survives 2 months.
2. **If data-ownership wins: self-host wger** as a Portainer CE stack (Postgres + app + Celery; config under the standard ZFS mount). Mature, REST API, mobile clients. openGym if wger's UI is too much.
3. **CLI fallback: spotr** — for "I want to log in 30 seconds from the terminal" days; local SQLite means zero infrastructure.
4. **Skip:** the $35/mo AI-coach apps unless the goal is competitive powerlifting (JuggernautAI is genuinely good at that specific job) — the closed store + high price is the wrong trade for a developer who can do better with an LLM over open data.

## Primary sources

- Liftosaur: [site](https://www.liftosaur.com/) · [REST API docs](https://www.liftosaur.com/doc/api) · [Liftoscript docs](https://www.liftosaur.com/doc/liftoscript) · [GitHub: astashov/liftosaur](https://github.com/astashov/liftosaur) · [App Store listing & pricing](https://apps.apple.com/us/app/liftosaur-scriptable-workouts/id1661880849) · reviews via App Store/Play
- wger: [GitHub](https://github.com/wger-project/wger) · [docs](https://wger.readthedocs.io) · live demo wger.de
- openGym: [GitHub](https://github.com/DuarteSantos8/openGym) · Trajectory: [GitHub](https://github.com/jumpingmushroom/Trajectory) · gymcoach: [GitHub](https://github.com/Julien-Au/gymcoach) · onerep: [GitHub](https://github.com/an2tha/onerep)
- CLI: [spotr](https://github.com/yokanater/spotr) · [lift](https://github.com/parkerdgabel/lift) · [hevycli](https://github.com/obay/hevycli) · [hevy Rust crate](https://docs.rs/hevy/latest/hevy/index.html) · [git-fit](https://github.com/paolopedrigal/git-fit)
- Commercial: Fitbod [algorithm Q&A](https://help.fitbod.me/hc/en-us/articles/16254175592215-Fitbod-s-Algorithm-Q-A) + [pricing](https://fitbod.zendesk.com/hc/en-us/articles/360004404714) · JuggernautAI [pricing](https://www.juggernautai.app/pricing) + [GGreviews review](https://www.garagegymreviews.com/juggernautai-review) · Element 26 [site](https://element26.app/) + App Store · Strong strong.app + [CSV export via Hevy help](https://help.hevyapp.com/hc/en-us/articles/38001424401943) · Hevy [export guide](https://thetaperapp.com/articles/how-to-export-hevy-data/) · roundups: [BarBend 2026](https://barbend.com/best-weightlifting-apps/), [SensAI comparison](https://www.sensai.fit/blog/hevy-vs-strong-vs-fitbod-vs-jefit), [SteelRep 2026](https://steelrep.app/blog/best-workout-apps-strength-training/)
- AI/dev patterns: [Workout Chat API & MCP](https://workout.chat/api_docs) · [FitAI](https://github.com/x2oreo/FitAI) · [Claude4Garmin](https://github.com/duvalcyril/Claude4Garmin) · [fitness-agent](https://github.com/marcin-codes/fitness-agent) · [EGYM Data Hub](https://developer.egym.com/data-hub)
