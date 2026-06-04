# Import our custom functions
from recruiting_data import load_recruiting_data, analyze_recruiting_composition

# Import streamlit, the library that turns Python scripts into web applications
# This is the core library that builds every page, button, table, and chart in the tool
import streamlit as st

# Import pandas for data manipulation
# We'll use it to organize and filter the roster and recruiting data
import pandas as pd

# Import requests to make API calls to the CFBD API
# This is how we pull live roster and recruiting data
import requests

# Import os and load_dotenv to securely load our API key from the .env file
# Never hardcode the API key directly in this file
import os
from dotenv import load_dotenv

# Load the .env file so our API key is available as an environment variable
load_dotenv()

# Try Streamlit secrets (Cloud), fall back to .env (local)
if 'CFBD_API_KEY' in st.secrets:
    API_KEY = st.secrets['CFBD_API_KEY']
else:
    load_dotenv()
    API_KEY = os.getenv('CFBD_API_KEY')

# Error check
if not API_KEY:
    st.error('CFBD_API_KEY not found. Check secrets configuration.')
    st.stop()

HEADERS = {'Authorization': f'Bearer {API_KEY}'}

# Configure the Streamlit page settings
# This runs first before anything else renders in the browser
# layout='wide' gives us more horizontal space for tables and comparisons
st.set_page_config(
    page_title='Notre Dame Roster Intelligence',
    page_icon='☘️',
    layout='wide'
)

# Define the navigation sidebar
# This is how staff switches between the three pages of the tool
# st.sidebar puts the navigation menu on the left side of the screen
st.sidebar.title('Notre Dame Roster Intelligence')

# Data Quality Callout
st.info(
    "**Data Quality Note:** Roster counts reflect CFBD-linked profiles (~70% of actual roster coverage). "
    "Walk-ons, recent transfers, and non-linked players may not appear. "
    "Use position thresholds and flags as a starting point for roster evaluation, not the definitive source."
)

st.sidebar.markdown('---')

# Create the page selection dropdown in the sidebar
# The three options map directly to our three blueprint pages
page = st.sidebar.selectbox(
    'Navigate to:',
    ['Roster Depth Dashboard', 'Position Deep Dive', 'Recruit Discovery', 'Recruiting Positioning']
)

# Define a function to fetch Notre Dame's roster from the CFBD API
# Functions keep our code organized and reusable across pages
# @st.cache_data tells Streamlit to store the result so it doesn't
# re-fetch from the API every time the user clicks something
@st.cache_data
def get_roster(team='Notre Dame', year=2024):
    # Make the API call to the roster endpoint
    response = requests.get(
        'https://api.collegefootballdata.com/roster',
        headers=HEADERS,
        params={'team': team, 'year': year}
    )
    # Convert the response to a pandas DataFrame and return it
    return pd.DataFrame(response.json())

# Define a function to fetch recruiting data from the CFBD API
# We'll use this on the Recruit Discovery page to surface available recruits
@st.cache_data
def get_recruits(position=None, year=None):
    # Set up the base parameters for the API call
    params = {}
    if position:
        params['position'] = position
    if year:
        params['year'] = year
    # Make the API call to the recruiting endpoint
    response = requests.get(
        'https://api.collegefootballdata.com/recruiting/players',
        headers=HEADERS,
        params=params
    )
    return pd.DataFrame(response.json())

# Define the position groupings for the depth chart
# This maps each unit (Offense, Defense, Special Teams) to its positions
# This is the structure that drives the expandable sections on Page 1
POSITION_GROUPS = {
    'Offense': ['QB', 'RB', 'WR', 'TE', 'OL'],
    'Defense': ['DL', 'LB', 'CB', 'S'],
    'Special Teams': ['PK', 'P', 'LS']
}

# Define the color coding thresholds for each position
# These are the minimums we agreed on based on real roster construction
# Format: position -> (red_max, yellow_max)
# If count <= red_max: red, if count <= yellow_max: yellow, else green
POSITION_THRESHOLDS = {
    'QB':  (1, 3),
    'RB':  (2, 4),
    'WR':  (4, 7),
    'TE':  (2, 4),
    'OL':  (6, 9),
    'DL':  (4, 7),
    'LB':  (3, 5),
    'CB':  (3, 5),
    'S':   (2, 4),
    'PK':  (1, 2),
    'P':   (1, 2),
    'LS':  (1, 2)
}

# Define a function that returns a color label based on player count
# This drives the color coding on Page 1
def get_status(position, count):
    # Look up the thresholds for this position
    red_max, yellow_max = POSITION_THRESHOLDS.get(position, (2, 4))
    if count <= red_max:
        return '🔴 Critical'
    elif count <= yellow_max:
        return '🟡 Watch'
    else:
        return '🟢 Healthy'
    

# PAGE 1 — ROSTER DEPTH DASHBOARD
# This block only runs when the user selects 'Roster Depth Dashboard' from the sidebar
if page == 'Roster Depth Dashboard':

    # Display the page title and a brief description
    st.title('☘️ Notre Dame Roster Depth Dashboard')
    st.markdown('Current roster depth by position group. Color coding reflects recruiting urgency.')
    st.markdown('---')

    # Fetch the Notre Dame roster using our function defined above
    roster = get_roster()

    # Store any flagged positions so we can display alerts below the table
    flagged_positions = []

    # Loop through each unit (Offense, Defense, Special Teams)
    # st.expander creates the clickable expandable sections
    for unit, positions in POSITION_GROUPS.items():

        # Create an expandable section for each unit, open by default
        with st.expander(f'{unit}', expanded=True):

            # Create columns for the table header
            col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
            col1.markdown('**Position**')
            col2.markdown('**Players**')
            col3.markdown('**Status**')
            col4.markdown('**Action**')

            st.markdown('---')

            # Loop through each position in this unit
            for position in positions:

                # Filter the roster to only players at this position
                position_players = roster[roster['position'] == position]
                count = len(position_players)

                # Get the color coded status for this position
                status = get_status(position, count)

                # If this position is critical, add it to flagged list
                if '🔴' in status:
                    flagged_positions.append(position)

                # Display one row per position with four columns
                col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
                col1.write(position)
                col2.write(count)
                col3.write(status)

                # If critical, show a button to jump to Recruit Discovery
                # st.session_state stores the selected position so Page 3 can read it
                if '🔴' in status:
                    if col4.button(f'Find {position} Recruits →', key=f'btn_{position}'):
                        st.session_state['recruit_position'] = position
                        st.session_state['page'] = 'Recruit Discovery'
                        st.rerun()
                else:
                    col4.write('')

    # Display flagged alerts section below the table
    st.markdown('---')
    st.subheader('⚠️ Flagged Alerts')

    if flagged_positions:
        for pos in flagged_positions:
            st.error(f'🔴 {pos} is critically thin — immediate recruiting attention needed')
    else:
        st.success('No critical position groups at this time')

# PAGE 2 — POSITION DEEP DIVE
# This block only runs when the user selects 'Position Deep Dive' from the sidebar
if page == 'Position Deep Dive':

    st.title('🔍 Position Deep Dive')
    st.markdown('Select a position group to see player details and competitor comparison.')
    st.markdown('---')

    # Flatten all positions from POSITION_GROUPS into a single list for the dropdown
    all_positions = [pos for group in POSITION_GROUPS.values() for pos in group]

    # Dropdown to select a position
    selected_position = st.selectbox('Select Position:', all_positions)

    # Fetch Notre Dame roster and filter to selected position
    roster = get_roster()
    position_players = roster[roster['position'] == selected_position].copy()

    # Display player count and status for selected position
    count = len(position_players)
    status = get_status(selected_position, count)
    st.markdown(f'**Current count:** {count} players — {status}')
    st.markdown('---')

    # Build the player table with relevant columns
    # Only show columns that exist and are useful to recruiting staff
    display_columns = ['firstName', 'lastName', 'year', 'position', 'height', 'weight', 'homeCity', 'homeState', 'recruitIds']
    player_table = position_players[display_columns].copy()

    # Rename columns to be staff-friendly
    player_table.columns = ['First Name', 'Last Name', 'Year', 'Position', 'Height', 'Weight', 'Hometown', 'State', 'Recruit Profile']

    # Add walk-on indicator — players with empty recruitIds are likely walk-ons
    player_table['Walk-On?'] = player_table['Recruit Profile'].apply(
        lambda x: '⚠️ No Profile' if len(x) == 0 else '✅ Has Profile'
    )

    # Drop the raw recruitIds column now that we have the indicator
    player_table = player_table.drop(columns=['Recruit Profile'])

    # Display the player table
    st.subheader(f'{selected_position} Roster')
    st.dataframe(player_table, use_container_width=True)

    st.markdown('---')

    # COMPETITOR COMPARISON SECTION
    st.subheader('📊 Competitor Comparison')
    st.markdown('Headcount at this position across programs.')

    # Define the competitor programs to compare against
    competitors = ['Ohio State', 'Georgia', 'Alabama']

    # Build comparison data
    comparison_data = {'Program': ['Notre Dame'] + competitors, 'Player Count': [count]}

    # Fetch each competitor roster and count players at selected position
    for competitor in competitors:
        comp_roster = get_roster(team=competitor)
        comp_count = len(comp_roster[comp_roster['position'] == selected_position])
        comparison_data['Player Count'].append(comp_count)

    # Display comparison as a clean table
    comparison_df = pd.DataFrame(comparison_data)
    st.dataframe(comparison_df, use_container_width=True, hide_index=True)

# PAGE 3 — RECRUIT DISCOVERY
# This block only runs when the user selects 'Recruit Discovery' from the sidebar
if page == 'Recruit Discovery':

    st.title('🎯 Recruit Discovery')
    st.markdown('Find recruits by position to address roster gaps.')
    st.markdown('---')

    # Flatten all positions for the dropdown
    all_positions = [pos for group in POSITION_GROUPS.values() for pos in group]

    # Check if this page was triggered by a 'Find Recruits' button on Page 1
    # If so, pre-select that position automatically
    default_position = st.session_state.get('recruit_position', all_positions[0])
    default_index = all_positions.index(default_position) if default_position in all_positions else 0

    # Three filters side by side using columns
    col1, col2, col3 = st.columns(3)

    with col1:
        # Position filter — pre-populated if coming from Page 1
        selected_position = st.selectbox(
            'Position:',
            all_positions,
            index=default_index
        )

    with col2:
        # Graduation year filter — recruits sign 1-4 years out typically
        selected_year = st.selectbox(
            'Recruiting Class Year:',
            [2025, 2026, 2027, 2028]
        )

    with col3:
        # Star rating filter — Notre Dame realistically targets 3+ stars
        min_stars = st.selectbox(
            'Minimum Stars:',
            [5, 4, 3, 2],
            index=2  # Default to 3 stars
        )

    # Add a fourth filter for commitment status
    # This lets staff focus only on recruits who are still available
    col4, _ = st.columns([1, 2])
    with col4:
        availability = st.radio(
            'Availability:',
            ['All Recruits', 'Uncommitted Only', 'Committed Only'],
            horizontal=True
        )

    st.markdown('---')

    # Fetch recruiting data based on selected filters
    recruits = get_recruits(year=selected_year)

    # Filter by position and minimum star rating
    if not recruits.empty:
        filtered = recruits[
            (recruits['position'] == selected_position) &
            (recruits['stars'] >= min_stars)
        ].copy()

        # Apply availability filter based on committedTo column
        # Uncommitted players have None or empty committedTo values
        if availability == 'Uncommitted Only':
            filtered = filtered[filtered['committedTo'].isna()]
        elif availability == 'Committed Only':
            filtered = filtered[filtered['committedTo'].notna()]

        # Sort by rating descending so best prospects appear first
        filtered = filtered.sort_values('rating', ascending=False)

        # Select and rename columns for staff-friendly display
        display_cols = ['name', 'position', 'stars', 'rating', 'school', 'city', 'stateProvince', 'committedTo']
        filtered = filtered[display_cols].copy()
        filtered.columns = ['Name', 'Position', 'Stars', 'Rating', 'High School', 'City', 'State', 'Committed To']

        # Show result count
        st.markdown(f'**{len(filtered)} recruits found** for {selected_position}, {selected_year} class, {min_stars}+ stars')

        # Display the recruit table
        st.dataframe(filtered, use_container_width=True, hide_index=True)

        # Clear the session state position after use
        # This prevents the page from always defaulting to the last flagged position
        if 'recruit_position' in st.session_state:
            del st.session_state['recruit_position']

    else:
        st.warning('No recruiting data found for the selected filters. Try adjusting the year or star rating.')

# PAGE 4 — RECRUITING POSITIONING
if page == 'Recruiting Positioning':

    st.title('📊 Recruiting Class Composition')
    
    st.info(
        "Compare Notre Dame's recruiting by position against Georgia, Ohio State, and Alabama. "
        "Identify where ND is over-recruiting or under-recruiting relative to elite programs."
    )
    
    # Load data
    with st.spinner("Loading recruiting data..."):
        recruiting_df = load_recruiting_data()
    
    if not recruiting_df.empty:
        import plotly.express as px
        
        st.subheader("Recruiting by Position (2023-2025 Combined)")
        
        # Group by team and position, count recruits
        pos_counts = recruiting_df.groupby(['team', 'position']).size().reset_index(name='count')
        
        # Filter to main positions only (no extras)
        main_positions = ['QB', 'RB', 'WR', 'TE', 'OL', 'DL', 'LB', 'CB', 'S']
        pos_counts = pos_counts[pos_counts['position'].isin(main_positions)]
        
        # Sort positions in logical order
        pos_counts['position'] = pd.Categorical(pos_counts['position'], categories=main_positions, ordered=True)
        pos_counts = pos_counts.sort_values('position')
        
        # Create grouped bar chart
        fig = px.bar(
            pos_counts,
            x='position',
            y='count',
            color='team',
            barmode='group',
            title='Recruiting Comparison by Position',
            labels={'position': 'Position', 'count': 'Number of Recruits', 'team': 'Program'},
            height=500
        )
        
        fig.update_layout(
            xaxis_title='Position',
            yaxis_title='Number of Recruits',
            hovermode='x unified',
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Raw data table below for reference
        st.markdown('---')
        st.subheader('Position Breakdown (Raw Data)')
        
        pivot_table = pos_counts.pivot(index='position', columns='team', values='count').fillna(0).astype(int)
        st.dataframe(pivot_table, use_container_width=True)
        
    else:
        st.error("No recruiting data loaded.")