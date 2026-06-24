"""
app.py: CFB Roster Intelligence Tool
=======================================
Main Streamlit application. Handles all UI rendering, page routing,
API calls for roster and portal data, and chart generation.

Architecture:
  - Single-file Streamlit app. Streamlit re-executes this file top-to-bottom
    on every user interaction, so all state must be managed via st.session_state
    or cached via @st.cache_data.
  - API calls for recruiting class data are delegated to recruiting_data.py
    to keep this file focused on UI logic.
  - All four pages share the same HEADERS, constants, and helper functions
    defined in the module-level sections below.

Pages:
  1. Roster Depth Dashboard  - depth by position with color-coded alerts + year selector
  2. Position Deep Dive       - player table + portal history + competitor headcount chart
  3. Recruit Discovery        - national recruit filter + choropleth map
  4. Recruiting Positioning   - recruiting class composition vs. chosen competitors

Data source: College Football Data API (https://collegefootballdata.com)
  - /roster             → Pages 1 and 2
  - /recruiting/players → Pages 3 and 4 (via recruiting_data.py)
  - /player/portal      → Page 2 portal history column

Deployment:
  - Streamlit Cloud: API key stored in st.secrets['CFBD_API_KEY']
  - Local: API key loaded from .env via python-dotenv
"""

import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from dotenv import load_dotenv
import streamlit as st
from recruiting_data import load_recruiting_data

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title='CFB Roster Intelligence',
    page_icon='🏈',
    layout='wide',
    initial_sidebar_state='expanded'
)

# ---------------------------------------------------------------------------
# Team color database: primary color for every FBS program
# Used to color that team's bar/highlight in charts
# ---------------------------------------------------------------------------
TEAM_COLORS = {
    'Air Force':              '#003087',
    'Akron':                  '#041E42',
    'Alabama':                '#9E1B32',
    'App State':              '#FFB300',
    'Arizona':                '#CC0033',
    'Arizona State':          '#8C1D40',
    'Arkansas':               '#9D2235',
    'Arkansas State':         '#CC0000',
    'Army':                   '#FFD700',
    'Auburn':                 '#0C2340',
    'Ball State':             '#BA0C2F',
    'Baylor':                 '#154734',
    'Boise State':            '#0033A0',
    'Boston College':         '#8B0000',
    'Bowling Green':          '#4F2C1D',
    'Buffalo':                '#005BBB',
    'BYU':                    '#002E5D',
    'California':             '#003262',
    'Central Michigan':       '#6A0032',
    'Charlotte':              '#046A38',
    'Cincinnati':             '#E00122',
    'Clemson':                '#F66733',
    'Coastal Carolina':       '#006F51',
    'Colorado':               '#CFB87C',
    'Colorado State':         '#1E4D2B',
    'UConn':            '#000E2F',
    'Duke':                   '#003087',
    'East Carolina':          '#4B1869',
    'Eastern Michigan':       '#006028',
    'Florida':                '#0021A5',
    'Florida Atlantic':       '#003366',
    'Florida International':  '#081E3F',
    'Florida State':          '#782F40',
    'Fresno State':           '#CC0000',
    'Georgia':                '#BA0C2F',
    'Georgia Southern':       '#011E41',
    'Georgia State':          '#0039A6',
    'Georgia Tech':           '#B3A369',
    'Hawai\'i':            '#024731',
    'Houston':                '#C8102E',
    'Idaho':                  '#B3A369',
    'Illinois':               '#E84A27',
    'Indiana':                '#990000',
    'Iowa':                   '#FFCD00',
    'Iowa State':             '#C8102E',
    'Jacksonville State':     '#CC0000',
    'James Madison':          '#450084',
    'Kansas':                 '#0051A5',
    'Kansas State':           '#512888',
    'Kennesaw State':         '#FCBA04',
    'Kent State':             '#002664',
    'Kentucky':               '#0033A0',
    'Liberty':                '#002868',
    'Louisiana':              '#CE181E',
    'Louisiana Tech':         '#002F8B',
    'UL Monroe':              '#800000',
    'Louisville':             '#AD0000',
    'LSU':                    '#461D7C',
    'Marshall':               '#009144',
    'Maryland':               '#E03A3E',
    'Massachusetts':       '#881C1C',
    'Memphis':                '#003087',
    'Miami':                  '#F47321',
    'Miami (OH)':             '#B61E2E',
    'Michigan':               '#00274C',
    'Michigan State':         '#18453B',
    'Middle Tennessee State':       '#0066CC',
    'Minnesota':              '#7A0019',
    'Mississippi State':      '#660000',
    'Missouri':               '#F1B82D',
    'Navy':                   '#00205B',
    'Nebraska':               '#E41C38',
    'Nevada':                 '#003366',
    'New Mexico':             '#C8102E',
    'New Mexico State':       '#861F41',
    'North Carolina':         '#4B9CD3',
    'NC State':   '#CC0000',
    'North Texas':            '#00853E',
    'Northern Illinois':      '#BA0C2F',
    'Northwestern':           '#4E2A84',
    'Notre Dame':             '#C99700',
    'Ohio':                   '#00694E',
    'Ohio State':             '#BB0000',
    'Oklahoma':               '#841617',
    'Oklahoma State':         '#FF6600',
    'Old Dominion':           '#003057',
    'Ole Miss':              '#CE1126',
    'Oregon':                 '#154733',
    'Oregon State':           '#DC4405',
    'Penn State':             '#041E42',
    'Pittsburgh':             '#003594',
    'Purdue':                 '#CEB888',
    'Rice':                   '#00205B',
    'Rutgers':                '#CC0033',
    'Sam Houston':         '#F77F00',
    'San Diego State':        '#A6192E',
    'San José State':        '#0055A2',
    'SMU':                    '#0033A0',
    'South Alabama':          '#00205B',
    'South Carolina':         '#73000A',
    'South Florida':          '#006747',
    'Southern Miss':   '#FFB300',
    'Stanford':               '#8C1515',
    'Syracuse':               '#F76900',
    'TCU':                    '#4D1979',
    'Temple':                 '#9D2235',
    'Tennessee':              '#FF8200',
    'Texas':                  '#BF5700',
    'Texas A&M':              '#500000',
    'Texas State':            '#461D7C',
    'Texas Tech':             '#CC0000',
    'Toledo':                 '#15397F',
    'Troy':                   '#8B0000',
    'Tulane':                 '#006747',
    'Tulsa':                  '#002D62',
    'UAB':                    '#1E6B52',
    'UCF':                    '#BA9B37',
    'UCLA':                   '#2D68C4',
    'UNLV':                   '#CF0A2C',
    'USC':                    '#990000',
    'Utah':                   '#CC0000',
    'Utah State':             '#0F1F52',
    'UTEP':                   '#FF8200',
    'UTSA':                   '#0C2340',
    'Vanderbilt':             '#866D4B',
    'Virginia':               '#232D4B',
    'Virginia Tech':          '#630031',
    'Wake Forest':            '#9E7E38',
    'Washington':             '#33006F',
    'Washington State':       '#981E32',
    'West Virginia':          '#002855',
    'Western Kentucky':       '#C8102E',
    'Western Michigan':       '#6C4023',
    'Wisconsin':              '#C5050C',
    'Wyoming':                '#FFC425',
}

# FBS_TEAMS is derived from TEAM_COLORS keys, sorted alphabetically for the sidebar dropdown.
# To add a new program, add an entry to TEAM_COLORS and it shows up here automatically.
# Team names must match CFBD's naming convention exactly. Spot-check new entries against
# the live /roster endpoint before adding, since CFBD's names don't always match common usage.
FBS_TEAMS = sorted(TEAM_COLORS.keys())

# ---------------------------------------------------------------------------
# CSS Theme
# ---------------------------------------------------------------------------
# Injected via st.markdown with unsafe_allow_html=True. Streamlit's built-in
# theming (config.toml) doesn't expose enough control for this design, so we
# use direct CSS injection instead.
#
# Font pair: Oswald (headings) + Inter (body/data)
#   - Oswald: used in college football broadcast graphics and Nike/Adidas
#     team branding. Reads as "football" without being gimmicky.
#   - Inter: highly legible at small sizes in tables and data displays.
#   Both loaded from Google Fonts via @import.
#
# Color system:
#   - Each team has its own primary color in TEAM_COLORS (used for bars,
#     highlights, and the choropleth map's darkest shade).
#   - Sidebar uses a neutral dark slate (#0f0f1a → #1a1a2e) so it works
#     for any team selection without clashing with team colors.
#   - Status badges use semantic colors: red (critical), amber (watch),
#     green (healthy), defined as .badge-red, .badge-yellow, .badge-green.
#
# Known CSS workaround:
#   - Streamlit's sidebar selectbox renders white text on white background
#     when the sidebar background is dark. Fixed by explicitly targeting
#     .stSelectbox > div > div with !important overrides.
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.main .block-container::before {
    content: ''; display: block; height: 4px;
    background: linear-gradient(90deg, #1a1a2e, #16213e, #1a1a2e);
    position: fixed; top: 0; left: 0; right: 0; z-index: 999;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f0f1a 0%, #1a1a2e 100%);
    border-right: 1px solid #2d2d4e;
}
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stCaption { color: #CBD5E1 !important; }
section[data-testid="stSidebar"] a { color: #94A3B8 !important; }

section[data-testid="stSidebar"] .stSelectbox > div > div {
    background-color: #2d2d4e !important;
    border: 1px solid #3d3d6e !important;
    border-radius: 6px !important;
    color: #FFFFFF !important;
}
section[data-testid="stSidebar"] .stSelectbox > div > div > div { color: #FFFFFF !important; }
section[data-testid="stSidebar"] .stSelectbox svg { fill: #94A3B8 !important; }
section[data-testid="stSidebar"] .stSelectbox label {
    color: #64748B !important; font-size: 11px !important;
    font-weight: 600 !important; text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}
section[data-testid="stSidebar"] .stMultiSelect > div > div {
    background-color: #2d2d4e !important;
    border: 1px solid #3d3d6e !important;
    border-radius: 6px !important;
}
section[data-testid="stSidebar"] .stMultiSelect label {
    color: #64748B !important; font-size: 11px !important;
    font-weight: 600 !important; text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}

h1 {
    font-family: 'Oswald', sans-serif !important; font-weight: 700 !important;
    font-size: 2rem !important; letter-spacing: 0.02em; text-transform: uppercase;
    border-bottom: 3px solid var(--team-color, #334155);
    padding-bottom: 8px; margin-bottom: 4px !important;
}
h2 { font-family: 'Oswald', sans-serif !important; font-weight: 600 !important;
     letter-spacing: 0.02em; text-transform: uppercase; font-size: 1.2rem !important; }
h3 { font-family: 'Oswald', sans-serif !important; font-weight: 500 !important; font-size: 1rem !important; }

div[data-testid="metric-container"] {
    background: linear-gradient(135deg, #F8FAFF 0%, #EEF2FA 100%);
    border: 1px solid #D1D9EE; border-top: 3px solid #334155;
    border-radius: 8px; padding: 14px 18px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}
div[data-testid="metric-container"] label {
    font-family: 'Inter', sans-serif !important; font-size: 11px !important;
    font-weight: 600 !important; text-transform: uppercase !important;
    letter-spacing: 0.08em !important; color: #64748B !important;
}
div[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-family: 'Oswald', sans-serif !important; font-size: 1.8rem !important;
    color: #1E293B !important; font-weight: 600 !important;
}

.stButton > button {
    background-color: #1E293B !important; color: #FFFFFF !important;
    border: none !important; border-radius: 4px !important;
    font-family: 'Inter', sans-serif !important; font-weight: 600 !important;
    font-size: 13px !important; padding: 6px 14px !important;
    transition: all 0.2s ease; letter-spacing: 0.02em;
}
.stButton > button:hover {
    opacity: 0.85 !important; transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(0,0,0,0.2) !important;
}

div[data-testid="stExpander"] {
    border: 1px solid #E2E8F0 !important; border-radius: 8px !important;
    margin-bottom: 8px !important; box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    overflow: hidden;
}
div[data-testid="stExpander"] summary {
    background: linear-gradient(90deg, #1E293B 0%, #334155 100%) !important;
    color: #FFFFFF !important; padding: 10px 16px !important;
    font-family: 'Oswald', sans-serif !important; font-size: 14px !important;
    font-weight: 600 !important; text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}
div[data-testid="stExpander"] summary svg { fill: #94A3B8 !important; }

div[data-testid="stTabs"] button {
    font-family: 'Oswald', sans-serif !important; font-weight: 500 !important;
    text-transform: uppercase !important; letter-spacing: 0.06em !important;
    font-size: 13px !important;
}

/* Sidebar radio nav: styled as a clean link list */

section[data-testid="stSidebar"] .stRadio label {
    color: #CBD5E1 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 7px 10px 7px 4px !important;
    border-radius: 5px !important;
    cursor: pointer !important;
    display: block !important;
    width: 100% !important;
    transition: background 0.15s;
}
section[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(255,255,255,0.07) !important;
    color: #FFFFFF !important;
}
section[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] > div:first-child {
    display: none !important;
}

div[data-testid="stAlert"] { border-radius: 6px; }
hr { border-color: #E2E8F0; margin: 12px 0; }
thead tr th {
    background-color: #1E293B !important; color: #FFFFFF !important;
    font-family: 'Inter', sans-serif !important; font-size: 12px !important;
    font-weight: 600 !important; text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}
.badge-red    { background:#FDECEA; color:#B71C1C; padding:4px 12px; border-radius:12px; font-size:12px; font-weight:700; font-family:'Inter',sans-serif; }
.badge-yellow { background:#FFF8E1; color:#7A5200; padding:4px 12px; border-radius:12px; font-size:12px; font-weight:700; font-family:'Inter',sans-serif; }
.badge-green  { background:#E8F5E9; color:#1B5E20; padding:4px 12px; border-radius:12px; font-size:12px; font-weight:700; font-family:'Inter',sans-serif; }
.main .block-container { padding-top: 24px !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# API key
# ---------------------------------------------------------------------------
if 'CFBD_API_KEY' in st.secrets:
    API_KEY = st.secrets['CFBD_API_KEY']
else:
    load_dotenv()
    API_KEY = os.getenv('CFBD_API_KEY')

if not API_KEY:
    st.error('⚠️ CFBD_API_KEY not found. Add it to Streamlit secrets or your .env file.')
    st.stop()

HEADERS = {'Authorization': f'Bearer {API_KEY}'}

# ---------------------------------------------------------------------------
# Sidebar: team selector + competitor selector + navigation
# ---------------------------------------------------------------------------
st.sidebar.markdown("""
<div style="text-align:center; padding: 16px 0 8px 0;">
    <div style="font-size:2rem; line-height:1;">🏈</div>
    <div style="font-family:'Oswald',sans-serif; font-size:1.1rem; font-weight:700;
                color:#FFFFFF; letter-spacing:0.08em; text-transform:uppercase;
                margin-top:6px; line-height:1.1;">CFB Roster Intelligence</div>
</div>
<div style="height:1px; background:linear-gradient(90deg,transparent,#475569,transparent); margin:10px 0;"></div>
""", unsafe_allow_html=True)

selected_team = st.sidebar.selectbox(
    'YOUR TEAM',
    FBS_TEAMS,
    index=FBS_TEAMS.index('Notre Dame')
)

st.sidebar.markdown("""
<div style="height:1px; background:linear-gradient(90deg,transparent,#475569,transparent); margin:10px 0;"></div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Page navigation
# ---------------------------------------------------------------------------
# st.radio respects index on every render unlike selectbox which caches its
# last user-selected value internally, making programmatic navigation impossible.
# ---------------------------------------------------------------------------
PAGES = ['Roster Depth Dashboard', 'Position Deep Dive', 'Recruit Discovery', 'Recruiting Positioning']

if 'current_page' not in st.session_state:
    st.session_state['current_page'] = PAGES[0]

if 'nav_to' in st.session_state:
    st.session_state['current_page'] = st.session_state.pop('nav_to')
    st.session_state['nav_counter'] = st.session_state.get('nav_counter', 0) + 1

_cur_idx = PAGES.index(st.session_state['current_page']) \
           if st.session_state['current_page'] in PAGES else 0

# Dynamic key forces selectbox to re-initialize when navigating programmatically.
# Each time nav_to fires, we increment a counter so Streamlit treats it as a
# brand new widget, so index gets respected on that render.
if 'nav_counter' not in st.session_state:
    st.session_state['nav_counter'] = 0

page = st.sidebar.selectbox(
    'NAVIGATE TO', PAGES,
    index=_cur_idx,
    key=f'nav_select_{st.session_state["nav_counter"]}',
)
st.session_state['current_page'] = page


st.sidebar.markdown("""
<div style="height:1px; background:linear-gradient(90deg,transparent,#475569,transparent); margin:10px 0;"></div>
""", unsafe_allow_html=True)

st.sidebar.caption(
    'Data: [CollegeFootballData.com](https://collegefootballdata.com)  \n'
    '~70% FBS roster coverage. Walk-ons and recent transfers may not appear.'
)

# ---------------------------------------------------------------------------
# Team color helpers: derived from selected_team each run
# ---------------------------------------------------------------------------
TEAM_COLOR = TEAM_COLORS.get(selected_team, '#334155')

# Build color map for charts: selected team gets its color, competitors get
# progressively lighter slate greys so they're clearly secondary
COMP_GREYS = ['#64748B', '#94A3B8', '#CBD5E1', '#E2E8F0']
def build_color_map(team: str, comps: list) -> dict:
    cmap = {team: TEAM_COLORS.get(team, '#334155')}
    for i, comp in enumerate(comps):
        cmap[comp] = TEAM_COLORS.get(comp, COMP_GREYS[min(i, len(COMP_GREYS)-1)])
    return cmap

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# POSITION_GROUPS drives the three expandable unit sections on Page 1.
# Order determines render order: Offense first, Defense second, Special Teams last.
POSITION_GROUPS = {
    'Offense':       ['QB', 'RB', 'WR', 'TE', 'OL'],
    'Defense':       ['DL', 'LB', 'CB', 'S'],
    'Special Teams': ['PK', 'P', 'LS'],
}

# POSITION_THRESHOLDS: (red_max, yellow_max) per position.
# count <= red_max    -> Critical  (immediate recruiting action needed)
# count <= yellow_max -> Watch     (monitor; may need recruiting attention)
# count > yellow_max  -> Healthy
# Benchmarks based on standard FBS roster construction logic:
#   QB: need 2+ to safely run practice; OL: need 6+ for 5 starters + 1 backup.
POSITION_THRESHOLDS = {
    'QB':  (1, 3), 'RB':  (2, 4), 'WR':  (4, 7),
    'TE':  (2, 4), 'OL':  (6, 9), 'DL':  (4, 7),
    'LB':  (3, 5), 'CB':  (3, 5), 'S':   (2, 4),
    'PK':  (1, 2), 'P':   (1, 2), 'LS':  (1, 2),
}

# RECRUIT_POSITION_MAP solves the most important data quality issue in the app:
# CFBD uses different position labels for recruiting vs. roster data.
#   Roster: 'OL'  |  Recruiting: 'OT', 'OG', 'IOL', 'C'
#   Roster: 'DL'  |  Recruiting: 'DT', 'DE', 'EDGE', 'WDE', 'SDE'
#   Roster: 'RB'  |  Recruiting: 'RB', 'APB', 'FB'
# Without this map, position filters on Recruit Discovery return zero results.
# Page 3 uses .isin(RECRUIT_POSITION_MAP[selected_position]) for filtering.
# Page 4 uses a reversed version of this map to group recruiting data by position.
RECRUIT_POSITION_MAP = {
    'QB':  ['QB'],
    'RB':  ['RB', 'APB', 'FB'],
    'WR':  ['WR', 'RECV', 'SB'],
    'TE':  ['TE'],
    'OL':  ['OT', 'OG', 'IOL', 'C', 'OL'],
    'DL':  ['DT', 'DE', 'EDGE', 'DL', 'WDE', 'SDE'],
    'LB':  ['LB', 'ILB', 'OLB', 'WLB', 'MLB'],
    'CB':  ['CB', 'DB'],
    'S':   ['S', 'SAF', 'SS', 'FS'],
    'PK':  ['PK', 'K'],
    'P':   ['P'],
    'LS':  ['LS', 'SNP'],
}

# PLOTLY_LAYOUT: shared base dict unpacked into every fig.update_layout() call.
# Intentionally excludes 'yaxis' and 'margin'. If those keys appear in both
# this dict AND an individual chart's update_layout() call, Python raises:
#   TypeError: multiple values for keyword argument 'yaxis'
# Each chart defines its own yaxis/margin to avoid this conflict.
PLOTLY_LAYOUT = dict(
    plot_bgcolor='white',
    paper_bgcolor='white',
    font=dict(family='Inter, sans-serif', size=13),
    title_font=dict(family='Oswald, sans-serif', color='#1E293B', size=17),
)

# ---------------------------------------------------------------------------
# API helpers
# All three functions use @st.cache_data(ttl=3600), a 1-hour in-memory cache.
# First load fetches from CFBD API (1-3 seconds per call).
# Subsequent interactions within the session use cached data (instant).
# Cache is per-session on Streamlit Cloud free tier.
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def get_roster(team: str, year: int = 2024) -> pd.DataFrame:
    """
    Fetch a team roster from CFBD /roster.
    team must match CFBD naming exactly (run test_teams.py to verify).
    Key columns: position, firstName, lastName, year, height, weight,
    homeCity, homeState, recruitIds (empty list = no recruiting profile).
    Returns empty DataFrame on error or no data.
    """
    try:
        r = requests.get(
            'https://api.collegefootballdata.com/roster',
            headers=HEADERS, params={'team': team, 'year': year}, timeout=10
        )
        r.raise_for_status()
        data = r.json()
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_recruits(year: int) -> pd.DataFrame:
    """
    Fetch ALL national recruits for a class year from CFBD /recruiting/players.
    Returns uncommitted and committed recruits; Page 3 filters downstream.
    Key columns: name, position (CFBD label), stars, rating (0.0-1.0 composite),
    school, city, stateProvince, committedTo (None if uncommitted).
    Note: 'position' uses CFBD recruiting labels, see RECRUIT_POSITION_MAP.
    """
    try:
        r = requests.get(
            'https://api.collegefootballdata.com/recruiting/players',
            headers=HEADERS, params={'year': year}, timeout=10
        )
        r.raise_for_status()
        return pd.DataFrame(r.json())
    except Exception as e:
        st.error(f'Failed to load recruiting data for {year}: {e}')
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_portal_entries(year: int) -> pd.DataFrame:
    """
    Fetch transfer portal entries for a year from CFBD /player/portal.
    Used on Page 2 to build the Portal History column in the player table.
    Key columns: firstName, lastName, origin, destination, transferDate.
    The matching code handles 'originSchool'/'destinationSchool' variants too.
    Coverage is most complete for 2022-2024; pre-2022 data is sparse.
    """
    try:
        r = requests.get(
            'https://api.collegefootballdata.com/player/portal',
            headers=HEADERS, params={'year': year}, timeout=10
        )
        r.raise_for_status()
        data = r.json()
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()

def get_status(position: str, count: int) -> tuple:
    """
    Return (status_label, badge_class) for a position given its player count.
    badge_class maps to CSS classes .badge-red / .badge-yellow / .badge-green
    defined in the theme block. Used on Page 1 and Page 2.
    """
    red_max, yellow_max = POSITION_THRESHOLDS.get(position, (2, 4))
    if count <= red_max:
        return '🔴 Critical', 'badge-red'
    elif count <= yellow_max:
        return '🟡 Watch', 'badge-yellow'
    else:
        return '🟢 Healthy', 'badge-green'

# ===========================================================================
# PAGE 1: ROSTER DEPTH DASHBOARD
# ===========================================================================
if page == 'Roster Depth Dashboard':

    title_col, year_col = st.columns([3, 1])
    with title_col:
        st.title(f'🏈 {selected_team} - Roster Depth Dashboard')
    with year_col:
        st.markdown('<div style="padding-top:12px;"></div>', unsafe_allow_html=True)
        selected_year = st.selectbox(
            'Season:',
            [2024, 2023, 2022, 2021],
            index=0,
            key='dashboard_year',
        )

    st.markdown(
        f'<p style="color:#64748B; font-size:14px; margin-top:-4px;">'
        f'{selected_year} scholarship roster depth by position group</p>',
        unsafe_allow_html=True
    )

    roster = get_roster(selected_team, year=selected_year)
    if roster.empty:
        st.warning(
            f'No roster data found for **{selected_team}** ({selected_year}). '
            f"This usually means the team name doesn't exactly match CFBD's database, "
            f"or CFBD doesn't have {selected_year} data for this program. "
            f'Try checking [collegefootballdata.com](https://collegefootballdata.com) '
            f'to confirm the exact team name.'
        )
        st.stop()

    all_positions_flat = [p for grp in POSITION_GROUPS.values() for p in grp]
    status_map = {p: get_status(p, len(roster[roster['position'] == p])) for p in all_positions_flat}
    flagged_positions = [p for p, (lbl, _) in status_map.items() if '🔴' in lbl]
    watch_positions   = [p for p, (lbl, _) in status_map.items() if '🟡' in lbl]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(f'Total Players (CFBD)', len(roster))
    m2.metric('Positions Tracked', len(POSITION_THRESHOLDS))
    m3.metric('🔴 Critical', len(flagged_positions))
    m4.metric('🟡 Watch', len(watch_positions))
    st.markdown('---')

    # Alert panel sits above the tables, not inline. Critical alerts show first
    # with a direct "Find Recruits" button on the same row; tables below stay
    # clean data with no action column.
    if flagged_positions:
        st.subheader('⚠️ Immediate Attention Required')
        for pos in flagged_positions:
            red_max, _ = POSITION_THRESHOLDS[pos]
            count = len(roster[roster['position'] == pos])
            col_msg, col_btn = st.columns([5, 1])
            col_msg.error(
                f'**{pos}**: {count} player(s) on roster '
                f'(minimum: >{red_max}). Immediate recruiting attention needed.'
            )
            if col_btn.button(f'Find {pos} →', key=f'alert_btn_{pos}', use_container_width=True):
                st.session_state['recruit_position'] = pos
                st.session_state['nav_to'] = 'Recruit Discovery'
                st.rerun()
        st.markdown('')

    if watch_positions:
        for pos in watch_positions:
            _, yellow_max = POSITION_THRESHOLDS[pos]
            count = len(roster[roster['position'] == pos])
            st.warning(f'**{pos}**: {count} player(s) on roster (healthy threshold: >{yellow_max}). Monitor this position.')
        st.markdown('')

    if not flagged_positions and not watch_positions:
        st.success('✅ No critical or watch-level position groups at this time.')
        st.markdown('')

    # Position depth tables: clean, no action column.
    for unit, positions in POSITION_GROUPS.items():
        with st.expander(unit, expanded=True):
            h1, h2, h3 = st.columns([2, 1, 2])
            h1.markdown('<span style="font-size:11px;font-weight:700;color:#94A3B8;text-transform:uppercase;letter-spacing:.08em">POSITION</span>', unsafe_allow_html=True)
            h2.markdown('<span style="font-size:11px;font-weight:700;color:#94A3B8;text-transform:uppercase;letter-spacing:.08em">COUNT</span>', unsafe_allow_html=True)
            h3.markdown('<span style="font-size:11px;font-weight:700;color:#94A3B8;text-transform:uppercase;letter-spacing:.08em">STATUS</span>', unsafe_allow_html=True)
            st.markdown('<hr style="margin:4px 0 6px 0; border-color:#E2E8F0;">', unsafe_allow_html=True)

            for position in positions:
                count = len(roster[roster['position'] == position])
                status_label, badge_class = status_map[position]
                c1, c2, c3 = st.columns([2, 1, 2])
                c1.markdown(f'<span style="font-family:Inter,sans-serif;font-weight:600;font-size:14px;">{position}</span>', unsafe_allow_html=True)
                c2.markdown(f'<span style="font-family:Oswald,sans-serif;font-size:16px;font-weight:600;color:#1E293B;">{count}</span>', unsafe_allow_html=True)
                c3.markdown(f'<span class="{badge_class}">{status_label}</span>', unsafe_allow_html=True)


# ===========================================================================
# PAGE 2: POSITION DEEP DIVE
# ===========================================================================
elif page == 'Position Deep Dive':

    st.title(f'🔍 Position Deep Dive - {selected_team}')
    st.markdown('<p style="color:#64748B; font-size:14px; margin-top:-4px;">Player details and competitor headcount for a selected position</p>', unsafe_allow_html=True)

    col_pos, col_comp = st.columns([1, 2])
    with col_pos:
        all_positions = [pos for grp in POSITION_GROUPS.values() for pos in grp]
        selected_position = st.selectbox('Select Position:', all_positions)
    with col_comp:
        default_comps_p2 = [t for t in ['Ohio State', 'Georgia', 'Alabama', 'Clemson'] if t != selected_team][:3]
        competitors_p2 = st.multiselect(
            'Compare Against (up to 4):',
            [t for t in FBS_TEAMS if t != selected_team],
            default=default_comps_p2,
            max_selections=4,
            key='competitors_p2',
        )

    roster = get_roster(selected_team)
    if roster.empty:
        st.warning(
            f"No roster data found for **{selected_team}** (2024). "
            "The team name may not match CFBD's database exactly. "
            "Try a variation such as 'NC State' instead of 'North Carolina State'."
        )
        st.stop()

    position_players = roster[roster['position'] == selected_position].copy()
    count = len(position_players)
    status_label, badge_class = get_status(selected_position, count)

    c1, c2, c3, _ = st.columns([1, 1, 1, 1])
    c1.metric(f'{selected_position} on Roster', count)
    red_max, yellow_max = POSITION_THRESHOLDS.get(selected_position, (2, 4))
    c2.metric('Critical Threshold', f'≤ {red_max}')
    c3.metric('Watch Threshold', f'≤ {yellow_max}')
    st.markdown(f'<div style="margin:8px 0 16px 0;"><span class="{badge_class}">{status_label}</span></div>', unsafe_allow_html=True)
    st.markdown('---')

    st.subheader(f'{selected_position} Roster - {selected_team} 2024')

    display_columns = ['firstName', 'lastName', 'year', 'height', 'weight', 'homeCity', 'homeState', 'recruitIds']
    available = [c for c in display_columns if c in position_players.columns]
    player_table = position_players[available].copy()

    rename_map = {
        'firstName': 'First', 'lastName': 'Last', 'year': 'Year',
        'height': 'Ht', 'weight': 'Wt',
        'homeCity': 'Hometown', 'homeState': 'State', 'recruitIds': 'Profile',
    }
    player_table.rename(columns={k: v for k, v in rename_map.items() if k in player_table.columns}, inplace=True)

    if 'Profile' in player_table.columns:
        player_table['Profile'] = player_table['Profile'].apply(
            lambda x: '⚠️ No Profile' if (isinstance(x, list) and len(x) == 0) or pd.isna(x) else '✅ Recruited'
        )

    # Portal history: queries CFBD portal data for 2021-2024, filters to entries
    # where origin or destination contains the selected team, and matches on
    # case-insensitive full name. Misses nicknames (e.g. 'CJ' vs 'Cornelius')
    # or spelling differences between CFBD and roster data.
    portal_lookup = {}
    for portal_year in [2021, 2022, 2023, 2024]:
        portal_df = get_portal_entries(portal_year)
        if portal_df.empty:
            continue
        cols = portal_df.columns.tolist()
        fname_col  = next((c for c in cols if c.lower() in ('firstname', 'first_name', 'first')), None)
        lname_col  = next((c for c in cols if c.lower() in ('lastname', 'last_name', 'last')), None)
        origin_col = next((c for c in cols if c.lower() in ('origin', 'originteam', 'originschool', 'origin_school')), None)
        dest_col   = next((c for c in cols if c.lower() in ('destination', 'destinationteam', 'destinationschool', 'destination_school')), None)
        if not fname_col or not lname_col:
            continue
        nd_mask = pd.Series([False] * len(portal_df), index=portal_df.index)
        if origin_col:
            nd_mask = nd_mask | portal_df[origin_col].fillna('').str.contains(selected_team, case=False, regex=False)
        if dest_col:
            nd_mask = nd_mask | portal_df[dest_col].fillna('').str.contains(selected_team, case=False, regex=False)
        nd_portal = portal_df[nd_mask].copy()
        for _, row in nd_portal.iterrows():
            full_name = (str(row.get(fname_col, '')).strip() + ' ' + str(row.get(lname_col, '')).strip()).lower().strip()
            origin = str(row.get(origin_col, '')).strip() if origin_col else ''
            dest   = str(row.get(dest_col, '')).strip() if dest_col else ''
            if dest and selected_team.lower() in dest.lower():
                portal_lookup[full_name] = f'🔄 Transfer In ({origin} → {selected_team}, {portal_year})'
            elif origin and selected_team.lower() in origin.lower():
                portal_lookup[full_name] = f'↗️ Transfer Out ({selected_team} → {dest}, {portal_year})'

    if 'First' in player_table.columns and 'Last' in player_table.columns:
        def get_portal_status(row):
            name = (str(row.get('First', '')).strip() + ' ' + str(row.get('Last', '')).strip()).lower().strip()
            return portal_lookup.get(name, '-')
        player_table['Portal History'] = player_table.apply(get_portal_status, axis=1)

    st.dataframe(
        player_table,
        use_container_width=True,
        hide_index=True,
        column_config={
            'Portal History': st.column_config.TextColumn('Portal History', width='large',
                help='Transfer portal activity involving this program (2021-2024)'),
            'Profile':  st.column_config.TextColumn('Profile',  width='medium'),
            'First':    st.column_config.TextColumn('First',    width='small'),
            'Last':     st.column_config.TextColumn('Last',     width='small'),
            'Year':     st.column_config.TextColumn('Year',     width='small'),
            'Ht':       st.column_config.TextColumn('Ht',       width='small'),
            'Wt':       st.column_config.TextColumn('Wt',       width='small'),
        }
    )
    st.markdown('---')

    if not competitors_p2:
        st.info('Select at least one comparison program above to see the headcount chart.')
    else:
        st.subheader(f'Headcount vs. Peer Programs - {selected_position}')
        st.caption(f'2024 scholarship rosters · {selected_team} highlighted in team color')

        programs, counts = [selected_team], [count]
        with st.spinner('Loading competitor rosters...'):
            for comp in competitors_p2:
                comp_roster = get_roster(comp)
                comp_count = len(comp_roster[comp_roster['position'] == selected_position]) if not comp_roster.empty else 0
                programs.append(comp)
                counts.append(comp_count)

        comparison_df = pd.DataFrame({'Program': programs, 'Players': counts})
        comparison_df = comparison_df.sort_values('Players', ascending=True)
        bar_colors = [TEAM_COLORS.get(p, '#64748B') for p in comparison_df['Program']]
        all_p2_programs = [selected_team] + list(competitors_p2)

        fig = go.Figure(go.Bar(
            x=comparison_df['Players'], y=comparison_df['Program'],
            orientation='h', marker_color=bar_colors,
            text=comparison_df['Players'], textposition='outside',
            textfont=dict(family='Oswald, sans-serif', size=15, color='#1E293B'),
        ))
        max_val = comparison_df['Players'].max()
        fig.update_layout(
            **PLOTLY_LAYOUT, title=' ',
            xaxis=dict(range=[0, max_val + max(2, int(max_val * 0.2))],
                       gridcolor='#E5E7EB', title='Players on Roster'),
            yaxis=dict(title='', gridcolor='white', showgrid=False),
            height=max(220, 80 + len(all_p2_programs) * 60),
            margin=dict(t=20, b=40, l=10, r=60),
            bargap=0.35,
        )
        st.plotly_chart(fig, use_container_width=True)


# ===========================================================================
# PAGE 3: RECRUIT DISCOVERY
# ===========================================================================
elif page == 'Recruit Discovery':

    st.title(f'🎯 Recruit Discovery')
    st.markdown('<p style="color:#64748B; font-size:14px; margin-top:-4px;">Filter the national recruit pool to address identified roster gaps</p>', unsafe_allow_html=True)

    all_positions = [pos for grp in POSITION_GROUPS.values() for pos in grp]
    default_position = st.session_state.get('recruit_position', all_positions[0])
    default_index = all_positions.index(default_position) if default_position in all_positions else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        selected_position = st.selectbox('Position:', all_positions, index=default_index)
        # If user manually changed position, update session state to match
        if selected_position != st.session_state.get('recruit_position'):
            st.session_state['recruit_position'] = selected_position
    with col2:
        selected_year = st.selectbox('Class Year:', [2025, 2026, 2027, 2028])
    with col3:
        min_stars = st.selectbox('Minimum Stars:', [5, 4, 3, 2], index=2)

    availability = st.radio('Availability:', ['All Recruits', 'Uncommitted Only', 'Committed Only'], horizontal=True)
    st.markdown('---')

    with st.spinner(f'Loading {selected_year} recruiting data...'):
        recruits = get_recruits(year=selected_year)

    if recruits.empty:
        st.warning('No recruiting data found. Try a different year or check your API key.')
        st.stop()

    valid_cfbd_positions = RECRUIT_POSITION_MAP.get(selected_position, [selected_position])
    filtered = recruits[
        (recruits['position'].isin(valid_cfbd_positions)) &
        (recruits['stars'] >= min_stars)
    ].copy()

    if availability == 'Uncommitted Only':
        filtered = filtered[filtered['committedTo'].isna()]
    elif availability == 'Committed Only':
        filtered = filtered[filtered['committedTo'].notna()]

    filtered = filtered.sort_values('rating', ascending=False)

    uncommitted_count = int(filtered['committedTo'].isna().sum())
    avg_rating = filtered['rating'].mean() if not filtered.empty else 0

    m1, m2, m3 = st.columns(3)
    m1.metric('Recruits Found', len(filtered))
    m2.metric('Uncommitted', uncommitted_count)
    m3.metric('Avg Composite Rating', f'{avg_rating:.4f}' if avg_rating else '-')
    st.markdown('---')

    if filtered.empty:
        st.info('No recruits match the selected filters. Try lowering the star minimum or changing the year.')
    else:
        display_cols = ['name', 'position', 'stars', 'rating', 'school', 'city', 'stateProvince', 'committedTo']
        available = [c for c in display_cols if c in filtered.columns]
        display_df = filtered[available].copy()
        display_df.rename(columns={
            'name': 'Name', 'position': 'Position', 'stars': 'Stars',
            'rating': 'Rating', 'school': 'High School', 'city': 'City',
            'stateProvince': 'State', 'committedTo': 'Committed To',
        }, inplace=True)
        if 'Committed To' in display_df.columns:
            display_df['Committed To'] = display_df['Committed To'].fillna('Uncommitted')
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Choropleth recruit density map: fills each US state by uncommitted
    # recruit count, easier to read than a dot map at a glance. Color scale
    # runs light blue (0 recruits) to team color (max recruits). Hover shows
    # the top 3 recruits per state by composite rating. Only uncommitted
    # recruits get plotted, so 'All Recruits' and 'Committed Only' show
    # fewer (or zero) dots.
    if not filtered.empty and 'stateProvince' in filtered.columns:
        st.markdown('---')
        st.subheader('📍 Uncommitted Recruit Density by State')
        st.caption('Uncommitted recruits matching current filters, hover a state for top recruits')

        map_df = filtered[filtered['committedTo'].isna()].copy()
        map_df = map_df[map_df['stateProvince'].notna()]
        map_df['state_upper'] = map_df['stateProvince'].str.upper().str.strip()
        map_df = map_df[map_df['state_upper'].str.len() == 2]

        if not map_df.empty:
            map_df_sorted = map_df.sort_values('rating', ascending=False)

            def build_hover(group):
                top3 = group.head(3)
                lines = []
                for _, r in top3.iterrows():
                    stars_str = '★' * int(r['stars']) if pd.notna(r['stars']) else ''
                    rating_str = f"{r['rating']:.4f}" if pd.notna(r.get('rating')) else ''
                    lines.append(f"{r['name']} {stars_str} ({rating_str})")
                return '<br>'.join(lines)

            state_counts = map_df_sorted.groupby('state_upper').agg(count=('name', 'count')).reset_index()
            state_counts.columns = ['state', 'count']
            top3_by_state = map_df_sorted.groupby('state_upper').apply(build_hover).reset_index()
            top3_by_state.columns = ['state', 'top3_text']
            state_counts = state_counts.merge(top3_by_state, on='state', how='left')
            state_counts['hover'] = (
                '<b>' + state_counts['state'] + '</b>: ' +
                state_counts['count'].astype(str) + ' uncommitted recruit(s)<br>' +
                '<i>Top recruits:</i><br>' + state_counts['top3_text']
            )

            fig_map = go.Figure(go.Choropleth(
                locations=state_counts['state'],
                z=state_counts['count'],
                locationmode='USA-states',
                colorscale=[[0, '#E8F0F8'], [0.4, '#4A7FB5'], [1, TEAM_COLOR]],
                showscale=True,
                colorbar=dict(
                    title=dict(text='Recruits', font=dict(family='Inter, sans-serif', size=12)),
                    thickness=14, len=0.6,
                    tickfont=dict(family='Inter, sans-serif', size=11),
                ),
                hovertext=state_counts['hover'],
                hoverinfo='text',
                marker_line_color='white',
                marker_line_width=1.5,
            ))

            fig_map.update_layout(
                title=' ',
                geo=dict(scope='usa', projection_type='albers usa',
                         showland=True, landcolor='#F8FAFC',
                         showlakes=True, lakecolor='#DBEAFE',
                         showframe=False, bgcolor='white'),
                paper_bgcolor='white',
                margin=dict(t=10, b=10, l=0, r=0),
                height=420,
            )
            st.plotly_chart(fig_map, use_container_width=True)

            col_left, col_right = st.columns(2)
            with col_left:
                top_states = state_counts.sort_values('count', ascending=False).head(8)[['state', 'count']].copy()
                top_states.columns = ['State', 'Uncommitted Recruits']
                st.caption('Top states by uncommitted recruit count:')
                st.dataframe(top_states, use_container_width=True, hide_index=True)
            with col_right:
                star_breakdown = map_df.groupby('stars').size().reset_index()
                star_breakdown.columns = ['Stars', 'Count']
                star_breakdown['Stars'] = star_breakdown['Stars'].apply(lambda s: '★' * int(s))
                star_breakdown = star_breakdown.sort_values('Count', ascending=False)
                st.caption('Star rating breakdown (uncommitted):')
                st.dataframe(star_breakdown, use_container_width=True, hide_index=True)
        else:
            st.info('No uncommitted recruits with US state data for the current filters.')

    # recruit_position stays in session state while on this page
    # so filter changes (availability, year, stars) don't reset the position.
    # It is cleared only when the user manually picks a different position above.


# ===========================================================================
# PAGE 4: RECRUITING POSITIONING
# ===========================================================================
elif page == 'Recruiting Positioning':

    st.title(f'📊 {selected_team} - Recruiting Positioning')

    default_comps_p4 = [t for t in ['Ohio State', 'Georgia', 'Alabama', 'Clemson'] if t != selected_team][:3]
    competitors_p4 = st.multiselect(
        'Compare Against (up to 4):',
        [t for t in FBS_TEAMS if t != selected_team],
        default=default_comps_p4,
        max_selections=4,
        key='competitors_p4',
    )

    if not competitors_p4:
        st.info('Select at least one comparison program above to use this page.')
        st.stop()

    all_programs = [selected_team] + list(competitors_p4)
    COLOR_MAP = build_color_map(selected_team, competitors_p4)

    comp_names = ', '.join(competitors_p4)
    st.markdown(
        f'<p style="color:#64748B; font-size:14px; margin-top:-4px;">'
        f'vs. {comp_names} - 2023-2025 combined classes</p>',
        unsafe_allow_html=True
    )

    with st.spinner('Loading recruiting data for all programs...'):
        recruiting_df = load_recruiting_data(teams=all_programs, years=[2023, 2024, 2025])

    if recruiting_df.empty:
        st.error('Recruiting data could not be loaded. Check your API key.')
        st.stop()

    main_positions = ['QB', 'RB', 'WR', 'TE', 'OL', 'DL', 'LB', 'CB', 'S']
    reverse_map = {}
    for group, cfbd_list in RECRUIT_POSITION_MAP.items():
        if group in main_positions:
            for cfbd_pos in cfbd_list:
                reverse_map[cfbd_pos] = group

    recruiting_df['position_group'] = recruiting_df['position'].map(reverse_map)
    recruiting_df = recruiting_df[recruiting_df['position_group'].notna()]

    pos_counts = (
        recruiting_df.groupby(['team', 'position_group'])
        .size().reset_index(name='count')
    )
    pos_counts['position_group'] = pd.Categorical(pos_counts['position_group'], categories=main_positions, ordered=True)
    pos_counts = pos_counts.sort_values('position_group')
    pos_counts['position_group'] = pos_counts['position_group'].astype(str)

    avg_stars = (
        recruiting_df.groupby(['team', 'position_group'])['stars']
        .mean().reset_index(name='avg_stars')
    )
    avg_stars['avg_stars'] = avg_stars['avg_stars'].round(0).astype(int)
    avg_stars['position_group'] = pd.Categorical(avg_stars['position_group'], categories=main_positions, ordered=True)
    avg_stars = avg_stars.sort_values('position_group')
    avg_stars['position_group'] = avg_stars['position_group'].astype(str)

    tab1, tab2, tab3 = st.tabs(['Headcount by Position', 'Avg Star Rating by Position', 'Gap vs. Field Average'])

    with tab1:
        st.subheader('Recruits Signed by Position (2023-2025)')
        fig1 = px.bar(
            pos_counts, x='position_group', y='count', color='team',
            barmode='group', color_discrete_map=COLOR_MAP,
            labels={'position_group': 'Position', 'count': 'Recruits Signed', 'team': 'Program'},
            height=440, title=' ',
        )
        fig1.update_layout(
            **PLOTLY_LAYOUT,
            yaxis=dict(gridcolor='#E5E7EB', title='Recruits Signed'),
            margin=dict(t=20, b=40, l=40, r=20),
            legend=dict(title_text=' ', orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        )
        st.plotly_chart(fig1, use_container_width=True)

    with tab2:
        st.subheader('Average Star Rating by Position (2023-2025)')
        fig2 = px.bar(
            avg_stars, x='position_group', y='avg_stars', color='team',
            barmode='group', color_discrete_map=COLOR_MAP,
            labels={'position_group': 'Position', 'avg_stars': 'Avg Stars', 'team': 'Program'},
            height=440, title=' ',
        )
        fig2.update_layout(
            **PLOTLY_LAYOUT,
            yaxis=dict(gridcolor='#E5E7EB', range=[0, 5], tickvals=[1,2,3,4,5], title='Avg Star Rating'),
            margin=dict(t=20, b=40, l=40, r=20),
            legend=dict(title_text=' ', orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        )
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.subheader(f'{selected_team} Recruiting Gap - vs. Competitor Average')
        st.caption(f'Positive = {selected_team} recruits more than competitor avg · Negative = less · Colored line = zero')

        field_avg = (
            pos_counts[pos_counts['team'] != selected_team]
            .groupby('position_group')['count']
            .mean().reset_index(name='field_avg')
        )
        nd_counts = pos_counts[pos_counts['team'] == selected_team][['position_group', 'count']].copy()
        gap_df = nd_counts.merge(field_avg, on='position_group', how='left')
        gap_df['delta'] = (gap_df['count'] - gap_df['field_avg']).round(1)
        gap_df['color'] = gap_df['delta'].apply(lambda d: TEAM_COLOR if d >= 0 else '#B91C1C')
        gap_df['label'] = gap_df['delta'].apply(lambda d: f'+{d}' if d >= 0 else str(d))
        gap_df['position_group'] = pd.Categorical(gap_df['position_group'], categories=main_positions, ordered=True)
        gap_df['position_group'] = gap_df['position_group'].astype(str)
        gap_df = gap_df.sort_values('position_group')

        fig3 = go.Figure(go.Bar(
            x=gap_df['position_group'].astype(str),
            y=gap_df['delta'],
            marker_color=gap_df['color'],
            text=gap_df['label'],
            textposition='outside',
            textfont=dict(family='Oswald, sans-serif', size=13),
        ))
        fig3.add_hline(y=0, line_width=2, line_color=TEAM_COLOR)
        fig3.update_layout(
            **PLOTLY_LAYOUT, title=' ',
            yaxis=dict(gridcolor='#E5E7EB', title='Recruits vs. Competitor Avg'),
            xaxis=dict(title='Position'),
            height=400,
            margin=dict(t=20, b=40, l=40, r=20),
        )
        st.plotly_chart(fig3, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f'**{selected_team} recruits more than competitors at:**')
            over = gap_df[gap_df['delta'] > 0].sort_values('delta', ascending=False)
            for _, row in over.iterrows():
                st.markdown(f'- **{row["position_group"]}** (+{row["delta"]:.1f} vs. avg)')
        with col2:
            st.markdown(f'**{selected_team} recruits less than competitors at:**')
            under = gap_df[gap_df['delta'] < 0].sort_values('delta')
            for _, row in under.iterrows():
                st.markdown(f'- **{row["position_group"]}** ({row["delta"]:.1f} vs. avg)')

    st.markdown('---')
    st.subheader('Raw Counts by Position')
    pivot = (
        pos_counts.pivot(index='position_group', columns='team', values='count')
        .fillna(0).astype(int)
    )
    pivot.index.name = 'Position'
    pivot.columns.name = None
    st.dataframe(pivot, use_container_width=True)

    st.markdown('---')
    st.info(
        f'**How to read this:** High headcount + low avg stars = volume recruiting. '
        f'Low headcount + high stars = targeted approach. '
        f'The gap chart shows where {selected_team} leans in vs. pulls back relative to chosen competitors.'
    )