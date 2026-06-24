# CFB Roster Intelligence Tool
### Technical Writeup
**Marcos Cisneros** · Built 2026

---

## Overview

The CFB Roster Intelligence Tool is a live, interactive web app for
analyzing college football roster depth, transfer portal history, and
recruiting strategy across any FBS program. It pulls real-time data from
the College Football Data API (CFBD), processes it with pandas, and renders
four analytical pages through a Streamlit interface deployed on Streamlit
Cloud.

It was built to solve a real operational problem in college football
recruiting analysis, and to show end-to-end applied data work: API
integration, data cleaning, interactive visualization, and public
deployment.

**Live app:** [roster-intelligence-tool.streamlit.app](https://roster-intelligence-tool.streamlit.app)
**Source code:** [github.com/mcisnerosy/roster-intelligence-tool](https://github.com/mcisnerosy/roster-intelligence-tool)
**Stack:** Python, Streamlit, Plotly, pandas, CFBD API, Streamlit Cloud

---

## The Problem Being Solved

College football recruiting staffs track roster depth and recruit pipelines
through a mix of internal systems, spreadsheets, and film sessions. These
sources don't talk to each other, and none of them quickly answers the
question that matters most during a recruiting cycle: *given where we're
thin right now, who is available in the national recruit pool to address
it?*

This tool closes that gap between current roster state and available
recruiting targets, by connecting four workflows that are usually handled
separately:

1. **Where is the roster thin?** Live depth tracking against defined thresholds
2. **How do we compare at a position?** Benchmarking against any user-selected program
3. **Who can fill the gap?** National recruit search by position, year, stars, and availability
4. **Are we recruiting strategically?** Class composition benchmarking across three recruiting cycles

---

## Technical Architecture

### Data Layer

All data comes from the CFBD API, a free, documented REST API for college
football data. Three endpoints are used:

| Endpoint | Data | Used On |
|---|---|---|
| `/roster` | Scholarship roster by team and year | Pages 1, 2 |
| `/recruiting/players` | National recruit pool by class year | Pages 3, 4 |
| `/player/portal` | Transfer portal entries by year | Page 2 |

API calls authenticate via Bearer token. The key lives in Streamlit
Cloud's secrets manager for the deployed version and in a `.env` file
(loaded via `python-dotenv`) locally. The same codebase handles both
through a `st.secrets` → `.env` fallback, no separate config needed.

All three API helper functions use `@st.cache_data(ttl=3600)`, a 1-hour
in-memory cache. Without it, Page 4 makes up to 15 sequential API calls
on every interaction (5 programs x 3 years). With it, only the first load
hits CFBD; everything after that is instant.

### Application Layer

The app is split into two Python files:

**`app.py`** (1,100+ lines) handles UI rendering, page routing, API calls
for roster and portal data, Plotly charts, and the CSS theme. Streamlit
re-executes this file top-to-bottom on every interaction, so persistent
state runs through `st.session_state` (cross-page navigation) and
`@st.cache_data` (API responses).

**`recruiting_data.py`** handles multi-team, multi-year recruiting class
fetching. It's separate from `app.py` so the data pipeline can be tested
without running the Streamlit UI. The `@st.cache_data` decorator applies
conditionally: the function is defined inside a `try` block that imports
`streamlit`, falling back to an uncached version if that import fails
(i.e. when run as a standalone script).

### Key Challenge: Position Label Mismatch

The biggest data quality problem in the project was a labeling
inconsistency inside CFBD's own API: recruiting data and roster data use
different position labels for the same positions.

```
Roster label    CFBD recruiting labels
'OL'       →    'OT', 'OG', 'IOL', 'C'
'DL'       →    'DT', 'DE', 'EDGE', 'WDE', 'SDE'
'RB'       →    'RB', 'APB', 'FB'
'LB'       →    'LB', 'ILB', 'OLB', 'WLB', 'MLB'
```

Without a mapping layer, position filters on the Recruit Discovery page
return zero results for most positions. The fix is `RECRUIT_POSITION_MAP`,
a dict mapping each standard position group to its equivalent CFBD
recruiting labels. Page 3 filters with
`.isin(RECRUIT_POSITION_MAP[selected_position])`. Page 4 uses a reversed
version of the same map to group recruiting records into standard position
groups before charting.

### Team Name Validation

CFBD's naming conventions differ from common usage for about 10 FBS
programs. I found these by writing a script that hit CFBD's `/roster`
endpoint for all 134 programs in the tool's team database and flagged
which names came back empty.

Confirmed fixes from that pass:

| Common name | CFBD name |
|---|---|
| Appalachian State | App State |
| North Carolina State | NC State |
| Hawaii | Hawai'i |
| Ole Miss (common) | Ole Miss (CFBD) |
| San Jose State | San José State |
| UConn, UMass, Southern Miss, Sam Houston | Verified variants |

Testing every name against the live API caught mismatches that manual
inspection missed entirely.

---

## Analytical Features

### Roster Depth Dashboard

Shows current scholarship roster depth for any FBS program, grouped by
offensive, defensive, and special teams units. Each position is checked
against a defined threshold:

```python
POSITION_THRESHOLDS = {
    'QB':  (critical<=1, watch<=3),
    'OL':  (critical<=6, watch<=9),
    'WR':  (critical<=4, watch<=7),
    # ... all 12 tracked positions
}
```

These thresholds follow real roster construction logic, a team needs at
least 2 scholarship QBs to run practice rotations safely, and 6 OL to
field five starters plus a backup at each spot. Keeping thresholds
explicit and adjustable in one place matters: a tool that calls something
"critical" should say what number that means.

Critical positions trigger an alert panel above the depth tables with a
"Find Recruits" button. Clicking it stores the position in
`st.session_state` and navigates to Recruit Discovery with that position
pre-filled. A year selector (2021-2024) allows historical comparisons,
like how OL depth has changed over three years.

### Position Deep Dive

Two sections: a player table with transfer portal history, and a
horizontal bar chart comparing headcount at that position against
user-selected competitor programs.

The portal history column comes from querying CFBD's `/player/portal`
endpoint for 2021-2024, filtering to entries involving the selected team,
and matching against roster players via case-insensitive full-name
lookup. Display format: `Transfer In (Duke → Notre Dame, 2024)` or
`Transfer Out (Notre Dame → Alabama, 2023)`.

The competitor chart is horizontal rather than vertical, since with 4+
programs, vertical bars get too wide and text labels overlap. The x-axis
range pads dynamically to `max_val + max(2, 20% of max)` so labels don't
clip at the edge.

### Recruit Discovery

Filters the national recruit pool (all FBS programs, any class year
2025-2028) by position, star rating, and commitment status. The position
filter uses `RECRUIT_POSITION_MAP` to translate standard groups into
every equivalent CFBD recruiting label; without it, filtering by "OL"
would return nothing, since CFBD recruiting data uses "OT", "IOL", and
similar labels instead.

Below the recruit table sits a choropleth map of uncommitted recruit
density by state. Color scale runs from light blue (zero recruits) to
the selected team's brand color (maximum). Hovering a state shows the
top 3 uncommitted recruits by composite rating, with name, stars, and
rating. A side-by-side summary lists top states by recruit count and the
star rating breakdown for the current filters.

The choropleth replaced an earlier dot map because color intensity reads
as density faster than a cluster of dots. 12 California recruits as 12
dots in the middle of the state looked busy without telling you much; a
filled state does the job better.

### Recruiting Class Composition

Compares recruiting class composition across 2023-2025 for any team and
its selected competitors, across three tabs:

**Headcount by position**: raw volume, which programs sign more or fewer
players at each position group.

**Average star rating by position**: a quality lens. High headcount with
low stars points to volume recruiting; low headcount with high stars
points to a targeted approach.

**Gap analysis**, the most useful of the three. Computes
`selected_team_count - mean(competitor_counts)` at each position group.

```python
field_avg = pos_counts[pos_counts['team'] != selected_team]\
    .groupby('position_group')['count'].mean()
gap_df['delta'] = nd_counts['count'] - field_avg
```

Positive delta (team color) means recruiting above the competitor
average at that position; negative (red) means below. A gold zero line
separates the two, and plain-language bullet summaries sit below the
chart so the finding doesn't require reading the axis.

---

## Visualization Decisions

### Plotly for all charts

Plotly over Matplotlib or Altair because it produces interactive charts
(hover, zoom, click) natively, and integrates cleanly with Streamlit
through `st.plotly_chart()`. All charts share a `PLOTLY_LAYOUT` base dict
unpacked with `**` into each `fig.update_layout()` call for consistent
styling.

One constraint: `yaxis` and `margin` stay out of the shared dict. If
those keys show up in both the shared dict and an individual call,
Python raises `TypeError: multiple values for keyword argument`. Each
chart sets its own axis config instead.

### Team color system

All 134 FBS programs have a hardcoded primary brand hex color in
`TEAM_COLORS`. The selected team's color drives its bars and chart
highlights; competitors use their own brand colors. A Michigan vs. Ohio
State comparison shows maize vs. scarlet rather than generic grey bars.

### The "undefined" Plotly bug

During development, Plotly Express charts rendered the literal text
"undefined" above the legend. The figure's JSON on the Python side was
clean; that string wasn't in it anywhere.

Root cause: Streamlit bundles its own version of Plotly.js, which lags
behind the pip-installable Python package, and that bundled version
reads an unset `legend.title.text` as JavaScript `undefined`, then
renders it literally.

Fix: `legend=dict(title_text=' ', ...)`, a single space instead of an
empty string or no key at all. The space is invisible but counts as a
valid value, so the undefined path never runs.

---

## Deployment

The tool runs on Streamlit Community Cloud at a public URL. GitHub
integration means any push to main triggers an automatic redeploy. The
API key sits in Streamlit Cloud's secrets manager and never appears in
the source code or repo.

`requirements.txt` lists five direct dependencies (streamlit, pandas,
requests, python-dotenv, plotly) instead of a full `pip freeze` output.
Streamlit Cloud resolves transitive dependencies on its own, and a
minimal requirements file avoids version conflicts between local and
cloud environments.

`showErrorDetails = false` in `config.toml` suppresses raw Python
tracebacks on the deployed version, so end users never see internal file
paths or stack traces.

---

## What This Demonstrates

**API integration and data cleaning.** Working with a real third-party
API, handling inconsistent naming across endpoints, validating data
quality, and building a mapping layer to normalize mismatched labels.

**Applied data engineering.** A caching strategy for an API-heavy
interactive app, session state for cross-page navigation, and a clean
split between data pipeline logic and UI logic.

**Interactive visualization.** Picking chart types based on the
question, horizontal bars for program comparisons, choropleth for
geographic density, a gap chart for delta analysis, with consistent
theming and hover text that surfaces what actually matters per point.

**Software engineering basics.** A modular file structure, documented
functions and constants, and a clean separation between `app.py` and
`recruiting_data.py`.

**Domain knowledge.** Position thresholds grounded in real FBS roster
construction, competitor sets based on actual recruiting dynamics, and
CFBD's coverage limitations documented rather than glossed over.
