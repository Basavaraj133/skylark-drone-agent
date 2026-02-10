import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Skylark Drone Agent", layout="wide")
st.title("🚁 Skylark Drone Operations Coordinator")

# ---------------- STEP 5A: COMMAND BOX ----------------
st.markdown("### 🤖 Ask the Operations Agent")

user_command = st.text_input(
    "Type a command (e.g., 'show available pilots in Bangalore', 'Arjun on leave')"
)

check_conflicts = st.button("🚨 Check Assignment Conflicts")
urgent_reassign = st.button("🚑 Handle Urgent Reassignment")

# ---------------- GOOGLE SHEETS AUTH ----------------
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_file(
    "service_account.json",
    scopes=scope
)

client = gspread.authorize(creds)

# ---------------- OPEN SHEETS ----------------
pilot_sheet = client.open("pilot_roster").sheet1
drone_sheet = client.open("drone_fleet").sheet1
mission_sheet = client.open("missions").sheet1

# ---------------- LOAD DATA ----------------
pilots = pd.DataFrame(pilot_sheet.get_all_records())
drones = pd.DataFrame(drone_sheet.get_all_records())
missions = pd.DataFrame(mission_sheet.get_all_records())

# ---------------- DISPLAY DATA ----------------
st.subheader("👨‍✈️ Pilot Roster")
st.dataframe(pilots)

st.subheader("🚁 Drone Fleet")
st.dataframe(drones)

st.subheader("📍 Missions")
st.dataframe(missions)

# ---------------- STEP 5B: COMMAND LOGIC ----------------
if user_command:
    cmd = user_command.lower()

    # 1️⃣ Show available pilots by location
    if "available pilots" in cmd:
        try:
            location = cmd.split("in")[-1].strip().title()

            filtered = pilots[
                (pilots["status"] == "Available") &
                (pilots["location"] == location)
            ]

            if filtered.empty:
                st.warning(f"No available pilots found in {location}")
            else:
                st.subheader(f"✅ Available Pilots in {location}")
                st.dataframe(filtered)

        except:
            st.error("❌ Could not process location query")

    # 2️⃣ Update pilot status → ON LEAVE (SYNC BACK)
    elif "on leave" in cmd:
        try:
            name = user_command.split("on")[0].strip()

            cell = pilot_sheet.find(name)
            status_col = pilots.columns.get_loc("status") + 1

            pilot_sheet.update_cell(cell.row, status_col, "On Leave")

            st.success(
                f"✅ {name} marked as On Leave (updated in Google Sheets)"
            )

        except:
            st.error("❌ Pilot name not found. Check spelling.")

    else:
        st.info("🤖 Command not recognized. Try another instruction.")

# ---------------- STEP 6: CONFLICT DETECTION ----------------
if check_conflicts:
    st.subheader("🚨 Conflict Report")

    conflicts_found = False

    for _, mission in missions.iterrows():
        assigned_pilot = mission.get("assigned_pilot")

        if not assigned_pilot:
            continue

        pilot_row = pilots[pilots["name"] == assigned_pilot]

        if pilot_row.empty:
            st.error(
                f"❌ Pilot '{assigned_pilot}' not found for mission {mission['project_id']}"
            )
            conflicts_found = True
            continue

        pilot = pilot_row.iloc[0]

        # Location mismatch
        if pilot["location"] != mission["location"]:
            st.warning(
                f"📍 Location mismatch: Pilot {pilot['name']} is in {pilot['location']} "
                f"but mission {mission['project_id']} is in {mission['location']}"
            )
            conflicts_found = True

        # Skill mismatch
        if mission["required_skills"] not in pilot["skills"]:
            st.warning(
                f"🧠 Skill mismatch: Pilot {pilot['name']} lacks "
                f"'{mission['required_skills']}' for mission {mission['project_id']}"
            )
            conflicts_found = True

        # Certification mismatch
        if mission["required_certs"] not in pilot["certifications"]:
            st.warning(
                f"📄 Certification mismatch: Pilot {pilot['name']} lacks "
                f"'{mission['required_certs']}' for mission {mission['project_id']}"
            )
            conflicts_found = True

    if not conflicts_found:
        st.success("✅ No conflicts detected. All assignments look good.")

# ---------------- STEP 7: URGENT REASSIGNMENT ----------------
if urgent_reassign:
    st.subheader("🚑 Urgent Reassignment Suggestions")

    urgent_missions = missions[missions["priority"] == "Urgent"]

    if urgent_missions.empty:
        st.info("No urgent missions found.")
    else:
        for _, mission in urgent_missions.iterrows():
            st.markdown(f"### 🚨 Mission {mission['project_id']}")

            assigned_pilot = mission.get("assigned_pilot")

            if not assigned_pilot:
                st.warning("No pilot assigned yet.")
                continue

            pilot_row = pilots[pilots["name"] == assigned_pilot]

            if pilot_row.empty:
                st.error(f"Assigned pilot {assigned_pilot} not found.")
                continue

            pilot = pilot_row.iloc[0]
            issue_found = False

            if pilot["status"] != "Available":
                st.warning("Pilot not available")
                issue_found = True

            if pilot["location"] != mission["location"]:
                st.warning("Pilot location mismatch")
                issue_found = True

            if mission["required_skills"] not in pilot["skills"]:
                st.warning("Pilot lacks required skill")
                issue_found = True

            if mission["required_certs"] not in pilot["certifications"]:
                st.warning("Pilot lacks required certification")
                issue_found = True

            if not issue_found:
                st.success("Assigned pilot is suitable. No reassignment needed.")
                continue

            alternatives = pilots[
                (pilots["status"] == "Available") &
                (pilots["location"] == mission["location"]) &
                (pilots["skills"].str.contains(mission["required_skills"])) &
                (pilots["certifications"].str.contains(mission["required_certs"]))
            ]

            if alternatives.empty:
                st.error("❌ No suitable alternative pilot found.")
            else:
                st.success("✅ Suggested Alternative Pilot(s)")
                st.dataframe(
                    alternatives[["name", "skills", "certifications", "location"]]
                )
