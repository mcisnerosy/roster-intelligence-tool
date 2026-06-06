# CFB Roster Intelligence Tool
### Technical Writeup
**Marcos Cisneros** · Built 2025

---

## Overview

The CFB Roster Intelligence Tool is a live, interactive web application for
analyzing college football roster depth, transfer portal history, and
recruiting strategy across any FBS program. It pulls real-time data from
the College Football Data API (CFBD), processes it with pandas, and renders
four analytical pages through a Streamlit interface deployed on Streamlit
Cloud.

The tool was built with two goals: to solve a real operational problem in
college football recruiting analysis, and to demonstrate end-to-end
applied data engineering — from API integration and data cleaning through
interactive visualization and public deployment.

**Live app:** [roster-intelligence-tool.streamlit.app](https://roster-intelligence-tool.streamlit.app)  
**Source code:** [github.com/mcisnerosy/roster-intelligence-tool](https://github.com/mcisnerosy/roster-intelligence-tool)  
**Stack:** Python · Streamlit · Plotly · pandas · CFBD API · Streamlit Cloud

---

## The Problem Being Solved

College football recruiting staffs track roster depth and recruit pipelines
through a mix of internal systems, spreadsheets, and film sessions. These
sources don't talk to each other, and none of them efficiently answers the
question that matters most during a recruiting cycle: *given where we're
thin right now, who is available in the national recruit pool to address it?*

The gap between current roster state and available recruiting targets is
what this tool is built to close. It connects four analytical workflows
that are typically handled separately:

1. **Where is the roster thin?** — live depth tracking with defined thresholds
2. **How do we compare at a position?** — competitor benchmarking against any
   user-selected program set
3. **Who can fill the gap?** — national recruit discovery with position,
   year, star rating, and availability filters
4. **Are we recruiting strategically?** — class composition benchmarking
   against competitor programs across three recruiting cycles

---

## Technical Architecture

### Data Layer

All data is sourced from the CFBD API, a free and documented REST API for
college football data. Three endpoints are used:

| Endpoint | Data | Used On |
|---|---|---|
| `/roster` | Scholarship roster by team and year | Pages 1, 2 |
| `/recruiting/players` | National recruit pool by class year | Pages 3, 4 |
| `/player/portal` | Transfer portal entries by year | Page 2 |

API calls are authenticated via Bearer token. The key is stored in
Streamlit Cloud secrets for the deployed version and in a `.env` file
(loaded via `python-dotenv`) for local development. The same codebase
handles both environments without modification via a `st.secrets` → `.env`
fallback pattern.

All three API helper functions use Streamlit's `@st.cache_data(ttl=3600)`
decorator — a 1-hour in-memory cache. Without caching, Page 4 makes up to
15 sequential API calls on every user interaction (5 programs × 3 years).
With caching, only the first load fetches from CFBD; all subsequent
interactions within the session are instant.

### Application Layer

The application is split into two Python files:

**`app.py`** (1,100+ lines) handles all UI rendering, page routing, API
calls for roster and portal data, Plotly chart generation, and the CSS
theme. Streamlit re-executes this file top-to-bottom on every user
interaction, so persistent state is managed via `st.session_state` (for
cross-page navigation) and `@st.cache_data` (for API responses).

**`recruiting_data.py`** handles multi-team, multi-year recruiting class
fetching. It's deliberately separate from `app.py` so the data pipeline
can be tested independently without running the Streamlit UI. The
`@st.cache_data` decorator is applied conditionally — the function is
defined inside a `try` block that imports `streamlit`, falling back to an
uncached version if the import fails (i.e., when run as a standalone script).

### Key Data Engineering Challenge: Position Label Mismatch

The most significant data quality problem in the project was a labeling
inconsistency in CFBD's own API: recruiting data and roster data use
different position labels for the same positions.

```
Roster label    CFBD recruiting labels
'OL'       →    'OT', 'OG', 'IOL', 'C'
'DL'       →    'DT', 'DE', 'EDGE', 'WDE', 'SDE'
'RB'       →    'RB', 'APB', 'FB'
'LB'       →    'LB', 'ILB', 'OLB', 'WLB', 'MLB'
```

Without a mapping layer between these two systems, position filters on the
Recruit Discovery page return zero results for most positions. The solution
is `RECRUIT_POSITION_MAP` — a dict mapping each standard position group to
all equivalent CFBD recruiting labels. Page 3 filters using
`.isin(RECRUIT_POSITION_MAP[selected_position])`. Page 4 uses a reversed
version of this map to group all recruiting records into standard position
groups before charting.

### Team Name Validation

CFBD uses naming conventions that differ from common usage for ~10 FBS
programs. These mismatches were discovered systematically: a test script
(`test_teams.py`) hit the CFBD `/roster` endpoint for all 134 programs in
the tool's team database and reported which names returned empty responses.

Confirmed fixes from this process:

| Common name | CFBD name |
|---|---|
| Appalachian State | App State |
| North Carolina State | NC State |
| Hawaii | Hawai'i |
| Ole Miss (common) | Ole Miss (CFBD) |
| San Jose State | San José State |
| UConn, UMass, Southern Miss, Sam Houston | Verified variants |

This kind of systematic validation — rather than manual inspection — is
the right approach when working with any external API that has inconsistent
naming conventions.

---

## Analytical Features

### Roster Depth Dashboard

Displays current scholarship roster depth for any FBS program, organized
by offensive, defensive, and special teams units. Each position is
evaluated against defined thresholds:

```python
POSITION_THRESHOLDS = {
    'QB':  (critical≤1, watch≤3),
    'OL':  (critical≤6, watch≤9),
    'WR':  (critical≤4, watch≤7),
    # ... all 12 tracked positions
}
```

Thresholds encode real roster construction logic — a team needs at minimum
2 scholarship QBs to run practice rotations safely, 6 OL to field five
starters plus a backup at each spot. Making thresholds explicit and
adjustable in one place is a deliberate design choice: a tool that flags
something as "critical" but doesn't define what that means isn't
trustworthy.

Critical positions surface an alert panel above the depth tables with a
direct "Find Recruits →" button. Clicking stores the position in
`st.session_state` and triggers a page navigation to Recruit Discovery
with that position pre-populated. A year selector (2021–2024) allows
historical depth comparison — "how has our OL depth changed over three
years?"

### Position Deep Dive

Two sections: a player table with transfer portal history, and a horizontal
bar chart comparing headcount at that position against user-selected
competitor programs.

The portal history column is built by querying CFBD's `/player/portal`
endpoint for 2021–2024, filtering entries to those involving the selected
team, and matching against roster players via case-insensitive full-name
lookup. Display format: `Transfer In (Duke → Notre Dame, 2024)` or
`Transfer Out (Notre Dame → Alabama, 2023)`.

The competitor chart is horizontal `go.Bar` rather than vertical — with
4+ programs, vertical bars are too wide and text labels overlap.
The x-axis range is padded dynamically to `max_val + max(2, 20% of max)`
to prevent labels from clipping at the chart edge.

### Recruit Discovery

Filters the national recruit pool (all FBS programs, any class year
2025–2028) by position, star rating, and commitment status. The position
filter uses `RECRUIT_POSITION_MAP` to translate standard position groups
to all equivalent CFBD recruiting labels — without this, filtering by
"OL" would return zero results because CFBD recruiting data uses "OT",
"IOL", etc.

Below the recruit table is a choropleth map showing uncommitted recruit
density by US state. Color scale runs from light blue (zero recruits) to
the selected team's brand color (maximum). Hovering any state shows the
top 3 uncommitted recruits by composite rating with name, stars, and
rating score. A side-by-side summary shows top states by recruit count
and the star rating breakdown for the current filter set.

The choropleth was chosen over a dot map (the first implementation)
because color intensity communicates density at a glance. A dot map with
12 California recruits shows 12 dots in the middle of the state —
visually interesting but analytically less readable than a filled state.

### Recruiting Class Composition

Compares recruiting class composition across 2023–2025 for any team and
its selected competitors. Three analytical tabs:

**Headcount by position** — raw volume comparison. Shows which programs
recruit more or fewer players at each position group.

**Average star rating by position** — quality comparison. High headcount
+ low stars = volume recruiting. Low headcount + high stars = targeted
approach. The combination of these two charts identifies programs that
over-recruit for depth vs. those that recruit selectively for quality.

**Gap analysis** — the most analytically interesting tab. Computes
`selected_team_count - mean(competitor_counts)` at each position group.

```python
field_avg = pos_counts[pos_counts['team'] != selected_team]\
    .groupby('position_group')['count'].mean()
gap_df['delta'] = nd_counts['count'] - field_avg
```

Positive delta (shown in team color) = recruiting above competitor
average at that position. Negative delta (shown in red) = recruiting
below. A gold zero line separates the two. Plain-language bullet summaries
render below the chart so a non-analyst can read the finding without
interpreting the y-axis.

---

## Visualization Decisions

### Plotly for all charts

Plotly was chosen over Matplotlib or Altair because it produces
interactive charts natively (hover, zoom, click) that integrate cleanly
with Streamlit via `st.plotly_chart()`. All charts share a `PLOTLY_LAYOUT`
base dict unpacked with `**` into each `fig.update_layout()` call for
consistent styling.

One technical constraint: `yaxis` and `margin` are excluded from the
shared dict. If those keys appear in both the shared dict and an
individual call, Python raises `TypeError: multiple values for keyword
argument`. Each chart defines its own axis config to avoid this.

### Team color system

All 134 FBS programs have hardcoded primary brand hex colors in
`TEAM_COLORS`. The selected team's color is used for its bars and
chart highlights; competitors use their own brand colors. This makes
charts immediately identifiable — a Michigan vs. Ohio State comparison
shows maize vs. scarlet rather than generic grey bars.

### The "undefined" Plotly bug

During development, Plotly Express charts rendered the text "undefined"
above the legend in Streamlit's interface. The Python-side figure JSON
was completely clean — the string didn't appear anywhere in it.

Root cause: Streamlit bundles its own version of Plotly.js (which lags
behind the pip-installable Python package), and that bundled version
interprets an unset `legend.title.text` field as JavaScript `undefined`,
rendering it literally on screen.

Fix: `legend=dict(title_text=' ', ...)` — a single space rather than an
empty string or omitted key. The space is invisible but is a valid
non-null value that prevents the undefined code path. This is a known
footgun for Streamlit + Plotly combinations where the package versions
are mismatched.

---

## Deployment

The tool is deployed on Streamlit Community Cloud at a public URL. GitHub
integration means any push to the main branch triggers an automatic
redeploy. The API key is stored in Streamlit Cloud's secrets manager and
never appears in the source code or repository.

The `requirements.txt` lists only five direct dependencies
(streamlit, pandas, requests, python-dotenv, plotly) rather than a
`pip freeze` output. Streamlit Cloud resolves transitive dependencies
automatically; a minimal requirements file avoids version conflicts
between the local environment and the cloud deployment environment —
a common cause of deploy failures in student projects.

`showErrorDetails = false` in `config.toml` suppresses raw Python
tracebacks on the deployed version. End users should never see internal
file paths or stack traces.

---

## What This Demonstrates

**API integration and data cleaning** — working with a real third-party
API, handling inconsistent naming conventions across endpoints, validating
data quality programmatically, and building a mapping layer to normalize
mismatched labels.

**Applied data engineering** — caching strategy for API-heavy interactive
apps, session state management for cross-page navigation, separating data
pipeline logic from UI logic.

**Interactive visualization** — chart type selection based on analytical
purpose (horizontal bars for program comparisons, choropleth for geographic
density, gap chart for delta analysis), consistent theming across all
visualizations, hover text that surfaces the most analytically useful
information per data point.

**Software engineering fundamentals** — modular file structure, documented
functions and constants, systematic validation tooling (`test_teams.py`),
clean separation of concerns between `app.py` and `recruiting_data.py`.

**Domain knowledge** — position threshold logic grounded in real FBS
roster construction, competitor selection based on actual recruiting
competition dynamics, CFBD data coverage limitations acknowledged and
documented rather than hidden.