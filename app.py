import streamlit as st
import pandas as pd
import random
import time
from datetime import datetime

# ==============================
# CONFIG
# ==============================
st.set_page_config(page_title="NO GOAL 5 MIN SCANNER", layout="wide")

REFRESH_INTERVAL = 25  # seconds

# Telegram Config (optional)
TELEGRAM_ENABLED = False
TELEGRAM_TOKEN = "YOUR_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

# ==============================
# SESSION STATE
# ==============================
if "previous_data" not in st.session_state:
    st.session_state.previous_data = {}

if "alerted_matches" not in st.session_state:
    st.session_state.alerted_matches = set()

# ==============================
# MOCK DATA GENERATOR
# ==============================
def fetch_live_data():
    matches = []

    teams = [
        "Barcelona vs Sevilla",
        "Liverpool vs Chelsea",
        "Real Madrid vs Valencia",
        "Bayern vs Dortmund",
        "PSG vs Lyon",
    ]

    for i, match in enumerate(teams):
        minute = random.randint(10, 85)
        home_score = random.randint(0, 3)
        away_score = random.randint(0, 3)

        shots_on_target_5 = random.randint(0, 3)
        shots_on_target_10 = random.randint(0, 4)

        dangerous_attacks = random.randint(10, 80)
        prev_da = st.session_state.previous_data.get(i, {}).get("dangerous_attacks", dangerous_attacks)

        corners_5 = random.randint(0, 3)

        red_cards = random.choice([0, 0, 0, 1])  # rare

        recent_goal = random.choice([True, False, False])

        possession_home = random.randint(40, 60)

        matches.append({
            "id": i,
            "match": match,
            "minute": minute,
            "score": f"{home_score}-{away_score}",
            "shots_on_target_5": shots_on_target_5,
            "shots_on_target_10": shots_on_target_10,
            "dangerous_attacks": dangerous_attacks,
            "prev_da": prev_da,
            "corners_5": corners_5,
            "red_cards": red_cards,
            "recent_goal": recent_goal,
            "possession": possession_home
        })

    return matches


# ==============================
# TELEGRAM ALERT
# ==============================
def send_telegram_alert(message):
    if not TELEGRAM_ENABLED:
        return

    import requests
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}

    try:
        requests.post(url, data=payload)
    except:
        pass


# ==============================
# SIGNAL ENGINE
# ==============================
def calculate_signal(match):
    conditions = [
        match["shots_on_target_5"] == 0,
        (match["dangerous_attacks"] - match["prev_da"]) < 4,
        match["minute"] < 75,
        not match["recent_goal"],
        match["red_cards"] == 0,
    ]

    true_count = sum(conditions)

    if true_count == 5:
        return "STRONG"
    elif true_count >= 3:
        return "MEDIUM"
    else:
        return "RISKY"


def safe_zone(match):
    if (
        (15 <= match["minute"] <= 40 or 55 <= match["minute"] <= 75)
        and (match["dangerous_attacks"] / max(match["minute"], 1)) < 1.2
        and match["shots_on_target_10"] == 0
        and match["corners_5"] == 0
    ):
        return True
    return False


def confidence(match):
    if (
        match["shots_on_target_10"] == 0
        and 40 <= match["possession"] <= 60
    ):
        return "HIGH (80%)"
    elif match["shots_on_target_5"] <= 1:
        return "MEDIUM (60%)"
    else:
        return "LOW (40%)"


# ==============================
# UI HEADER
# ==============================
st.title("⚽ NO GOAL 5 MIN SCANNER")

col1, col2 = st.columns(2)

with col1:
    show_strong_only = st.checkbox("Show only STRONG signals")

with col2:
    show_safe_only = st.checkbox("Show SAFE ZONE only")

# ==============================
# MAIN LOOP
# ==============================
data = fetch_live_data()

rows = []

for match in data:
    da_delta = match["dangerous_attacks"] - match["prev_da"]
    match["da_delta"] = da_delta

    signal = calculate_signal(match)
    is_safe = safe_zone(match)
    conf = confidence(match)

    # Save state
    st.session_state.previous_data[match["id"]] = {
        "dangerous_attacks": match["dangerous_attacks"]
    }

    # Alerts
    if signal == "STRONG" and match["id"] not in st.session_state.alerted_matches:
        msg = f"🔥 STRONG NO GOAL\n{match['match']} {match['minute']}'\nScore: {match['score']}"
        send_telegram_alert(msg)
        st.session_state.alerted_matches.add(match["id"])

    # Filters
    if show_strong_only and signal != "STRONG":
        continue

    if show_safe_only and not is_safe:
        continue

    rows.append({
        "Match": match["match"],
        "Minute": match["minute"],
        "Score": match["score"],
        "Shots(5m)": match["shots_on_target_5"],
        "DA": match["dangerous_attacks"],
        "DA Δ": da_delta,
        "Corners(5m)": match["corners_5"],
        "Red": match["red_cards"],
        "Signal": signal,
        "Safe Zone": "YES" if is_safe else "NO",
        "Confidence": conf
    })

df = pd.DataFrame(rows)

# ==============================
# COLOR STYLING
# ==============================
def color_signal(val):
    if val == "STRONG":
        return "background-color: green; color: white"
    elif val == "MEDIUM":
        return "background-color: orange; color: black"
    else:
        return "background-color: red; color: white"

styled_df = df.style.applymap(color_signal, subset=["Signal"])

st.dataframe(styled_df, use_container_width=True)

# ==============================
# FOOTER
# ==============================
st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

# ==============================
# AUTO REFRESH
# ==============================
time.sleep(REFRESH_INTERVAL)
st.rerun()
