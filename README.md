# 🏈 CFB Roster Intelligence Tool

A Streamlit app for tracking college football roster depth and recruiting gaps, for any FBS program.

**Live App:** [roster-intelligence-tool.streamlit.app](https://roster-intelligence-tool.streamlit.app)

> **Data source:** [College Football Data API (CFBD)](https://collegefootballdata.com), roughly 70% FBS roster coverage. Walk-ons and recent transfers may not appear. Cross-reference with internal systems before acting on alerts.

---

## What It Does

Recruiting staff often track roster depth by hand in spreadsheets. This tool pulls live roster and recruiting data from the CFBD API across four pages. Pick a team in the sidebar, and every page, chart, and threshold follows that team.

---

## The Four Pages

### 1. Roster Depth Dashboard
Roster depth for the selected team by position group, with thresholds for what counts as a gap.

- Positions grouped by unit (Offense, Defense, Special Teams)
- Color-coded status per position: 🟢 Healthy · 🟡 Watch · 🔴 Critical
- Thresholds are explicit, e.g. fewer than 2 scholarship QBs is Critical
- Season selector covering 2021 to 2024
- One click from a flagged position into Recruit Discovery

<img width="2340" height="1304" alt="image" src="https://github.com/user-attachments/assets/18ea85ed-d778-4fb0-bfc7-07776f2f43c4" />

### 2. Position Deep Dive
Player table for one position, plus transfer portal history and a competitor comparison.

- Name, year, height, weight, hometown, walk-on indicator
- Transfer portal history column (in or out, year, origin/destination), from CFBD's portal endpoint
- Bar chart comparing headcount against up to 4 competitor programs at that position
- Walk-on flag based on whether the player has a CFBD recruiting profile

<img width="2340" height="1300" alt="image" src="https://github.com/user-attachments/assets/8173114c-c418-410c-b87e-f1d45ca57fb1" />

### 3. Recruit Discovery
Filters the national recruit pool down to prospects that match an identified gap.

- Filters: position, class year (2025 to 2028), minimum star rating, commitment status
- Maps CFBD's recruiting labels (OT, IOL, EDGE) onto roster position groups (OL, DL); the two use different naming
- Sorted by composite rating, top prospects first
- Choropleth map of uncommitted recruits by state, top 3 per state on hover
- Pre-fills the position filter when arriving from a Page 1 alert

<img width="2308" height="1362" alt="image" src="https://github.com/user-attachments/assets/fa95fea1-8db3-4f73-afe9-dcd1440d7b5c" />

### 4. Recruiting Positioning
Compares the selected team's recruiting class against chosen competitors.

- Headcount by position group, 2023 to 2025 classes combined
- Average star rating by position group, to see quality vs. volume
- Gap tab showing where the team recruits above or below the competitor average, by position
- Pick up to 4 competitors, set independently of the other pages

<img width="2340" height="1400" alt="image" src="https://github.com/user-attachments/assets/f19b7c8c-f7de-44eb-8bfc-6343fd68954d" />

---

## Key Design Decisions

**Why a team selector instead of one fixed team?** The first version was built just for Notre Dame. Switching teams now recolors the charts to that team's brand color and reruns the position math against that team's roster.

**Why does each page pick its own competitors?** Page 2 and Page 4 answer different questions, so each gets its own competitor list (up to 4) instead of one shared sidebar selection.

**Why these headcount thresholds?** They follow common roster construction rules of thumb, like needing 2+ scholarship QBs or 6+ OL. Defined in `app.py`, easy to adjust.

**Why CFBD?** It's the most complete free API for college football roster and recruiting data, with consistent coverage back to 2014.

---

## Data Quality Notes

| Issue | Impact | Mitigation |
|---|---|---|
| ~70% roster coverage | Some players missing | Noted on the dashboard |
| Walk-on detection via recruitIds | Inaccurate for some transfers | Labeled "No Profile," not "Walk-On" |
| CFBD recruiting positions don't match roster positions | Filters return nothing without a mapping | `RECRUIT_POSITION_MAP` in app.py |
| 2025 class data incomplete until signing day | Undercounts the current cycle | Year filter defaults to 2025; caveat shown in UI |
| Portal name matching is string-based | Misses nicknames, e.g. "CJ" vs "Cornelius" | Best-effort match, not used for alerts |

---

## Local Setup

```bash
git clone https://github.com/mcisnerosy/roster-intelligence-tool.git
cd roster-intelligence-tool

python3 -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

pip install -r requirements.txt

# Create .env with your API key
echo "CFBD_API_KEY=your_key_here" > .env

streamlit run app.py
# Opens at http://localhost:8501
```

Get a free CFBD API key at [collegefootballdata.com](https://collegefootballdata.com).

---

## Streamlit Cloud Deployment

1. Push the repo to GitHub (keep `.env` and `secrets.toml` in `.gitignore`)
2. Go to [share.streamlit.io](https://share.streamlit.io), New app, select this repo
3. Set the main file path to `app.py`
4. Under Advanced settings, Secrets, add:
   ```toml
   CFBD_API_KEY = "your_key_here"
   ```
5. Deploy. Live in a couple minutes.

---

## File Structure

```
roster-intelligence-tool/
├── app.py                  # Streamlit app: team selector, theme, all four pages
├── recruiting_data.py      # CFBD recruiting API calls (cached)
├── data_exploration.ipynb  # Notebook for poking at the raw data
├── requirements.txt        # Dependencies
├── .env                    # Local API key, not committed
├── .gitignore
├── .streamlit/
│   ├── config.toml         # Base theme config
│   └── secrets.toml        # Cloud API key, not committed
└── README.md
```

---

## Roadmap

**V2.1**
- Eligibility column on the player table (years remaining)
- Roster projection model: forecast depth a couple years out by class year
- Offer-to-commit conversion rate by position

**V3**
- Recruiting class quality vs. CFP roster composition
- Saved team/competitor presets per session

Full version history, including the move from single-team to multi-team, is in [CHANGELOG.md](CHANGELOG.md).

---

This project was built with assistance from Claude (Anthropic) via Claude Code for debugging, API integration, and code structure. Project direction, analytical framing, and interpretation of findings were the author's own.

Built by [Marcos Cisneros](https://github.com/mcisnerosy)
