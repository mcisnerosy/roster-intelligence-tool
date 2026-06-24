# Technical Documentation
## CFB Roster Intelligence Tool

---

## Architecture Overview

The tool is a two-file Python application built on Streamlit. All UI logic,
page routing, and chart generation lives in `app.py`. All external API logic
for multi-team recruiting class data lives in `recruiting_data.py`. Both files
share API authentication via a module-level `HEADERS` dict but are otherwise
independent. `recruiting_data.py` can be run standalone for testing without
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

Data flows one direction: CFBD API to pandas DataFrame to Streamlit widget.
There's no database, no write operations, and no user authentication. Cross-page
state runs through `st.session_state` (e.g. flagging a critical position on
Page 1 pre-populates the position filter on Page 3).

---

## File Reference

### `app.py`

The main application file, 1,100+ lines covering all four pages, shared
constants, API helper functions, and the injected CSS theme. Streamlit
re-executes this file top-to-bottom on every user interaction, so all
persistent state uses `st.session_state` or `@st.cache_data`.

---

**`TEAM_COLORS` dict**

Maps all 134 FBS program names to their primary brand hex color. Used to
color each team's bars and highlights in Plotly charts. The selected team
always gets its own brand color, and competitors get theirs too, so a
Michigan vs. Ohio State comparison looks like maize vs. scarlet, not
generic grey bars.

Team names have to match CFBD's naming convention exactly. Known mismatches
from common usage, found and corrected:
- `"Appalachian State"` → `"App State"`
- `"North Carolina State"` → `"NC State"`
- `"Hawai'i"` (with okina)
- `"Ole Miss"` (not `"Mississippi"`)
- `"San José State"` (with accent)
- `"UConn"`, `"UMass"`, `"Southern Miss"`, `"Sam Houston"`

`FBS_TEAMS` is derived from `sorted(TEAM_COLORS.keys())`, so adding a new
program only requires an entry in `TEAM_COLORS`. New entries should be spot-checked
against the live `/roster` endpoint, since CFBD's naming isn't always what you'd guess.

---

**CSS theme block**

Injected via `st.markdown(..., unsafe_allow_html=True)`. Streamlit's
built-in theming via `config.toml` doesn't expose enough control for
this design, so direct CSS injection takes over instead.

Font pair: **Oswald** (headings, uppercase) + **Inter** (body, data tables),
both loaded from Google Fonts. Oswald shows up across college football
broadcast graphics and Nike/Adidas team kits, so it reads as "football"
without trying too hard.

Color system is team-aware. The selected team's `TEAM_COLOR` drives
highlights, active bars, and the darkest shade on the choropleth map.
The sidebar uses a neutral dark slate (`#0f0f1a` to `#1a1a2e`) so it works
for any team without clashing.

Known CSS workaround: Streamlit's sidebar selectbox renders white text on
white background when the sidebar is dark. Fixed by targeting
`.stSelectbox > div > div` directly with `!important` overrides, since
that internal class isn't exposed by Streamlit's theming API.

---

**`POSITION_GROUPS`**

Maps the three unit names to their position lists. Drives the expandable
sections on Page 1 and the position dropdown on Pages 2 and 3. Render order
is Offense, then Defense, then Special Teams.

---

**`POSITION_THRESHOLDS`**

Dict of `position → (red_max, yellow_max)` tuples encoding minimum viable
depth at each position for an FBS program.

```
count <= red_max    → 🔴 Critical
count <= yellow_max → 🟡 Watch
count > yellow_max  → 🟢 Healthy
```

Benchmarks follow standard FBS roster construction logic:
- QB: need 2+ scholarship players to run practice safely
- OL: need 6+ to field 5 starters plus 1 backup at each spot
- WR: need 4+ to run a full route tree in practice

Defined here instead of inline in the UI, so thresholds stay visible,
adjustable, and consistent across all four pages.

---

**`RECRUIT_POSITION_MAP`**

The most important constant in the codebase. It fixes a data quality issue
that would otherwise zero out Page 3's position filters: CFBD uses
different position labels for recruiting data than for roster data.

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

Shared base dict, unpacked with `**` into every `fig.update_layout()` call.
Holds only `plot_bgcolor`, `paper_bgcolor`, `font`, and `title_font`.
Leaves out `yaxis` and `margin` on purpose: if those keys show up in both
the shared dict and an individual chart's call, Python raises
`TypeError: multiple values for keyword argument 'yaxis'`.
Each chart defines its own `yaxis` and `margin` to dodge that.

---

**`build_color_map(team, comps)`**

Builds a Plotly `color_discrete_map` dict for a given team and competitor
list. The selected team gets its `TEAM_COLORS` entry, and each competitor
gets theirs too. If a team isn't in `TEAM_COLORS`, it falls back to
`COMP_GREYS` (progressively lighter slate greys).

---

**API helper functions**

All three use `@st.cache_data(ttl=3600)`. The first load fetches from CFBD
(1 to 3 seconds per call). Everything after that within the session reads
from cache and returns instantly. Cache is per-session on Streamlit Cloud's
free tier.

`get_roster(team, year)`: CFBD `/roster`. Key columns: `position`,
`firstName`, `lastName`, `year`, `height`, `weight`, `homeCity`,
`homeState`, `recruitIds` (empty list means no recruiting profile, i.e.
likely a walk-on). Used on Pages 1 and 2. Returns an empty DataFrame
silently on error; callers show the user a specific message instead.

`get_recruits(year)`: CFBD `/recruiting/players`. Fetches every recruit
for a class year; filtering by position, stars, and availability happens
downstream in Page 3. Key columns: `name`, `position` (CFBD recruiting
label), `stars`, `rating` (0.0 to 1.0 composite), `school`, `city`,
`stateProvince`, `committedTo` (None if uncommitted).

`get_portal_entries(year)`: CFBD `/player/portal`. Used on Page 2 to
build the Portal History column. Key columns: `firstName`, `lastName`,
`origin`, `destination`, `transferDate`. The matching code handles both
`origin`/`destination` and `originSchool`/`destinationSchool` field name
variants, since CFBD has used both across API versions.

`get_status(position, count)`: pure function, no caching needed. Returns
a `(status_label, badge_class)` tuple from `POSITION_THRESHOLDS`. The
`badge_class` maps to the CSS classes `.badge-red`, `.badge-yellow`,
`.badge-green` defined in the theme block.

---

**Page 1, Roster Depth Dashboard**

Year selector (2021 to 2024) sits inline with the page title in a
two-column layout via `st.columns([3, 1])`. Year feeds `get_roster()`,
cached per `(team, year)` combination, so switching years doesn't
re-fetch a year that's already loaded.

The alert panel renders above the depth tables when critical positions
exist. Each alert is a full-width `st.error()` with a compact "Find X"
button in a second column (`use_container_width=True`). Clicking sets
`st.session_state['recruit_position']` and calls `st.rerun()`, landing on
Page 3 with that position pre-selected.

Depth tables are a clean 3-column layout (Position, Count, Status), no
ACTION column. Keeping the alert panel separate from the tables keeps the
data display clean and the actionable items easy to spot.

---

**Page 2, Position Deep Dive**

The competitor multiselect lives at the top of the page, not in the
sidebar, on purpose. Pages 2 and 4 answer different questions, and a
user might want different competitors for each. Sidebar-level selection
would force the same comparison everywhere.

Portal history comes from looping over years 2021 to 2024, filtering
portal entries to rows where `origin` or `destination` contains the
selected team (case-insensitive), and building a
`lowercased_full_name → display_string` lookup. Display format:
`Transfer In (Duke → Notre Dame, 2024)` or
`Transfer Out (Notre Dame → Alabama, 2023)`.

Known limitation: name matching fails for players who go by nicknames
(e.g. "CJ" vs. "Cornelius") or when CFBD and roster spell a name
differently. Matching on CFBD player IDs would be more robust, but the
roster and portal endpoints don't return IDs in a consistent format.

The competitor chart is a horizontal `go.Bar`, chosen over vertical
because with 4+ programs, vertical bars get too wide and labels overlap.
The x-axis range pads out to `max_val + max(2, 20% of max)` so text
labels don't clip at the edge.

---

**Page 3, Recruit Discovery**

Filters apply in sequence:
1. Position: `recruits['position'].isin(RECRUIT_POSITION_MAP[pos])`
2. Stars: `recruits['stars'] >= min_stars`
3. Availability: `committedTo.isna()` / `.notna()` / no filter

The choropleth map uses `go.Choropleth` with `locationmode='USA-states'`
and 2-letter state abbreviations. Color scale runs from light blue
(#E8F0F8) to the selected team's brand color. Hover text is built per
state from the top 3 uncommitted recruits by composite rating, showing
name, stars, and rating. Only uncommitted recruits get plotted, so
switching to "Committed Only" or "All Recruits" correctly drops dots from
the map.

Session state cleanup: `recruit_position` gets deleted from
`st.session_state` at the end of the page so it doesn't carry over
unexpectedly the next time Page 3 loads.

---

**Page 4, Recruiting Class Composition**

Competitor multiselect at the top of the page, independent of Page 2's
selection. Calls `load_recruiting_data(teams=all_programs, years=[2023, 2024, 2025])`
where `all_programs = [selected_team] + list(competitors_p4)`.

Raw CFBD recruit positions map onto standard groups via a reversed
`RECRUIT_POSITION_MAP` lookup before charting.

Three tabs:
1. **Headcount**: grouped bar, recruits signed by position
2. **Avg Stars**: grouped bar, mean star rating by position, rounded to
   whole numbers since decimals aren't very informative on a 1 to 5 scale
3. **Gap Analysis**: `selected_team_count - mean(competitor_counts)` per
   position. Team color for positive bars (over-recruiting vs. peers),
   red for negative (under-recruiting). Gold zero line via
   `fig.add_hline()`. Plain-language bullet summaries below the chart.

---

### `recruiting_data.py`

Standalone module for multi-team, multi-year recruiting class data.
Importable by `app.py` and runnable directly via `python recruiting_data.py`.

**`fetch_recruiting_class(team, year)`**

Defined twice: once with `@st.cache_data(ttl=3600)` inside a try block
(Streamlit context), once without inside the except block (standalone
context). The try/except on `import streamlit as st` decides which
version runs. That way the function gets caching when run inside
Streamlit and works fine without it in a notebook or terminal.

**`load_recruiting_data(teams, years)`**

Loops every team/year combination. Default parameters stick around for
convenience, but Page 4 always passes `teams` and `years` explicitly.
Returns a concatenated DataFrame, or an empty one if every call fails.

**`analyze_recruiting_composition(df)`**

Returns composition, star distribution, and avg stars as summary dicts.
Not called by `app.py`, Page 4 does its own inline groupby logic instead
for UI flexibility. Kept here for notebook-based analysis.

---

### `requirements.txt`

Five packages, intentionally minimal:

```
streamlit==1.45.0    # Web framework and UI components
pandas==2.2.3        # Data manipulation and DataFrame operations
requests==2.32.3     # HTTP calls to CFBD API
python-dotenv==1.0.1 # .env file loading for local development
plotly==5.24.1       # Interactive charts and choropleth map
```

`numpy` is a transitive pandas dependency, imported inline for the
recruit map jitter calculation. Worth listing explicitly if the pandas
version ever changes.

---

### `.streamlit/config.toml`

```toml
[theme]
primaryColor = "#C99700"             # Gold, buttons and active states
backgroundColor = "#FFFFFF"          # Main content area
secondaryBackgroundColor = "#F0F4FA" # Widget backgrounds
textColor = "#1F1F1F"                # Body text
font = "sans serif"

[client]
showErrorDetails = false             # Suppress tracebacks on Streamlit Cloud
```

`primaryColor` is gold, not navy, because Streamlit uses `primaryColor`
for interactive highlights like button rings and active tabs. Navy on
white doesn't have enough contrast there; gold does.

`showErrorDetails = false` keeps raw Python tracebacks away from end
users on Streamlit Cloud.

---

## Caching Strategy

All three API helpers use `@st.cache_data(ttl=3600)`:

| Call | First load | Cached load | Calls per session |
|---|---|---|---|
| `get_roster(team, year)` | ~1s | instant | 1 per team+year combo |
| `get_recruits(year)` | ~2s | instant | 1 per year |
| `get_portal_entries(year)` | ~1s | instant | 4 (years 2021-2024) |
| `fetch_recruiting_class(team, year)` | ~1s | instant | up to 15 (5 teams x 3 years) |

A 1-hour TTL fits since CFBD data updates at most once a day. Shorter
causes unnecessary API calls; longer risks stale data during an active
transfer portal window or signing day.

---

## Known Limitations

**Team name matching.** CFBD's naming differs from common usage for
about 10 programs. Known mismatches are corrected in `TEAM_COLORS`; new
additions should be spot-checked against the live `/roster` endpoint.

**Portal name matching.** Uses lowercased full-name string comparison.
Fails for nicknames or when CFBD and roster spell a name differently. A
player ID-based match would be more reliable, but CFBD doesn't return
consistent IDs across the roster and portal endpoints.

**~70% roster coverage.** CFBD links roster players to recruiting
profiles through an internal ID system. Players without a profile
(walk-ons, some transfers, some international players) still show up on
the roster but may be undercounted elsewhere. Documented on every page.

**2025 recruiting class.** Incomplete until National Signing Day. The
year filter defaults to 2025 on Page 3, with a note in the sidebar
explaining the gap.

**Louisiana-Monroe (ULM).** Exists in CFBD's team database but has no
roster data for any year tested (2021-2024). Stays in the team selector
under the correct CFBD name `"Louisiana-Monroe"`; selecting it shows the
empty roster message.
