# ☘️ Notre Dame Roster Intelligence Tool

A data-driven Streamlit app for analyzing Notre Dame football roster depth, surfacing recruiting gaps, and benchmarking recruiting strategy against elite programs.

**Live App:** [roster-intelligence-tool.streamlit.app](https://roster-intelligence-tool.streamlit.app)

> **Data source:** [College Football Data API (CFBD)](https://collegefootballdata.com) — ~70% FBS roster coverage. Walk-ons and recently transferred players may not appear. Cross-reference with internal systems before acting on alerts.

---

## What It Does

College football staff spend time manually tracking roster depth in spreadsheets. This tool pulls live roster and recruiting data from the CFBD API and surfaces the information that matters to a recruiting department in four focused views.

---

## The Four Pages

### 1. Roster Depth Dashboard
Current Notre Dame roster depth by position group with defined thresholds for what constitutes a critical gap.

- Positions organized by unit (Offense, Defense, Special Teams)
- Color-coded status per position: 🟢 Healthy · 🟡 Watch · 🔴 Critical
- Threshold logic is explicit (e.g., fewer than 2 scholarship QBs = Critical)
- One-click navigation from a flagged position directly to Recruit Discovery
<img width="2340" height="1304" alt="image" src="https://github.com/user-attachments/assets/18ea85ed-d778-4fb0-bfc7-07776f2f43c4" />

### 2. Position Deep Dive
Full player table for a selected position plus competitor headcount.

- Name, year, height, weight, hometown, walk-on indicator
- Bar chart comparing Notre Dame headcount vs. Ohio State, Georgia, Alabama at that position
- Walk-on detection based on presence of CFBD recruiting profile
<img width="2340" height="1300" alt="image" src="https://github.com/user-attachments/assets/8173114c-c418-410c-b87e-f1d45ca57fb1" />

### 3. Recruit Discovery
Filter the national recruit pool to find prospects that address identified gaps.

- Filters: position, class year (2025–2028), minimum star rating, commitment status
- Position mapping translates CFBD recruiting labels (OT, IOL, EDGE) to standard groups (OL, DL)
- Sorted by composite rating. Top prospects first
- Pre-populates position when navigated from a Page 1 alert
<img width="2308" height="1362" alt="image" src="https://github.com/user-attachments/assets/fa95fea1-8db3-4f73-afe9-dcd1440d7b5c" />

### 4. Recruiting Class Composition
Side-by-side comparison of Notre Dame's recruiting class composition vs. peer programs.

- Headcount by position group. 2023–2025 combined classes
- Average star rating by position group. Identifies quality vs. volume tradeoffs
- Programs compared: Notre Dame, Georgia, Ohio State, Alabama
<img width="2340" height="1400" alt="image" src="https://github.com/user-attachments/assets/f19b7c8c-f7de-44eb-8bfc-6343fd68954d" />

---

## Key Design Decisions

**Why those four competitor programs?** Ohio State, Georgia, and Alabama represent three distinct recruiting models, Ohio State (Midwest pipeline), Georgia (SEC dominance), Alabama (national reach), that Notre Dame competes with directly for top recruits.

**Why headcount thresholds?** Standard college football roster construction guidelines suggest a minimum of 2 scholarship QBs, 6 OL, 4 WR, etc. for a healthy depth chart. These thresholds are defined explicitly in `app.py` and can be adjusted.

**Why CFBD?** It's the most comprehensive free API for college football roster and recruiting data, with documented endpoints and consistent structure going back to 2014.

---

## Data Quality Notes

| Issue | Impact | Mitigation |
|---|---|---|
| ~70% roster coverage | Some players missing | Note shown on dashboard |
| Walk-on detection via recruitIds | Inaccurate for some transfers | Labeled "No Profile" not "Walk-On" |
| CFBD recruiting positions ≠ roster positions | Filters return wrong results without mapping | Position mapping dict in app.py |
| 2025 class data incomplete until signing day | Undercounts current cycle | Year filter defaults to 2025; caveat in UI |

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

1. Push repo to GitHub (ensure `.env` and `secrets.toml` are in `.gitignore`)
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app → select this repo
3. Set main file path to `app.py`
4. Under **Advanced settings → Secrets**, add:
   ```toml
   CFBD_API_KEY = "your_key_here"
   ```
5. Deploy — live in ~2 minutes

---

## File Structure

```
roster-intelligence-tool/
├── app.py                  # Main Streamlit app — all four pages
├── recruiting_data.py      # CFBD recruiting API helpers (cached)
├── requirements.txt        # Pinned dependencies
├── .env                    # Local API key — NOT committed
├── .gitignore
├── .streamlit/
│   ├── config.toml         # Theme — Notre Dame navy/gold
│   └── secrets.toml        # Cloud API key — NOT committed
└── README.md
```

---

## Roadmap

**V1.1**
- Transfer portal layer — flag players who entered the portal in prior cycles
- Eligibility column on player table (years remaining)
- State-level recruit map on Recruit Discovery page

**V2**
- Roster projection model — forecast depth 2+ years out by class year
- Offer-to-commit conversion rate by position
- Recruiting class quality vs. CFP roster composition analysis

---

This project was built with assistance from Claude (Anthropic) via Claude Code for debugging, API integration, and code structure. Project direction, analytical framing, and interpretation of findings were the author's own.

Built by [Marcos Cisneros](https://github.com/mcisnerosy)
