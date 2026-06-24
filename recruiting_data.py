"""
recruiting_data.py
==================
Handles all CFBD recruiting class API calls for the CFB Roster Intelligence Tool.

This module is intentionally separate from app.py so that:
  1. Recruiting data fetching can be tested independently without running Streamlit
  2. The caching decorator (@st.cache_data) is applied correctly in Streamlit context
     but gracefully degrades when the file is run as a standalone script
  3. app.py stays focused on UI logic; this file stays focused on data retrieval

Data source: College Football Data API (https://collegefootballdata.com)
Endpoint used: GET /recruiting/players
  - Required param: team (string) or year (int)
  - Returns: signed recruiting class members with name, position, stars, rating,
    hometown, state, committedTo
  - Coverage: ~70% of FBS programs; walk-ons and some transfers may not appear

API key resolution order:
  1. Streamlit Cloud secrets (st.secrets['CFBD_API_KEY'])
  2. Local .env file via python-dotenv
  3. Raises ValueError if neither is found
"""

import requests
import pandas as pd
import os
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# API key resolution
# Streamlit Cloud secrets take priority over .env for deployed environments.
# The try/except handles the case where this file is run outside Streamlit
# (e.g. directly via `python recruiting_data.py` for testing).
# ---------------------------------------------------------------------------
try:
    import streamlit as st
    if 'CFBD_API_KEY' in st.secrets:
        API_KEY = st.secrets['CFBD_API_KEY']
    else:
        load_dotenv()
        API_KEY = os.getenv('CFBD_API_KEY')
except Exception:
    # Not running in Streamlit context, fall back to .env
    load_dotenv()
    API_KEY = os.getenv('CFBD_API_KEY')

if not API_KEY:
    raise ValueError(
        "CFBD_API_KEY not found. "
        "Add it to your .env file (local) or Streamlit secrets (cloud)."
    )

HEADERS = {'Authorization': f'Bearer {API_KEY}'}


# ---------------------------------------------------------------------------
# fetch_recruiting_class
# ---------------------------------------------------------------------------
# Defined twice: once with @st.cache_data when running inside Streamlit,
# once without when running as a standalone script. The try/except on the
# import determines which version is active.
#
# Caching rationale: CFBD recruiting data updates at most once per day, so a
# 24-hour TTL with disk persistence (ttl=86400, persist="disk") is plenty
# fresh and survives the app sleeping/restarting on Streamlit Cloud. This
# matters because CFBD's free tier caps out at 1,000 calls/month; without
# caching, Page 4 alone makes up to 15 calls (5 teams x 3 years) on every
# interaction. The cache is shared across all users of the deployed app,
# not per-session, so it's the TTL and persistence doing the work here,
# not how many people happen to be visiting at once.
# ---------------------------------------------------------------------------
try:
    import streamlit as st

    @st.cache_data(ttl=86400, persist="disk")
    def fetch_recruiting_class(team: str, year: int) -> pd.DataFrame:
        """
        Fetch a single team's signed recruiting class for one year from CFBD.

        Args:
            team: Exact CFBD team name (e.g. 'Notre Dame', 'Ohio State').
                  Must match CFBD's naming convention, see TEAM_COLORS in app.py
                  for the verified list of correct names.
            year: Recruiting class year (e.g. 2024 = players who signed in
                  the 2023-24 cycle).

        Returns:
            DataFrame with columns: name, position, stars, rating, hometown,
            state, commitment_status, year, team.
            Returns empty DataFrame on API error or no data.

        Notes:
            - 'position' uses CFBD recruiting labels (OT, IOL, EDGE, APB, etc.)
              which differ from roster position labels (OL, DL, RB, etc.).
              The RECRUIT_POSITION_MAP in app.py handles this translation.
            - 'rating' is CFBD's composite rating on a 0.0-1.0 scale.
              It is NOT the same as star rating (1-5).
            - 2025 class data is incomplete until National Signing Day.
        """
        url = 'https://api.collegefootballdata.com/recruiting/players'
        params = {'team': team, 'year': year}

        try:
            response = requests.get(url, headers=HEADERS, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if not data:
                return pd.DataFrame()

            # Extract only the fields we use, keeps DataFrames lean
            records = []
            for recruit in data:
                records.append({
                    'name':              recruit.get('name', 'Unknown'),
                    'position':          recruit.get('position', 'Unknown'),
                    'stars':             recruit.get('stars', 0),
                    'rating':            recruit.get('rating', 0.0),
                    'hometown':          recruit.get('hometown', 'Unknown'),
                    'state':             recruit.get('stateProvince', 'Unknown'),
                    'commitment_status': recruit.get('committedTo', None),
                    'year':              year,
                    'team':              team,
                })

            return pd.DataFrame(records)

        except Exception as e:
            response = getattr(e, 'response', None)
            if response is not None and response.status_code == 429:
                st.error("CFBD's API rate limit has been hit for this billing period. Data will return once the limit resets.")
            else:
                print(f"Error fetching {team} {year}: {e}")
            return pd.DataFrame()

except ImportError:
    # Running outside Streamlit, same function without the cache decorator.
    # Used for standalone testing and data exploration in notebooks.
    def fetch_recruiting_class(team: str, year: int) -> pd.DataFrame:
        """
        Fetch a single team's signed recruiting class for one year from CFBD.
        (Uncached version, used when running outside Streamlit context.)
        """
        url = 'https://api.collegefootballdata.com/recruiting/players'
        params = {'team': team, 'year': year}
        try:
            response = requests.get(url, headers=HEADERS, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if not data:
                return pd.DataFrame()
            records = []
            for recruit in data:
                records.append({
                    'name':              recruit.get('name', 'Unknown'),
                    'position':          recruit.get('position', 'Unknown'),
                    'stars':             recruit.get('stars', 0),
                    'rating':            recruit.get('rating', 0.0),
                    'hometown':          recruit.get('hometown', 'Unknown'),
                    'state':             recruit.get('stateProvince', 'Unknown'),
                    'commitment_status': recruit.get('committedTo', None),
                    'year':              year,
                    'team':              team,
                })
            return pd.DataFrame(records)
        except Exception as e:
            print(f"Error fetching {team} {year}: {e}")
            return pd.DataFrame()


def load_recruiting_data(
    teams: list = ['Notre Dame', 'Georgia', 'Ohio State', 'Alabama'],
    years: list = [2023, 2024, 2025]
) -> pd.DataFrame:
    """
    Load recruiting data for multiple teams and years by calling
    fetch_recruiting_class for every team/year combination.

    Args:
        teams: List of CFBD team names. Defaults to the four programs used
               on Page 4, but Page 4 passes the user-selected team and
               competitors dynamically.
        years: List of recruiting class years to include. 2023-2025 gives
               three cycles of data for trend analysis.

    Returns:
        Single concatenated DataFrame of all recruiting records.
        Returns empty DataFrame if all API calls fail.

    Usage on Page 4:
        Called with the user-selected team and competitors. fetch_recruiting_class
        is cached app-wide (shared across all users, not just one session), so
        switching pages, or another visitor loading the same team/year, doesn't
        trigger a re-fetch within the cache's TTL.
    """
    all_data = []
    for team in teams:
        for year in years:
            df = fetch_recruiting_class(team, year)
            if not df.empty:
                all_data.append(df)

    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()


# ---------------------------------------------------------------------------
# analyze_recruiting_composition
# ---------------------------------------------------------------------------
# Utility function for notebook-based analysis. Not called by app.py directly
# (Page 4 does its own groupby logic inline for UI flexibility), but kept here
# for use in data_exploration.ipynb or future analysis work.
# ---------------------------------------------------------------------------
def analyze_recruiting_composition(df: pd.DataFrame) -> dict:
    """
    Summarize a recruiting DataFrame by position, stars, and team/year.

    Args:
        df: DataFrame returned by load_recruiting_data().

    Returns:
        Dict with three keys:
          'composition'      : recruit count by team, year, position
          'star_distribution': recruit count by team, year, star rating
          'avg_stars'        : mean star rating by team and year
        Returns empty dict if df is empty.
    """
    if df.empty:
        return {}

    composition = df.groupby(['team', 'year', 'position']).size().reset_index(name='count')
    star_dist   = df.groupby(['team', 'year', 'stars']).size().reset_index(name='count')
    avg_stars   = df.groupby(['team', 'year'])['stars'].mean().reset_index(name='avg_stars')

    return {
        'composition':        composition,
        'star_distribution':  star_dist,
        'avg_stars':          avg_stars,
    }


# ---------------------------------------------------------------------------
# Standalone test
# Run `python recruiting_data.py` from the project root to verify:
#   1. API key is loaded correctly
#   2. CFBD returns data for a known team
#   3. Field names and data types look correct
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    print('Testing recruiting_data.py standalone...')
    df = load_recruiting_data(teams=['Notre Dame'], years=[2024])
    if df.empty:
        print('ERROR: No data returned. Check your API key and team name.')
    else:
        print(df.head(10).to_string())
        print(f'\nTotal recruits loaded : {len(df)}')
        print(f'Columns               : {list(df.columns)}')
        print(f'Positions found       : {sorted(df["position"].unique())}')
        print(f'Star range            : {df["stars"].min()}-{df["stars"].max()}')
        print(f'Rating range          : {df["rating"].min():.4f}-{df["rating"].max():.4f}')