import requests
import pandas as pd
import os
from dotenv import load_dotenv

try:
    import streamlit as st
    # We're in Streamlit context
    if 'CFBD_API_KEY' in st.secrets:
        API_KEY = st.secrets['CFBD_API_KEY']
    else:
        load_dotenv()
        API_KEY = os.getenv('CFBD_API_KEY')
except:
    # We're running the script directly (not in Streamlit)
    load_dotenv()
    API_KEY = os.getenv('CFBD_API_KEY')

if not API_KEY:
    raise ValueError("CFBD_API_KEY not found in environment variables or secrets")

HEADERS = {'Authorization': f'Bearer {API_KEY}'}

def fetch_recruiting_class(team, year):
    """
    Fetch recruiting class for a team in a given year.
    Returns DataFrame with: name, position, stars, hometown, commitment_status
    """
    url = f"https://api.collegefootballdata.com/recruiting/players"
    params = {
        'team': team,
        'year': year
    }
    
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            return pd.DataFrame()
        
        # Extract relevant fields
        records = []
        for recruit in data:
            records.append({
                'name': recruit.get('name', 'Unknown'),
                'position': recruit.get('position', 'Unknown'),
                'stars': recruit.get('stars', 0),
                'hometown': recruit.get('hometown', 'Unknown'),
                'state': recruit.get('state', 'Unknown'),
                'commitment_status': recruit.get('commitment', 'Unknown'),
                'year': year,
                'team': team
            })
        
        return pd.DataFrame(records)
    
    except Exception as e:
        print(f"Error fetching {team} {year}: {e}")
        return pd.DataFrame()


def load_recruiting_data(teams=['Notre Dame', 'Georgia', 'Ohio State', 'Alabama'], years=[2023, 2024, 2025]):
    """
    Load recruiting data for multiple teams and years.
    Returns combined DataFrame.
    """
    all_data = []
    
    for team in teams:
        for year in years:
            print(f"Fetching {team} {year}...")
            df = fetch_recruiting_class(team, year)
            all_data.append(df)
    
    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()


def analyze_recruiting_composition(df):
    """
    Analyze recruiting class composition by position and stars.
    Returns summary stats.
    """
    if df.empty:
        return {}
    
    composition = df.groupby(['team', 'year', 'position']).size().reset_index(name='count')
    star_dist = df.groupby(['team', 'year', 'stars']).size().reset_index(name='count')
    avg_stars = df.groupby(['team', 'year'])['stars'].mean().reset_index(name='avg_stars')
    
    return {
        'composition': composition,
        'star_distribution': star_dist,
        'avg_stars': avg_stars
    }


if __name__ == '__main__':
    # Test: Load data and print summary
    df = load_recruiting_data()
    print(df.head())
    print(f"\nTotal recruits: {len(df)}")
    print(f"Teams: {df['team'].unique()}")