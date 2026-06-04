# Notre Dame Roster Intelligence Tool

A data-driven tool to analyze Notre Dame football roster depth, identify recruiting gaps, and benchmark recruiting strategy against elite programs.

**Live App:** [https://share.streamlit.io/mcisnerosy/roster-intelligence-tool/main/app.py](https://share.streamlit.io/mcisnerosy/roster-intelligence-tool/main/app.py)

---

## What This Tool Does

The Roster Intelligence Tool helps recruiting staff:
- **See roster gaps** by position in real-time
- **Identify underutilized positions** and flag critical needs
- **Discover available recruits** that match recruiting priorities
- **Benchmark recruiting strategy** against Georgia, Ohio State, and Alabama

Four pages, four workflows.

---

## The Four Pages

### 1. **Roster Depth Dashboard**
See Notre Dame's current roster at a glance. 
- Positions organized by unit (Offense, Defense, Special Teams)
- Color-coded status: 🟢 Healthy, 🟡 Watch, 🔴 Critical
- Flagged alerts section shows positions that need immediate recruiting attention
- Quick jump to recruit discovery from critical positions

### 2. **Position Deep Dive**
Drill into a specific position.
- Full roster table: name, year, height, weight, hometown, walk-on indicator
- Competitor headcount comparison (Ohio State, Georgia, Alabama)
- See how Notre Dame stacks up position-by-position

### 3. **Recruit Discovery**
Find recruits that fill roster gaps.
- Filter by position, recruiting class year, minimum star rating
- Availability filter: All recruits, uncommitted only, or committed only
- Sorted by rating so top prospects appear first
- Integrates with Roster Depth Dashboard—flag a critical position, jump here to find recruits

### 4. **Recruiting Class Composition**
Compare recruiting strategy across programs.
- Grouped bar chart showing recruit count by position for ND, Georgia, Ohio State, Alabama
- Identifies where Notre Dame is over-recruiting or under-recruiting relative to elite programs
- Raw data table for detailed comparison

---

## Data Quality & Limitations

**Important:** Roster counts reflect CFBD-linked profiles (~70% of actual roster coverage). 

- Walk-ons and recent transfers may not appear
- Some player data is incomplete or outdated
- Use position thresholds and flags as a **starting point** for roster evaluation, not the definitive source
- Always cross-reference with internal ND roster management systems

---

## Local Development

### Setup

```bash
# Clone the repo
git clone https://github.com/mcisnerosy/roster-intelligence-tool.git
cd roster-intelligence-tool

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with your API key
echo "CFBD_API_KEY=your_api_key_here" > .env

# Run the app
streamlit run app.py
```

The app will open at `http://localhost:8501`.

### API Key

Get your CFBD API key from [collegefootballdata.com](https://collegefootballdata.com).

For Streamlit Cloud deployment, add the API key via the Secrets tab in your app settings (not as environment variable).

---

## File Structure

```
roster-intelligence-tool/
├── app.py                 # Main Streamlit app (all four pages)
├── recruiting_data.py     # CFBD API functions for recruiting data
├── requirements.txt       # Python dependencies
├── .env                   # Local API key (not committed)
├── .gitignore             # Git ignore rules
├── .streamlit/
│   ├── config.toml        # Streamlit theme configuration
│   └── secrets.toml       # Secrets for Cloud (not committed)
└── README.md
```

---

## How It Works

**Data Source:** [College Football Data (CFBD) API](https://collegefootballdata.com)

**Tech Stack:**
- Python 3
- Streamlit (web framework)
- Pandas (data manipulation)
- Plotly (interactive charts)
- Deployed on Streamlit Community Cloud

**Real-time Updates:**
- Roster data pulled on-demand from CFBD API
- Charts and tables update automatically based on current data

---

## Future Roadmap

### V1.1 (Planned)
- Transfer portal filtering
- Data quality improvements (better walk-on detection)
- Recruiting class timeline view (when commits arrive on campus)

### V2+ (TBD based on feedback)
- Roster projection model (forecast depth 2+ years out)
- Recruiting efficiency tracking (offer-to-commit conversion by position)
- Recruiting class quality vs. championship rosters analysis

---

## Questions or Feedback?

Built by Marcos Cisneros

For bugs, feature requests, or data questions, reach out directly.