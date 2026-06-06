# Technical Documentation
## CFB Roster Intelligence Tool

---

## Architecture Overview

The tool is a two-file Python application built on Streamlit. All UI logic,
page routing, and chart generation lives in `app.py`. All external API logic
for multi-team recruiting class data lives in `recruiting_data.py`. Both files
share API authentication via a module-level `HEADERS` dict but are otherwise
independent — `recruiting_data.py` can be run standalone for testing without
launching the Streamlit UI.

```
User browser
    │
    ▼
Streamlit runtime (app.py)
    ├── Sidebar: team selector + page navigation
    ├── Page routing via st.sidebar.selectbox
    ├── Cached API calls via @st.cache_data(ttl=3600)
    │       ├── get_roster(team, year)     → CFBD /roster
    │       ├── get_recruits(year)         → CFBD /recruiting/players
    │       └── get_portal_entries(year)   → CFBD /player/portal
    │
    └── recruiting_data.py
            └── load_recruiting_data(teams, years)
                    └── fetch_recruiting_class(team, year) [cached per team+year]
```

Data flows in one direction: CFBD API → pandas DataFrame → Streamlit widget.
There is no database, no write operations, and no user authentication. Cross-page
state is managed via `st.session_state` (e.g., flagging a critical position on
Page 1 pre-populates the position filter on Page 3).

---

## File Reference

### `app.py`

The main application file. 1,100+ lines covering all four pages, shared
constants, API helper functions, and the injected CSS theme. Streamlit
re-executes this file top-to-bottom on every user interaction, so all
persistent state uses `st.session_state` or `@st.cache_data`.

---

**Module docstring**

Documents the full architecture, data flow, API endpoints used per page,
and deployment environment handling (Streamlit Cloud vs. local).

---

**`TEAM_COLORS` dict**

Maps all 134 FBS program names to their primary brand hex color. Used to
color each team's bars and highlights in Plotly charts. The selected team
always gets its own brand color; competitors get their brand colors too —
so a Michigan vs. Ohio State comparison looks like maize vs. scarlet, not
generic grey bars.

Team names must match CFBD's naming convention exactly. Known mismatches
from common usage that were identified and corrected:
- `"Appalachian State"` → `"App State"`
- `"North Carolina State"` → `"NC State"`
- `"Hawai'i"` (with okina)
- `"Ole Miss"` (not `"Mississippi"`)
- `"San José State"` (with accent)
- `"UConn"`, `"UMass"`, `"Southern Miss"`, `"Sam Houston"`

`FBS_TEAMS` is derived from `sorted(TEAM_COLORS.keys())` — adding a new
program requires only an entry in `TEAM_COLORS`.

`test_teams.py` verifies every name against the live CFBD API and reports
any that return empty rosters.

---

**CSS theme block**

Injected via `st.markdown(..., unsafe_allow_html=True)`. Streamlit's
built-in theming via `config.toml` does not expose enough control for
this design, so direct CSS injection is used instead.

Font pair: **Oswald** (headings, uppercase) + **Inter** (body, data tables).
Both loaded from Google Fonts. Oswald is used across college football
broadcast graphics and Nike/Adidas team kits — reads as "football"
immediately without being a gimmick.

Color system: team-color-aware. The selected team's `TEAM_COLOR` is used
for highlights, active bars, and the darkest shade on the choropleth map.
The sidebar uses a neutral dark slate (`#0f0f1a → #1a1a2e`) so it works
for any team without clashing.

Known CSS workaround: Streamlit's sidebar selectbox renders white text on
white background when the sidebar background is dark. Fixed by explicitly
targeting `.stSelectbox > div > div` with `!important` overrides — this
internal class isn't exposed by Streamlit's theming API.

---

**`POSITION_GROUPS`**

Maps the three unit names to their position lists. Drives the expandable
sections on Page 1 and the position dropdown on Pages 2–3. Render order
is Offense → Defense → Special Teams.

---

**`POSITION_THRESHOLDS`**

Dict of `position → (red_max, yellow_max)` tuples encoding minimum viable
depth at each position for an FBS program.

```
count <= red_max    → 🔴 Critical
count <= yellow_max → 🟡 Watch
count > yellow_max  → 🟢 Healthy
```

Benchmarks are based on standard FBS roster construction logic:
- QB: need 2+ scholarship players to run practice safely
- OL: need 6+ to field 5 starters plus 1 backup at each spot
- WR: need 4+ to run a full route tree in practice

Defined here rather than inline in the UI so thresholds are visible,
adjustable, and consistent across all four pages.

---

**`RECRUIT_POSITION_MAP`**

The most important constant in the codebase. Solves a data quality issue
that would otherwise cause Page 3 position filters to return zero results:
CFBD uses different position labels for recruiting data vs. roster data.

```
Roster label → CFBD recruiting labels
'OL'         → ['OT', 'OG', 'IOL', 'C', 'OL']
'DL'         → ['DT', 'DE', 'EDGE', 'DL', 'WDE', 'SDE']
'RB'         → ['RB', 'APB', 'FB']
'LB'         → ['LB', 'ILB', 'OLB', 'WLB', 'MLB']
```

Page 3 filters recruits using `.isin(RECRUIT_POSITION_MAP[selected_position])`.
Page 4 uses a reversed version of this map to group all recruiting data into
standard position groups before charting.

---

**`PLOTLY_LAYOUT`**

Shared base dict unpacked with `**` into every `fig.update_layout()` call.
Contains only `plot_bgcolor`, `paper_bgcolor`, `font`, and `title_font`.
Intentionally excludes `yaxis` and `margin` — if those keys appear in both
the shared dict and an individual chart's call, Python raises:
`TypeError: multiple values for keyword argument 'yaxis'`
Each chart defines its own `yaxis` and `margin` to avoid this.

---

**`build_color_map(team, comps)`**

Builds a Plotly `color_discrete_map` dict for a given team + competitor
list. The selected team gets its `TEAM_COLORS` entry; each competitor also
gets its `TEAM_COLORS` entry. If a team isn't in `TEAM_COLORS`, falls back
to `COMP_GREYS` (a list of progressively lighter slate greys).

---

**API helper functions**

All three use `@st.cache_data(ttl=3600)`. First load fetches from CFBD
(1–3 seconds per call). Subsequent interactions within the session use
cached data (instant). Cache is per-session on Streamlit Cloud free tier.

`get_roster(team, year)` — CFBD `/roster`. Key columns: `position`,
`firstName`, `lastName`, `year`, `height`, `weight`, `homeCity`,
`homeState`, `recruitIds` (empty list = no recruiting profile/walk-on).
Used on Pages 1 and 2. Returns empty DataFrame silently on error —
callers show the user a specific message.

`get_recruits(year)` — CFBD `/recruiting/players`. Fetches ALL recruits
for a class year; filtering by position, stars, and availability happens
downstream in Page 3 logic. Key columns: `name`, `position` (CFBD
recruiting label), `stars`, `rating` (0.0–1.0 composite), `school`,
`city`, `stateProvince`, `committedTo` (None if uncommitted).

`get_portal_entries(year)` — CFBD `/player/portal`. Used on Page 2 to
build the Portal History column. Key columns: `firstName`, `lastName`,
`origin`, `destination`, `transferDate`. The matching code handles both
`origin`/`destination` and `originSchool`/`destinationSchool` field name
variants across API versions.

`get_status(position, count)` — pure function, no caching needed. Returns
`(status_label, badge_class)` tuple using `POSITION_THRESHOLDS`. The
`badge_class` maps to CSS classes `.badge-red`, `.badge-yellow`,
`.badge-green` defined in the theme block.

---

**Page 1 — Roster Depth Dashboard**

Year selector (2021–2024) sits inline with the page title — a two-column
layout using `st.columns([3, 1])`. Year is passed to `get_roster()`, which
is cached per `(team, year)` combination, so switching years doesn't
re-fetch a previously loaded year.

Alert panel renders above the depth tables when critical positions exist.
Each alert is a full-width `st.error()` with a compact "Find X →" button
in a second column using `use_container_width=True`. Clicking sets
`st.session_state['recruit_position']` and calls `st.rerun()`, which
navigates to Page 3 with that position pre-selected.

Depth tables are a clean 3-column layout (Position, Count, Status) — no
ACTION column. Separating the alert panel from the tables keeps the data
display clean and the actionable items prominent.

---

**Page 2 — Position Deep Dive**

Competitor multiselect lives at the top of the page, not in the sidebar.
This is intentional — Pages 2 and 4 serve different analytical questions
and a user might want different competitors for each. Sidebar-level
competitor selection would force the same comparison everywhere.

Portal history is built by looping over years 2021–2024, filtering portal
entries to rows where `origin` or `destination` contains the selected team
(case-insensitive), and building a `lowercased_full_name → display_string`
lookup dict. Display format: `Transfer In (Duke → Notre Dame, 2024)` or
`Transfer Out (Notre Dame → Alabama, 2023)`.

Known limitation: name matching fails for players who go by nicknames
(e.g. "CJ" vs. "Cornelius") or when CFBD and roster use different
spellings. A more robust solution would match on CFBD player IDs, but
the roster and portal endpoints don't consistently return IDs in the same
format.

Competitor chart is a horizontal `go.Bar` — chosen over vertical because
with 4+ programs, vertical bars are too wide and labels overlap. The
x-axis range is padded to `max_val + max(2, 20% of max)` to prevent
text labels from clipping at the chart edge.

---

**Page 3 — Recruit Discovery**

Filters applied sequentially:
1. Position: `recruits['position'].isin(RECRUIT_POSITION_MAP[pos])`
2. Stars: `recruits['stars'] >= min_stars`
3. Availability: `committedTo.isna()` / `.notna()` / no filter

Choropleth map uses `go.Choropleth` with `locationmode='USA-states'` and
2-letter state abbreviations. Color scale runs from light blue (#E8F0F8)
to the selected team's brand color. Hover text is built per state from
the top 3 uncommitted recruits by composite rating, showing name, stars,
and rating. Only uncommitted recruits are plotted — selecting "Committed
Only" or "All Recruits" correctly shows zero/fewer dots on the map.

Session state cleanup: `recruit_position` is deleted from
`st.session_state` at the end of the page so it doesn't persist
unexpectedly on the next Page 3 visit.

---

**Page 4 — Recruiting Class Composition**

Competitor multiselect at page top (independent of Page 2 selection).
Calls `load_recruiting_data(teams=all_programs, years=[2023, 2024, 2025])`
where `all_programs = [selected_team] + list(competitors_p4)`.

Raw CFBD recruit positions are mapped to standard groups via a reversed
`RECRUIT_POSITION_MAP` lookup before charting.

Three tabs:
1. **Headcount** — grouped bar, recruits signed by position
2. **Avg Stars** — grouped bar, mean star rating by position (rounded to
   whole numbers; decimals are uninformative for 1–5 scale)
3. **Gap Analysis** — `selected_team_count - mean(competitor_counts)` per
   position. Bars use team color for positive (over-recruiting vs. peers)
   and red for negative (under-recruiting). Gold zero line added via
   `fig.add_hline()`. Plain-language bullet summaries rendered below.

---

### `recruiting_data.py`

Standalone module for multi-team, multi-year recruiting class data.
Importable by `app.py` and runnable directly via `python recruiting_data.py`.

**`fetch_recruiting_class(team, year)`**

Defined twice — once with `@st.cache_data(ttl=3600)` inside a try block
(Streamlit context), once without inside the except block (standalone
context). The try/except on `import streamlit as st` determines which
version is active. This pattern allows the function to be cached when
running inside Streamlit and uncached when running in a notebook or
terminal without error.

**`load_recruiting_data(teams, years)`**

Loops all team/year combinations. Default parameters are kept for
backward compatibility but Page 4 always passes `teams` and `years`
explicitly. Returns concatenated DataFrame or empty DataFrame if all
calls fail.

**`analyze_recruiting_composition(df)`**

Utility function returning composition, star distribution, and avg stars
summary dicts. Not called by `app.py` — Page 4 does inline groupby logic
for UI flexibility. Kept for notebook-based analysis.

---

### `requirements.txt`

Five packages — intentionally minimal:

```
streamlit==1.45.0    # Web framework and UI components
pandas==2.2.3        # Data manipulation and DataFrame operations
requests==2.32.3     # HTTP calls to CFBD API
python-dotenv==1.0.1 # .env file loading for local development
plotly==5.24.1       # Interactive charts and choropleth map
```

`numpy` is a transitive pandas dependency, imported inline for the
recruit map jitter calculation. Explicit listing recommended if pandas
version changes.

---

### `.streamlit/config.toml`

```toml
[theme]
primaryColor = "#C99700"             # Gold — buttons and active states
backgroundColor = "#FFFFFF"          # Main content area
secondaryBackgroundColor = "#F0F4FA" # Widget backgrounds
textColor = "#1F1F1F"                # Body text
font = "sans serif"

[client]
showErrorDetails = false             # Suppress tracebacks on Streamlit Cloud
```

`primaryColor` is gold rather than navy — Streamlit uses `primaryColor`
for interactive highlights (button rings, active tabs). Navy on white has
insufficient contrast; gold is visually distinct.

`showErrorDetails = false` prevents raw Python tracebacks from being
visible to end users on Streamlit Cloud.

---

### `test_teams.py`

Utility script for verifying CFBD team name coverage. Hits the `/roster`
endpoint for every team in `TEAM_COLORS` and reports which names return
data vs. empty. Run locally with `python test_teams.py` after adding new
teams or when investigating a team that shows "no roster data" in the app.

---

## Caching Strategy

All three API helpers use `@st.cache_data(ttl=3600)`:

| Call | First load | Cached load | Calls per session |
|---|---|---|---|
| `get_roster(team, year)` | ~1s | instant | 1 per team+year combo |
| `get_recruits(year)` | ~2s | instant | 1 per year |
| `get_portal_entries(year)` | ~1s | instant | 4 (years 2021–2024) |
| `fetch_recruiting_class(team, year)` | ~1s | instant | up to 15 (5 teams × 3 years) |

The 1-hour TTL is appropriate — CFBD data updates at most once per day.
A shorter TTL causes unnecessary API calls; a longer one risks showing
stale data during active transfer portal or signing day cycles.

---

## Known Limitations

**Team name matching** — CFBD uses its own naming conventions that differ
from common usage for ~10 programs. All known mismatches are corrected in
`TEAM_COLORS`. `test_teams.py` surfaces any remaining issues.

**Portal name matching** — uses lowercased full-name string comparison.
Fails for players who go by nicknames or when CFBD and roster use different
spellings. A player ID-based match would be more robust but CFBD doesn't
return consistent IDs across the roster and portal endpoints.

**~70% roster coverage** — CFBD links roster players to recruiting profiles
via an internal ID system. Players without profiles (walk-ons, some
transfers, some international players) appear in roster data but may be
undercounted. The tool documents this limitation on every page.

**2025 recruiting class** — incomplete until National Signing Day. The year
filter defaults to 2025 on Page 3; a note in the sidebar explains the
coverage limitation.

**Louisiana-Monroe (ULM)** — exists in CFBD's team database but has no
roster data for any year tested (2021–2024). Included in the team selector
with the correct CFBD name `"Louisiana-Monroe"`; selecting it shows the
empty roster message.