# Changelog
## CFB Roster Intelligence Tool

---

## V2.0 — Multi-Team Release
*Generalized the tool from Notre Dame-specific to all 134 FBS programs.*

**New features**
- Team selector in the sidebar. Any FBS program can now be selected as the primary team.
- TEAM_COLORS dictionary with primary brand hex colors for all 134 FBS programs. Each team's bars and highlights use their actual brand color in charts.
- Per-page competitor multiselect on Pages 2 and 4 rather than a shared sidebar selection. Pages 2 and 4 answer different analytical questions, so independent competitor sets made more sense.
- Year selector on Roster Depth Dashboard covering 2021-2024.
- Recruiting gap analysis tab on Page 4 showing selected team recruiting volume versus competitor average at each position.
- Choropleth recruit density map on Page 3 replacing the dot map. Hover text shows top three recruits per state by composite rating.
- Transfer portal history column on Page 2 using CFBD /player/portal endpoint.

**Bug fixes**
- Position filters on Recruit Discovery now return results. CFBD recruiting data uses different position labels than roster data (OT vs OL, EDGE vs DL). Added RECRUIT_POSITION_MAP to translate between the two.
- Competitor comparison chart changed from vertical to horizontal bars. Vertical bars with four or more programs produced bars too wide and overlapping labels.
- Fixed "undefined" legend label rendering in Streamlit's bundled Plotly.js. Setting legend title_text to a single space rather than empty string prevents the JavaScript undefined rendering path.
- Fixed pandas 3.x Arrow backend TypeError on map jitter calculation. Added .astype(float) before NumPy arithmetic on lat/lon columns.
- Fixed portal endpoint URL from /transferportal to /player/portal.
- Portal matching logic rewritten to filter entries by team involvement rather than checking all portal entries. Previous version produced false positives for name collisions.
- Alert panel moved above position tables. Previously the ACTION column inside tables was empty when no positions were critical. Now alerts and action buttons render separately above the clean data tables.

**Team name corrections validated against live CFBD API**
- Appalachian State -> App State
- North Carolina State -> NC State
- Hawaii -> Hawai'i
- Mississippi -> Ole Miss
- San Jose State -> San José State
- Louisiana-Monroe, UConn, UMass, Southern Miss, Sam Houston verified

**Navigation fix**
- Find Recruits buttons on Page 1 now correctly navigate to Recruit Discovery with the position pre-selected. Previous implementation could not programmatically control Streamlit's selectbox after first render. Fixed using a dynamic widget key that increments on programmatic navigation, forcing the selectbox to re-initialize and respect the target index.
- Changing filters on Recruit Discovery (availability, year, stars) no longer resets the position back to QB. Position selection now persists in session state for the lifetime of the page visit.

**Removed**
- Hardcoded Notre Dame references throughout app.py
- Dead get_fbs_teams() function that was never called
- Sidebar competitor multiselect moved to individual pages

---

## V1.0 — Initial Release
*Notre Dame-specific roster intelligence tool.*

**Features**
- Roster Depth Dashboard with color-coded position status and alert panel
- Position Deep Dive with player table and competitor headcount comparison
- Recruit Discovery with position, year, star rating, and availability filters
- Recruiting Class Composition with headcount and average star rating charts
- Notre Dame brand theme (Oswald + Inter fonts, navy and gold color system)
- CFBD API integration with one-hour caching via @st.cache_data
- Session state navigation from Page 1 critical alerts to Page 3 position filter
- Streamlit Cloud deployment with secrets-based API key management

---

Built by Marcos Cisneros