# Build Process & Design Narrative
## CFB Roster Intelligence Tool

---

## The Problem

The idea came from working inside Notre Dame's football program. Recruiting
staff track roster depth and recruit pipelines through internal systems,
spreadsheets, and film — but none of those sources answer a specific
question: *given where we're thin right now, who is actually available in
the national recruit pool to address it?*

That gap — between current roster state and available recruiting targets —
is what this tool is built to close. The secondary goal was a portfolio
project. Football analytics roles consistently ask for evidence that you
can build something functional, not just run models in a notebook. A
deployed, interactive tool with real data is more compelling than a
well-commented Jupyter notebook.

---

## Phase 1: Scope Definition

The first design decision was to avoid scope creep. Football analytics
projects tend to expand — "let's add injury tracking, NIL data, draft
projections" — and end up half-finished.

The constraint I set: four pages, each answering one specific question a
recruiting analyst would actually ask on any given day.

| Page | Question |
|---|---|
| Roster Depth Dashboard | Where are we thin right now? |
| Position Deep Dive | How do we compare at a specific position? |
| Recruit Discovery | Who's available to fill the gap? |
| Recruiting Positioning | Are we recruiting the right positions strategically? |

Every feature idea got evaluated against those four questions. If it didn't
serve one of them, it didn't ship — at least not in V1.

The competitor set started hardcoded to Ohio State, Georgia, and Alabama.
In V2, this became a user-selectable multiselect, and the tool was
generalized to work for any FBS program — not just Notre Dame. That
upgrade made the tool portfolio-defining rather than program-specific.

---

## Phase 2: Data Source Decision

The data source question came before writing any code. The options:

- **247Sports / Rivals** — most comprehensive, requires paid license
- **ESPN API** — undocumented, rate-limited, unclear terms for programmatic use
- **CFBD (College Football Data)** — free, documented, consistent structure,
  covers FBS rosters back to 2014

CFBD was the only viable option for an independent student project. The
trade-off is ~70% roster coverage — walk-ons and some transfers don't
appear. That limitation is documented in the tool rather than hidden:
a tool that acknowledges its data quality constraints is more trustworthy
than one that doesn't.

The first thing built before any UI was a data validation script — fetch a
single team's roster, check field names, check coverage, check position
label formats. This step caught what became the most important technical
decision in the project:

**CFBD uses completely different position labels for recruiting data vs.
roster data.** Recruiting uses `OT`, `IOL`, `EDGE`, `APB`. Roster uses
`OL`, `DL`, `RB`. Without a mapping layer between these two systems,
position filters on the Recruit Discovery page return zero results.
The `RECRUIT_POSITION_MAP` constant is the fix.

---

## Phase 3: Architecture Decisions

**Single-file vs. modular**

Initial prototype was a single `app.py`. The first refactor separated
recruiting data fetching into `recruiting_data.py` for two reasons:
the recruiting functions are testable without running Streamlit, and
`app.py` stays focused on UI logic rather than data pipeline logic.

**Caching**

Without caching, every user interaction re-fetches from CFBD. Page 4
alone makes up to 15 API calls (5 programs × 3 years). With
`@st.cache_data(ttl=3600)`, the first load is slow but all subsequent
interactions are instant. The 1-hour TTL is appropriate because CFBD
data updates at most once per day.

**Session state for cross-page navigation**

The "Find Recruits →" button on Page 1 pre-populates the position
filter on Page 3. Streamlit's `st.session_state` handles this:
the button writes `st.session_state['recruit_position'] = position`,
triggers `st.rerun()`, and Page 3 reads that value to set the default
dropdown index. State is cleared after use so it doesn't persist.

**Per-page competitor selection vs. sidebar**

V1 put the competitor multiselect in the sidebar. This was changed in V2
because Pages 2 and 4 serve different analytical questions — a user might
want different competitors for each. Sidebar selection forces the same
comparison everywhere. Moving the selector to each page that uses it
gives users the flexibility to compare against, say, SEC schools on Page 2
and national programs on Page 4 without changing the sidebar between views.

---

## Phase 4: Generalization to All FBS Programs

The biggest upgrade from V1 to V2 was making the tool work for any FBS
program rather than only Notre Dame.

**What this required:**

- `TEAM_COLORS` dict with primary brand hex colors for all 134 FBS programs
- `FBS_TEAMS` team selector in the sidebar
- `TEAM_COLOR` variable derived from `selected_team` each run, used for
  chart highlights and the choropleth map color scale
- `build_color_map()` function that assigns real brand colors to both
  the selected team and its competitors in Plotly charts
- All hardcoded `'Notre Dame'` strings replaced with `selected_team`
- Portal matching updated to use `selected_team` dynamically
- `load_recruiting_data()` updated to accept `teams` as a parameter

**Team name validation:**

CFBD uses naming conventions that differ from common usage for ~10 programs.
Discovered through a systematic test script (`test_teams.py`) that hit the
API for every team name in `TEAM_COLORS` and reported which returned empty
rosters. Confirmed fixes:

| Common name | CFBD name |
|---|---|
| Appalachian State | App State |
| North Carolina State | NC State |
| Hawaii | Hawai'i |
| Ole Miss | Mississippi → Ole Miss |
| San Jose State | San José State |
| UConn | UConn |
| UMass | Massachusetts |
| Southern Mississippi | Southern Miss |
| Sam Houston State | Sam Houston |

Louisiana-Monroe (ULM) was found to have no roster data for any year
in CFBD's database despite existing as a team entry. Kept in the selector
with a graceful empty-roster message rather than removed silently.

---

## Phase 5: UI and Visualization Decisions

**Framework choice**

Streamlit over Dash or Flask because the target users — recruiting staff
and hiring managers — need zero install friction. A live URL they can open
on a phone during a meeting is more valuable than a technically superior
app that requires local setup.

**Font and color system**

Target aesthetic: editorial sports — The Athletic or ESPN Stats & Info,
not a fan site. Oswald (headings) + Inter (body) because Oswald is the
dominant font in college football broadcast graphics. The color system is
team-color-aware: each program's bars and highlights use their actual brand
color, making charts immediately recognizable.

**Roster alert panel design**

Early versions had a fourth ACTION column in the depth tables with a
"Find Recruits" button per critical position. This was changed to a
dedicated alert panel that renders above the tables when critical positions
exist. Each alert is a full row with the status message and action button
side by side. The tables themselves became a clean 3-column display with no
action column — separating data display from actionable alerts.

**Choropleth vs. dot map**

The first recruit map used dots at state centroids with jitter for
clustering. The problem: California with 12 recruits showed 12 dots in
the middle of the state — visually impressive but analytically useless
since you couldn't tell at a glance that California had more recruits than
Montana.

A choropleth (filled state map) solves this immediately — color intensity
communicates density at a glance. The color scale uses light blue (zero
recruits) to the selected team's brand color (maximum), which keeps the
tool feeling team-specific even on a generic visualization. Hover text
shows the top 3 recruits per state by composite rating, turning the map
from a density display into a scouting reference.

**Gap analysis chart**

The third tab on Page 4 — showing Notre Dame's (or any team's) recruit
count minus the competitor average at each position — was added because
the raw headcount and star rating charts answer "what did we do?" but not
"are we doing it differently than our competitors?" The gap chart answers
the second question directly. Positive bars (team color) = over-recruiting
vs. peers. Negative bars (red) = under-recruiting. Plain-language bullet
summaries render below so a non-analyst can read the chart without
interpreting the y-axis.

---

## Things That Didn't Work

**`PLOTLY_LAYOUT` dict conflict**

A shared layout dict for all Plotly charts is a clean pattern. It breaks
the moment any key in the shared dict is also passed as a keyword argument
in an individual chart's `update_layout()` call. Python raises:
`TypeError: multiple values for keyword argument 'yaxis'`

The resolution: remove `yaxis` and `margin` from the shared dict entirely.
Each chart owns its own axis config. Slightly more verbose but error-free.

**The "undefined" legend label**

Plotly Express charts were rendering the text "undefined" above the legend
in Streamlit's bundled Plotly.js version. The Python-side figure JSON was
completely clean — the string didn't appear anywhere in it. Root cause:
Streamlit's bundled Plotly.js (which lags behind the pip-installable
version) interprets an unset `legend.title.text` field as JavaScript
`undefined` and renders it literally.

Fix: `legend=dict(title_text=' ', ...)` — a single space instead of an
empty string or omitted key. The space is invisible but is a valid
non-null string that prevents the undefined rendering path.

**pandas 3.x Arrow backend**

pandas 3.x uses PyArrow as the default backend for certain column types.
NumPy arithmetic on Arrow-backed Series (adding a float array to a lat/lon
column for jitter) raises a `TypeError` that doesn't occur in older pandas.
Fix: `.astype(float)` before arithmetic — forces the column out of the
Arrow backend. Relevant for any project mixing pandas 3.x with NumPy.

**Portal endpoint URL**

Initial implementation used `/transferportal` — returned empty responses
for all years. Correct CFBD endpoint is `/player/portal`. Discovered by
adding a debug expander to Page 2 that printed raw API response data
including field names and row counts.

**Transfer portal name matching**

First version collected all names from all portal entries and checked if
a roster player's name appeared anywhere in that set. Wrong in two ways:
false positives for players sharing a name with someone who transferred
elsewhere, and no context about direction or year.

Fixed by filtering portal entries to only those where `origin` or
`destination` contains the selected team, then building a structured
lookup with direction and year: `Transfer In (Duke → ND, 2024)`.

---

## Lessons Applied

**Define thresholds explicitly.** Any tool that flags something as
"critical" needs to define what that means with a specific number.
`POSITION_THRESHOLDS` makes the logic visible and adjustable in one place.

**Document data quality in the UI, not just the README.** The ~70%
coverage caveat appears on every page. Users who don't read documentation
will still see it.

**Validate API data before building UI.** The CFBD position label mismatch
and the portal endpoint URL issue would both have been caught earlier with
a data exploration step before any UI code was written.

**Ship V1 before adding features.** Transfer portal, the recruit map, gap
analysis, and multi-team support were all added after a working V1 existed.
Building on a working foundation was far easier than designing for all of
them upfront.

**Test every team name programmatically.** Manual inspection would have
missed the `"App State"` vs. `"Appalachian State"` mismatch. A systematic
script that tests all 134 names against the live API surfaces issues that
aren't obvious from documentation.

---

## What Would Be Different in V3

**Year selector on Pages 2 and 4.** Page 1 has a year selector (2021–2024)
but Pages 2 and 4 are still locked to 2024 rosters and 2023–2025 recruiting
classes. Adding year range controls to those pages would allow historical
trend analysis — "how has our OL depth changed over 3 years?"

**Conference-aware competitor defaults.** Right now the competitor default
is always Ohio State/Georgia/Alabama/Clemson regardless of the selected team.
A Kansas State user would more likely want to compare against Iowa State,
TCU, and Oklahoma State. Defaulting to same-conference programs would make
the tool more immediately useful for any team.

**Player ID-based portal matching.** The current name-matching approach for
portal history is the weakest part of the tool. CFBD assigns internal player
IDs, but the roster and portal endpoints don't return them in a consistent
format. If CFBD standardizes this, the portal column becomes perfectly
accurate instead of best-effort.