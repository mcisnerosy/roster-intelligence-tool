# Build Process & Design Narrative
## CFB Roster Intelligence Tool

---

## The Problem

The idea came from working inside Notre Dame's football program. Recruiting
staff track roster depth and recruit pipelines through internal systems,
spreadsheets, and film, but none of those sources answer one specific
question: *given where we're thin right now, who is actually available in
the national recruit pool to address it?*

This tool exists to close that gap, between current roster state and
available recruiting targets. The secondary goal was a portfolio project.
Football analytics roles ask for evidence you can build something
functional, not just run models in a notebook.

---

## Phase 1: Scope Definition

The first decision was to avoid scope creep. Football analytics projects
tend to expand, "let's add injury tracking, NIL data, draft projections,"
and end up half-finished.

The constraint I set: four pages, each answering one specific question a
recruiting analyst would actually ask on any given day.

| Page | Question |
|---|---|
| Roster Depth Dashboard | Where are we thin right now? |
| Position Deep Dive | How do we compare at a specific position? |
| Recruit Discovery | Who's available to fill the gap? |
| Recruiting Positioning | Are we recruiting the right positions strategically? |

Every feature idea got evaluated against those four questions. If it didn't
serve one of them, it didn't ship, at least not in V1.

The competitor set started hardcoded to Ohio State, Georgia, and Alabama.
In V2 this became a user-selectable multiselect, and the tool was
generalized to work for any FBS program, not just Notre Dame.

---

## Phase 2: Data Source Decision

The data source question came before writing any code. The options:

- **247Sports / Rivals**: most comprehensive, requires paid license
- **ESPN API**: undocumented, rate-limited, unclear terms for programmatic use
- **CFBD (College Football Data)**: free, documented, consistent structure,
  covers FBS rosters back to 2014

CFBD was the only viable option for an independent student project. The
trade-off is ~70% roster coverage, walk-ons and some transfers don't
appear. That limitation is documented in the tool rather than hidden.

Before writing any UI, I ran a quick script to pull a single team's
roster and check field names, coverage, and position label formats. That
step caught the most important technical decision in the project:

**CFBD uses completely different position labels for recruiting data vs.
roster data.** Recruiting uses `OT`, `IOL`, `EDGE`, `APB`. Roster uses
`OL`, `DL`, `RB`. Without a mapping layer between these two systems,
position filters on the Recruit Discovery page return zero results.
The `RECRUIT_POSITION_MAP` constant is the fix.

---

## Phase 3: Architecture Decisions

**Single-file vs. modular**

The initial prototype was a single `app.py`. The first refactor split
recruiting data fetching into `recruiting_data.py`: the recruiting
functions are testable without running Streamlit, and `app.py` stays
focused on UI logic rather than data pipeline logic.

**Caching**

Without caching, every user interaction re-fetches from CFBD. Page 4
alone makes up to 15 API calls (5 programs x 3 years). With
`@st.cache_data(ttl=86400, persist="disk")`, the first load per cache
window is slow but every later interaction, from any visitor, is instant.
A 24-hour TTL fits because CFBD data updates at most once a day, and disk
persistence keeps the cache warm across the app sleeping or restarting on
Streamlit Cloud. That matters because CFBD's free tier caps out at
1,000 calls/month; a shorter TTL or memory-only cache would burn through
that for no real freshness gain.

**Session state for cross-page navigation**

The "Find Recruits" button on Page 1 pre-populates the position filter
on Page 3. `st.session_state` handles this: the button writes
`st.session_state['recruit_position'] = position`, triggers
`st.rerun()`, and Page 3 reads that value for its default dropdown
index. The value is cleared after use so it doesn't linger.

**Per-page competitor selection vs. sidebar**

V1 put the competitor multiselect in the sidebar. This changed in V2
because Pages 2 and 4 serve different questions, a user might want
different competitors for each. Moving the selector onto each page lets
someone compare against SEC schools on Page 2 and national programs on
Page 4 without resetting anything in the sidebar.

---

## Phase 4: Generalization to All FBS Programs

The biggest change from V1 to V2 was making the tool work for any FBS
program instead of only Notre Dame.

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

CFBD uses naming conventions that differ from common usage for about 10
programs. I found these by writing a quick script that hit the API for
every team name in `TEAM_COLORS` and flagged which ones came back with
an empty roster. Confirmed fixes:

| Common name | CFBD name |
|---|---|
| Appalachian State | App State |
| North Carolina State | NC State |
| Hawaii | Hawai'i |
| Mississippi | Ole Miss |
| San Jose State | San José State |
| UConn | UConn |
| UMass | Massachusetts |
| Southern Mississippi | Southern Miss |
| Sam Houston State | Sam Houston |

Louisiana-Monroe (ULM) turned out to have no roster data for any year in
CFBD's database, despite existing as a team entry. It stayed in the
selector with a plain empty-roster message instead of being removed.

---

## Phase 5: UI and Visualization Decisions

**Framework choice**

Streamlit over Dash or Flask because the target users, recruiting staff
and hiring managers, need zero install friction. A live URL they can
open on a phone during a meeting beats a more polished app that needs
local setup.

**Font and color system**

Target look: editorial sports, more The Athletic than fan site. Oswald
(headings) plus Inter (body) because Oswald shows up across college
football broadcast graphics. The color system follows whichever team is
selected: each program's bars and highlights use its actual brand color.

**Roster alert panel design**

Early versions had a fourth ACTION column in the depth tables with a
"Find Recruits" button per critical position. That became a dedicated
alert panel above the tables, shown only when critical positions exist.
Each alert is a full row with the status message and action button side
by side. The tables underneath are now a clean 3-column display with no
action column.

**Choropleth vs. dot map**

The first recruit map used dots at state centroids with jitter for
clustering. The problem: California with 12 recruits showed 12 dots
bunched in the middle of the state, which looked busy but didn't tell
you at a glance that California had more recruits than Montana.

A choropleth (filled state map) fixes that: color intensity reads as
density immediately. The color scale runs from light blue (zero
recruits) to the selected team's brand color (maximum). Hover text
shows the top 3 recruits per state by composite rating, so the map
doubles as a scouting reference.

**Gap analysis chart**

The third tab on Page 4 shows a team's recruit count minus the
competitor average at each position. The raw headcount and star rating
charts answer "what did we do," but not "are we doing it differently
than our competitors." The gap chart answers that directly. Positive
bars (team color) mean over-recruiting vs. peers; negative bars (red)
mean under-recruiting. Plain-language bullet summaries sit below the
chart so a non-analyst can read the finding without parsing the axis.

---

## Things That Didn't Work

**`PLOTLY_LAYOUT` dict conflict**

A shared layout dict for all Plotly charts is a clean pattern, until any
key in it is also passed as a keyword argument in an individual chart's
`update_layout()` call. Python raises:
`TypeError: multiple values for keyword argument 'yaxis'`

Fix: drop `yaxis` and `margin` from the shared dict entirely. Each chart
owns its own axis config. A bit more typing, but no conflicts.

**The "undefined" legend label**

Plotly Express charts were rendering the literal text "undefined" above
the legend. The figure's JSON on the Python side was clean, that string
wasn't in it anywhere. Root cause: Streamlit bundles its own version of
Plotly.js, which lags behind the pip-installable package, and that older
version reads an unset `legend.title.text` as JavaScript `undefined` and
renders it as text.

Fix: `legend=dict(title_text=' ', ...)`, a single space instead of an
empty string or no key at all. The space is invisible but counts as a
valid string, so the undefined path never fires.

**pandas 3.x Arrow backend**

pandas 3.x uses PyArrow as the default backend for some column types.
Running NumPy arithmetic on an Arrow-backed Series (adding a float array
to a lat/lon column for map jitter) raises a `TypeError` that older
pandas versions don't. Fix: `.astype(float)` before the arithmetic,
which forces the column off the Arrow backend.

**Portal endpoint URL**

The first attempt hit `/transferportal`, which returned empty responses
for every year. The correct CFBD endpoint is `/player/portal`. Found by
adding a debug expander to Page 2 that printed the raw API response,
field names and row counts included.

**Transfer portal name matching**

The first version collected every name across all portal entries and
checked whether a roster player's name showed up anywhere in that set.
That was wrong two ways: false positives for players who share a name
with someone else who transferred, and no sense of direction or year.

Fixed by filtering portal entries down to ones where `origin` or
`destination` contains the selected team, then building a lookup with
direction and year attached: `Transfer In (Duke → ND, 2024)`.

---

## Lessons Applied

**Define thresholds explicitly.** Any tool that flags something as
"critical" needs a specific number behind it. `POSITION_THRESHOLDS` keeps
that logic visible and adjustable in one place.

**Document data quality in the UI, not just the README.** The ~70%
coverage caveat shows up on every page, so people who skip the docs
still see it.

**Validate API data before building UI.** The position label mismatch
and the wrong portal endpoint would both have surfaced sooner with a
quick data check before writing any UI code.

**Ship V1 before adding features.** Transfer portal, the recruit map,
gap analysis, and multi-team support were all bolted on after a working
V1 existed. Building on something that already worked was a lot easier
than trying to design for all of it up front.

**Test every team name programmatically.** Manual inspection would have
missed the "App State" vs. "Appalachian State" mismatch. A script that
tests all 134 names against the live API catches things documentation
won't tell you.

---

## What Would Be Different in V3

**Year selector on Pages 2 and 4.** Page 1 has a year selector
(2021-2024) but Pages 2 and 4 are still locked to 2024 rosters and
2023-2025 recruiting classes. Adding year controls there would open up
trend questions like "how has our OL depth changed over 3 years?"

**Conference-aware competitor defaults.** Right now the default
competitor set is always Ohio State, Georgia, Alabama, and Clemson,
regardless of the selected team. A Kansas State user would more likely
want Iowa State, TCU, and Oklahoma State. Defaulting to same-conference
programs would make the tool more useful out of the box for any team.

**Player ID-based portal matching.** The current name-matching approach
for portal history is the weakest part of the tool. CFBD assigns
internal player IDs, but the roster and portal endpoints don't return
them in a consistent format. If that changes, the portal column could
go from best-effort to fully accurate.
