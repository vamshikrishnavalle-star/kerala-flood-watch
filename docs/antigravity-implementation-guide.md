# Implementation Guide: Building the Disaster Prediction System in Google Antigravity

**Project:** AI-Powered Disaster Prediction and Emergency Response System (PRD v1.1) **Stack:** Python 3.11, FastAPI, SQLite, scikit-learn, XGBoost, SHAP, Leaflet, Chart.js **Timeline:** 12 weeks | **Required hazard:** floods

> Antigravity is in active development, so menu names and defaults may differ slightly in your version. If a setting is not where this guide says, search the settings panel for its name.

---

## Part 1: How the Build Works

**Two views.** The **Agent Manager** is where you give tasks to agents and monitor them. The **Editor** is where you read and fix code. You will switch between them constantly.

**Two modes.** Use **Planning mode** for anything that touches several files (almost every phase below). The agent produces a task list and implementation plan before coding. Use **Fast mode** only for small fixes such as renaming or a one-line bug.

**Artifacts.** Agents produce reviewable artifacts: task lists, implementation plans, walkthroughs, and browser screenshots or recordings. You can comment on an artifact to steer the agent before it writes code. Always read the plan before approving.

**Rules and Workflows.** *Rules* are standing instructions the agent follows in every task. *Workflows* are saved prompts you trigger with `/`. Both live in your workspace (`.agent/rules/` and `.agent/workflows/`). Part 3 gives you ready-made files.

**What you do vs what the agent does**

| You | The agent |
| --- | --- |
| Choose region, zones, and flood label definition | Writes ingestion, features, training, API, dashboard, tests |
| Download or approve datasets | Runs code and fixes errors |
| Judge whether metrics are believable | Produces plans, walkthroughs, screenshots |
| Review every plan and diff; commit | Refactors on request |
| Keep API keys private | Never sees your real keys if you keep them in `.env` |

An agent can make code run. It cannot tell you whether your flood labels are scientifically sound. That judgment stays with you.

---

## Part 2: Setup (Day 1)

### Step 2.1: Install and sign in

1. Download Antigravity from Google's official page and install it for your OS.
2. Sign in with your Google account. It is offered in preview for personal accounts in approved regions.
3. Complete the setup wizard.

### Step 2.2: Recommended settings

- **Development mode:** Agent-assisted (balanced). Avoid the maximum-autonomy preset until you trust the workflow.
- **Review policy:** "Agent Decides" so it checkpoints on important steps. Never "Always Proceed" for this project.
- **Terminal policy:** require approval for commands. Add a **deny list**: `rm -rf`, `sudo`, `git push --force`, `curl | sh`.
- **Secure Mode:** optional. It forces review of every action, which is slow but safe.
- Open the agent panel with `Cmd+L` (Mac) or `Ctrl+L` (Windows/Linux).

### Step 2.3: Install tools yourself

- Python 3.11+, Git, and (optional) Chrome so the browser sub-agent can test your dashboard. Antigravity may prompt you to install a browser extension; allow it for this workspace only.

### Step 2.4: Accounts and keys

| Item | Needed? | Notes |
| --- | --- | --- |
| Open-Meteo | No key | Free forecast and historical weather |
| NASA POWER | No key | Free historical meteorology |
| Telegram bot token | Yes, for alerts | Create via BotFather |
| LLM API key | Optional (advisories) | Claude or Gemini; the code must work without it |

Keys go in a `.env` file, never in prompts or code.

### Step 2.5: Decisions to make before Phase 1

| Decision | Recommendation |
| --- | --- |
| Region | One flood-prone state or river basin with good records (e.g., Kerala, Assam, Bihar, Chennai area) |
| Zones | 5 to 10 districts or grid cells (keep it small) |
| Flood label | River gauge above danger level, or a recorded flood event for that district and date |
| Alert channel | Telegram (free) |
| Advisory language | English plus one regional language |

---

## Part 3: Bootstrap the Workspace (Day 1 to 2)

### Step 3.1: Create the folder and repo

```
mkdir disaster-ai && cd disaster-ai
git init
mkdir docs data scripts src web tests notebooks
mkdir -p .agent/rules .agent/workflows
```

Save the PRD v1.1 as `docs/PRD.md`. Add a `.gitignore` containing: `.env`, `data/`, `__pycache__/`, `.venv/`, `*.joblib`, `*.db`. Open the folder as a workspace in Antigravity.

### Step 3.2: Rule file

Create `.agent/rules/project-rules.md`:

```markdown
# Project Rules: Disaster Prediction System
Follow docs/PRD.md (v1.1). Flood is the only required hazard.

## Stack (do not add dependencies without asking)
Python 3.11, FastAPI, SQLAlchemy + SQLite, APScheduler, scikit-learn,
XGBoost, SHAP, joblib. Dashboard: static HTML + vanilla JS, Leaflet,
Chart.js. No Node, no build step.

## Working rules
- Always write an implementation plan first. Keep changes small: one feature per task.
- After every task, run `pytest` and report results honestly.
- Never edit a test just to make it pass. If a test must change, say why.
- Never invent or fabricate data, metrics, or API responses. If data is
  missing, stop and ask.
- Use chronological train/validation/test splits only. Never tune on the test set.
- Training and inference must share one saved feature pipeline (with a test).
- Always report precision, recall, F1, ROC-AUC, PR-AUC, Brier score, and
  false-alarm rate. Never accuracy alone. Flag suspiciously high scores (ROC-AUC > 0.98) as possible leakage.
- The LLM only rephrases model output into advisories. It never decides risk.
  Every LLM call needs a template fallback and error handling.
- Secrets live in `.env`. Never print or commit them.
- Predictions support human decisions: UI shows confidence and a disclaimer.
- Prefer simple, commented code over clever code.
```

### Step 3.3: Workflows

Create these four files in `.agent/workflows/`. Trigger each with `/` in the agent panel.

**`run-checks.md`**

```markdown
Run `pytest -q`. Summarize failures with file and cause. Do not change tests
or code unless I ask. End with a pass/fail count.
```

**`new-feature.md`**

```markdown
Read docs/PRD.md and the project rules. Write a short plan for the feature I
describe, list files you will touch, then implement it with tests. Finish with
a walkthrough: what changed, how to run it, what to verify.
```

**`report-metrics.md`**

```markdown
Run the evaluation script. Print a table of precision, recall, F1, ROC-AUC,
PR-AUC, Brier score, and false-alarm rate for every model on the test set.
Flag any sign of data leakage and explain what you checked.
```

**`commit-phase.md`**

```markdown
Run `git status`. Summarize changes in plain language. Stage tracked source
files only (no data, keys, or models), and commit with the message
"phase <N>: <summary>". Do not push.
```

### Step 3.4: Environment files

Create `.env.example` (commit this one) and copy to `.env` (never commit):

```
REGION_NAME=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
ADVISORY_PROVIDER=template   # template | claude | gemini
ADVISORY_API_KEY=
ALERT_THRESHOLD=0.7
ALERT_CONSECUTIVE_READINGS=3
```

---

## Part 4: The Build, Phase by Phase

**Routine for every phase:** (1) open a **new conversation** in Planning mode, (2) paste the prompt, (3) read and comment on the implementation plan, (4) approve, (5) review the walkthrough and diff, (6) run `/run-checks`, (7) do the human checkpoint, (8) run `/commit-phase`.

---

### Phase 0: Scaffold (Day 2)

**Goal:** empty but runnable project skeleton.

```
Read docs/PRD.md and .agent/rules. Create: requirements.txt (unpinned, from
the stack in the rules; after installing, pin versions), a Python virtual
environment setup in README, src/ subpackages (ingest, features, models, api,
alerts, advisory), a config module that loads .env, a /api/health endpoint in
FastAPI, and one passing smoke test. No feature code yet.
```

**You verify:** `uvicorn src.api.main:app --reload` starts; `/api/health` responds; `pytest` passes.

---

### Phase 1: Data Ingestion (Week 1 to 2)

**Goal:** fetch weather for your zones, live and historical.

```
Build src/ingest to fetch (a) hourly forecast/current rainfall, temperature,
humidity and soil moisture from Open-Meteo for these zones: [ZONE NAME,
LAT, LON; ...], and (b) multi-year daily historical weather from the Open-Meteo
historical API for the same zones from [YEAR] to [YEAR]. Save raw JSON/CSV
under data/raw/. Add retries, timeouts, and caching. Add tests using
mocked responses. Do not invent any values.
```

**You verify:** open a raw file and check coordinates, dates, and units are sensible. Compare one rainfall total with a news or IMD report for a known heavy-rain day.

---

### Phase 2: Labels and Dataset (Week 2 to 4) ⚠ the hardest phase

**Goal:** a labeled table of (zone, date) with `flood = 0/1`.

**You do this first (the agent cannot):** obtain flood records. Options, best first:

1. River gauge data with danger levels (state water resources or national water information portals; sometimes needs a request).
2. Recorded flood events per district and date (state disaster management reports, Dartmouth Flood Observatory archive).
3. A public Kaggle flood dataset. **Check its provenance**: some popular ones are synthetic and will give meaningless results.

Place your file in `data/raw/labels/`, then:

```
Read the label file in data/raw/labels/. First, show me its columns, date
range, row counts, and class balance. Then build src/features/dataset.py
that joins labels to historical weather by zone and date, handles missing
values, and writes data/processed/dataset.parquet. Document every cleaning
decision in docs/data-notes.md. Do not guess missing labels.
```

**You verify:** flood rate (usually a few percent), no duplicate rows, labels line up with known flood dates (e.g., a famous flood year shows 1s).

---

### Phase 3: Feature Pipeline (Week 4)

**Goal:** one saved pipeline used in both training and live inference.

```
Build the feature pipeline: rolling rainfall (24h/72h/7d), rainfall
anomaly versus the zone's seasonal norm, soil moisture, rate of change,
month/monsoon flag, and static zone features (elevation, distance to river
if I provide them in data/raw/zones.csv). Use only data available BEFORE
the prediction time. Save the fitted pipeline with joblib. Add a test proving
training and inference code paths produce identical features, and a test
that no feature uses future data.
```

**You verify:** read the leakage test; ask the agent to explain each feature in one line.

---

### Phase 4: Modeling and Evaluation (Week 4 to 6)

**Goal:** baseline, XGBoost, SVM, ensemble, calibration, SHAP, forecast model.

```
In src/models and scripts/train.py: split chronologically (train / validation
/ test by year, test = most recent years). Train logistic regression
(baseline), XGBoost, SVM, and a soft-voting ensemble of XGBoost + SVM, using
class weights for imbalance. Tune on validation using TimeSeriesSplit only.
Calibrate probabilities (isotonic) on validation. Add a 24h rainfall forecast
model using gradient boosting on lag features and compare against persistence.
Compute SHAP values for XGBoost. Save artifacts to models/ and a metrics
table to docs/results.md. Produce calibration and PR-curve plots.
```

Then run **`/report-metrics`**.

**You verify:**

- The test set contains only the latest period.
- ROC-AUC above about 0.98 on real data is suspicious. Ask the agent to audit for leakage.
- Recall is reported at your alert threshold, not just AUC.
- If results are weak, report them honestly. The PRD allows documented limits.

---

### Phase 5: API, Database, Scheduler (Week 6 to 7)

**Goal:** live predictions stored and served.

```
Build the FastAPI app per PRD section 4.3: SQLAlchemy models (readings,
predictions, alerts, feedback), endpoints /api/risk/current,
/api/forecast/{zone}, /api/explain/{zone}, /api/whatif, /api/alerts,
/api/feedback, /api/health, plus a Server-Sent Events stream at /api/stream.
Add an APScheduler job that every 30 minutes ingests data, applies the saved
pipeline, scores each zone, and stores the result. If an API call fails,
keep the last prediction and mark data as stale. Add endpoint tests.
```

**You verify:** open `http://localhost:8000/docs` and call each endpoint; stop your internet and confirm the app does not crash.

---

### Phase 6: Dashboard (Week 7 to 8)

**Goal:** map, charts, alerts, emergency panel.

```
Build web/ with plain HTML, CSS, JS served by FastAPI. Include: Leaflet map
with color-coded zones (Low/Medium/High/Critical, with text labels), a live
data panel, Chart.js forecast chart, alert center with severity filter,
emergency panel (shelters/hospitals from data/raw/facilities.csv and a route
via the OSRM public API), historical page, responsive dark theme, and a
visible disclaimer. Update live via SSE with polling fallback.
```

**Use the browser sub-agent:** start a second task: "Open the dashboard in the browser, click each zone, open every panel, resize to mobile width, and report visual bugs with screenshots." Review the screenshots.

**You verify:** it works on your phone browser on the same network.

---

### Phase 7: Advancements A1 to A5 (Week 8 to 9)

Run each as a separate task.

**A1 + A2: confidence and "Why this risk?"**

```
Expose calibrated probability and a confidence score (agreement between
XGBoost and SVM) in /api/risk/current. Implement /api/explain/{zone}
returning the top 3 SHAP drivers in plain language with the actual values
(e.g., "72h rainfall 180 mm, 3.1x seasonal norm"). Show both on the dashboard.
```

**A3: what-if simulator**

```
Implement /api/whatif accepting zone and extra_rainfall_mm. Recompute rolling
features with the added rainfall, re-score, and return old vs new risk. Add a
slider to the dashboard. Include tests.
```

**A4: AI advisories**

```
Create src/advisory with a function that turns structured model output (zone,
risk level, probability, top drivers, forecast) into a short advisory in
English plus [REGIONAL LANGUAGE]. Providers: template (default), claude, gemini,
chosen by ADVISORY_PROVIDER. The LLM may only rephrase the numbers it is given
and must never change the risk level. On any error, fall back to the template.
Add tests for both paths with the LLM mocked.
```

**You verify:** have a native speaker check the regional-language text, and confirm every number in the advisory appears in the model output.

**A5: feedback and model health**

```
Add feedback buttons (correct / false alarm) to each alert, stored via
/api/feedback. Add a model-health page showing data freshness, rolling
precision and recall from feedback, and alert counts. Create
scripts/retrain.py that retrains on updated data and saves a new model
version only if validation recall does not drop.
```

---

### Phase 8: Alerts (Week 9)

```
Implement src/alerts: trigger when probability >= ALERT_THRESHOLD for
ALERT_CONSECUTIVE_READINGS consecutive readings for a zone. Send a Telegram
message with the advisory, log every alert to the database, and avoid
duplicate alerts within a cooldown period. Add tests with Telegram mocked.
```

**You verify:** trigger a test alert to your own Telegram chat.

---

### Phase 9: Simulation Mode (Week 10)

**Goal:** a reliable demo that does not depend on live weather.

```
Build scripts/simulate.py to replay [EVENT, e.g. the 2018 Kerala floods]
from historical data through the same pipeline, model, API and dashboard at
adjustable speed (1x to 100x), triggering real alerts to a test chat.
Add a "Simulation" banner on the dashboard so it is never mistaken for live data.
```

**You verify:** run it start to finish three times. This is your demo.

---

### Phase 10: Testing and Hardening (Week 11)

```
Audit the project against the acceptance criteria in docs/PRD.md section 8.
Produce a table: criterion, status, evidence, gap. Do not mark anything
passed without evidence. Then fix test gaps, add input validation to all
endpoints, protect admin routes, and make sure no secrets are in the repo.
```

Then run a usability test with at least 5 people (give them 5 tasks, time them, note confusion).

---

### Phase 11: Documentation and Demo (Week 12)

```
Write README.md (setup, run, train, simulate, test), docs/architecture.md with
a Mermaid diagram, and docs/limitations.md covering data quality, regional
generalization, false-alarm trade-offs, and ethical considerations. Base
results only on docs/results.md.
```

Record a 3 to 5 minute demo video of simulation mode.

---

## Part 5: Using Antigravity Effectively

1. **Review plans, not just code.** Comment on the implementation plan ("use the saved pipeline, don't recompute features") before approving. It is the cheapest place to catch mistakes.
2. **One conversation per phase.** Long conversations drift. Start fresh and let the rules and PRD supply context.
3. **Parallel agents only after contracts are frozen.** Once the API endpoints in Phase 5 are stable, one agent can build the dashboard (Phase 6) while another builds advisories (A4), since they touch different folders.
4. **Use the browser sub-agent for UI checks**, not for judging correctness of predictions.
5. **Commit after every approved phase.** If an agent makes a mess, `git restore .` or reset to the last commit and retry with a narrower prompt.
6. **Ask "explain this result" before accepting any metric** you cannot interpret yourself.

---

## Part 6: Common Problems

| Problem | Likely cause | Fix |
| --- | --- | --- |
| Near-perfect scores | Leakage (random split, future features, label in features) | Re-audit split and features; rerun `/report-metrics` |
| Agent edits tests to pass | Prompt did not forbid it | Rule already forbids it; ask it to revert and fix the code |
| Agent invents data or endpoints | Data missing or API unclear | Provide a sample file or the API docs link; tell it to stop and ask |
| Model works in training, fails live | Different preprocessing | Use the single saved pipeline; check the identical-features test |
| No floods in the labels window | Too narrow a date range | Extend years or pick a more flood-prone region |
| Dashboard not updating | SSE blocked or server restart | Keep polling fallback; check browser console |
| API rate limits | Too-frequent fetching | Cache; fetch every 30 to 60 minutes |
| Library version errors | Unpinned dependencies | Run `pip freeze` into requirements.txt after the first working install |
| Agent stalls or loops | Task too big | Stop it, split into smaller tasks |

---

## Part 7: 12-Week Schedule

| Week | Work | Output |
| --- | --- | --- |
| 1 | Setup, decisions, Phase 0, start Phase 1 | Skeleton, region and zones chosen |
| 2 | Phase 1 ingestion; find label data | Raw weather data |
| 3 to 4 | Phase 2 labels and dataset; Phase 3 features | Clean dataset and pipeline |
| 5 to 6 | Phase 4 modeling and evaluation | Results table, calibrated models |
| 7 | Phase 5 API and scheduler | Working backend |
| 8 | Phase 6 dashboard | Working dashboard |
| 9 | Phase 7 advancements, Phase 8 alerts | Feature-complete system |
| 10 | Phase 9 simulation | Reliable demo |
| 11 | Phase 10 testing and usability study | Test report |
| 12 | Phase 11 documentation, video, viva practice | Final package |

Review checkpoints with your guide: end of weeks 2, 6, 9, and 11.

---

## Part 8: Final Checklist Before Submission

- [ ] Model comparison table with baseline, XGBoost, SVM, ensemble
- [ ] Calibration plot, Brier score, SHAP examples, ablation study
- [ ] Forecast beats persistence baseline
- [ ] Dashboard works on desktop and phone
- [ ] Telegram alert received within 5 minutes in testing
- [ ] Advisories work with the LLM on and off
- [ ] Simulation mode runs end to end, three times in a row
- [ ] Usability test with 5+ users documented
- [ ] No secrets or raw data in the repository
- [ ] README, architecture diagram, limitations document, demo video
- [ ] Slides updated to match the built system (hybrid = XGBoost + SVM; CNN is a stretch goal)

**Last honest note:** the model's value depends on label quality. Spend more time on Phase 2 than on anything else, and report your results truthfully. An honest 0.80 recall with a clear explanation scores better than an unexplained 0.99.
