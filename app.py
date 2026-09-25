import streamlit as st
import json
import os
import subprocess
import urllib.parse
from datetime import datetime, timedelta
import requests
import base64

# --- STREAMLIT PAGE INITIALIZATION ---
st.set_page_config(
    page_title="F5-TTS Enterprise Premium Hub",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- DATABASE ENGINE & CONFIGURATION ---
REPO_OWNER = "mfazil78761-glitch"
REPO_NAME = "F5-TTS-AK"
DB_URL = f"https://githubusercontent.com{REPO_OWNER}/{REPO_NAME}/main/users_db.json"
GITHUB_PAT_TOKEN = str(st.secrets.get("GITHUB_PAT_TOKEN", "")).strip()

def fetch_live_database():
    try:
        res = requests.get(DB_URL, timeout=15)
        if res.status_code == 200:
            return res.json().get("users", {})
    except Exception:
        pass
    return {"AKKHAN": {"password": "AKKHAN90", "expiry_timestamp": "2030-12-31 23:59:59", "total_limit": 99999999, "remaining_chars": 99999999, "is_revoked": False, "is_admin": True}}

def push_database_updates_to_github(updated_db_dict):
    if not GITHUB_PAT_TOKEN:
        st.error("GitHub PAT missing in Streamlit Secrets.")
        return False
    api_url = f"https://github.com{REPO_OWNER}/{REPO_NAME}/contents/users_db.json"
    headers = {
        "Authorization": f"Bearer {GITHUB_PAT_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "F5-TTS-Cloud-App"
    }
    try:
        get_res = requests.get(api_url, headers=headers, timeout=15)
        if get_res.status_code != 200: return False
        sha = get_res.json().get("sha")
        encoded_content = base64.b64encode(json.dumps({"users": updated_db_dict}, indent=2).encode("utf-8")).decode("ascii")
        payload = {"message": "SaaS Admin Interface Auto Commit Update", "content": encoded_content, "sha": sha}
        put_res = requests.put(api_url, headers=headers, json=payload, timeout=15)
        return put_res.status_code in (200, 201)
    except:
        return False

# --- PERSISTENT REFRESH RECOVERY ENGINE (ANTI-LOGOUT) ---
user_db = fetch_live_database()

# Agar url parameters check active ho refresh state recovery ke liye
query_params = st.query_params
if "sess_user" in query_params and "sess_pass" in query_params:
    u_param = query_params["sess_user"]
    p_param = query_params["sess_pass"]
    if u_param in user_db and user_db[u_param]["password"] == p_param:
        st.session_state.auth_session = True
        st.session_state.current_user = u_param

if "auth_session" not in st.session_state:
    st.session_state.auth_session = False
if "current_user" not in st.session_state:
    st.session_state.current_user = ""

# --- LOGIN GATEWAY (SHOWN ONLY IF LOGGED OUT) ---
if not st.session_state.auth_session:
    st.title("🔐 Secure Cloud Infrastructure Portal Login")
    with st.form("secure_gateway"):
        username_input = st.text_input("Username").upper().strip()
        password_input = st.text_input("Password", type="password")
        login_triggered = st.form_submit_button("Authorize & Sign In")

        if login_triggered:
            if username_input in user_db:
                target_user = user_db[username_input]
                if target_user.get("is_revoked", False):
                    st.error("🚨 Ask admin for access. Your access is revoked!")
                elif target_user["password"] == password_input:
                    exp_time = datetime.strptime(target_user["expiry_timestamp"], "%Y-%m-%d %H:%M:%S")
                    if exp_time < datetime.now() and not target_user.get("is_admin", False):
                        st.error("🚨 Your plan validity package has expired!")
                    else:
                        st.session_state.auth_session = True
                        st.session_state.current_user = username_input
                        # URL state dynamic mapping trigger to survive page refresh drops
                        st.query_params["sess_user"] = username_input
                        st.query_params["sess_pass"] = password_input
                        st.success("Authorized! Fetching workspace modules...")
                        st.rerun()
                else:
                    st.error("Invalid password code parameters.")
            else:
                st.error("Unauthorized profile handles configuration missing.")
    st.stop()

# --- ACTIVE LOGGED IN INSTANCE ---
active_username = st.session_state.current_user
account_profile = user_db[active_username]

# SIDEBAR NAV (HAMBURGER SWITCH MANAGER SYSTEM)
with st.sidebar:
    st.markdown(f"### 🤗 Active: **{active_username.upper()}**")
    if account_profile.get("is_admin", False):
        st.info("⭐ Account Level: Admin")
        saas_mode = st.radio("🎛️ Navigation Panel Menu", ["🗃️ Manage SaaS Users", "➕ Register New Customer"])
    else:
        st.info("👤 Account Level: Client User")
        saas_mode = st.radio("🎛️ Navigation Panel Menu", ["🎤 Reference Voice Cloning", "🔊 Text To Speech Engine"])
    
    st.write("---")
    if st.button("🔒 Secure Terminate Session", use_container_width=True):
        st.session_state.auth_session = False
        st.session_state.current_user = ""
        st.query_params.clear() # Clear out parameters drops tracking
        st.rerun()

# --- MASTER ADMIN VIEWS INTERFACES ---
if account_profile.get("is_admin", False):
    if saas_mode == "🗃️ Manage SaaS Users":
        st.title("👑 Active Clients Base Controls Management Matrix")
        for u_name, u_info in list(user_db.items()):
            if u_info.get("is_admin", False): continue
            status_badge = "🟢 Active" if not u_info.get("is_revoked", False) else "🔴 Revoked"
            st.markdown(f"##### Client Account: `{u_name}` | Status: **{status_badge}**")
            col1, col2, col3 = st.columns(3)
            with col1: new_limit = st.number_input("Char balance:", value=int(u_info["remaining_chars"]), key=f"c_{u_name}")
            with col2: add_days = st.number_input("Extend Days:", min_value=0, value=0, key=f"d_{u_name}")
            with col3:
                st.write("<div style='margin-top:25px;'></div>", unsafe_allow_html=True)
                rev_toggle = u_info.get("is_revoked", False)
                if st.button("Grant Access" if rev_toggle else "Revoke Access", key=f"r_{u_name}"):
                    user_db[u_name]["is_revoked"] = not rev_toggle
                    if push_database_updates_to_github(user_db): st.rerun()
                if st.button("💾 Save", key=f"s_{u_name}"):
                    user_db[u_name]["remaining_chars"] = new_limit
                    if add_days > 0:
                        curr_exp = datetime.strptime(u_info["expiry_timestamp"], "%Y-%m-%d %H:%M:%S")
                        if curr_exp < datetime.now(): curr_exp = datetime.now()
                        user_db[u_name]["expiry_timestamp"] = (curr_exp + timedelta(days=int(add_days))).strftime("%Y-%m-%d %H:%M:%S")
                    if push_database_updates_to_github(user_db): st.rerun()
            st.write("---")

    elif saas_mode == "➕ Register New Customer":
        st.title("👑 Register New Client Profile Node Instance")
        with st.form("new_user_registration_form"):
            reg_user = st.text_input("New Account Handle").upper().strip()
            reg_pass = st.text_input("Set Secret Login Password")
            reg_days = st.number_input("Duration Package (Days)", min_value=1, value=30)
            reg_chars = st.number_input("Character Limit Allocation Wallet Size", min_value=1000, value=1000000)
            if st.form_submit_button("🚀 Provision Node & Auto Commit Changes"):
                if reg_user and reg_pass and reg_user not in user_db:
                    user_db[reg_user] = {"password": reg_pass, "expiry_timestamp": (datetime.now() + timedelta(days=int(reg_days))).strftime("%Y-%m-%d %H:%M:%S"), "total_limit": int(reg_chars), "remaining_chars": int(reg_chars), "is_revoked": False, "is_admin": False}
                    if push_database_updates_to_github(user_db):
                        st.success(f"User {reg_user} added successfully!")
                        st.rerun()
    st.stop()

# --- REGULAR CLIENT ENGINE VIEWS (LIVE COUNTDOWN TIMER CODES INCLUDED) ---
expiry_target_obj = datetime.strptime(account_profile["expiry_timestamp"], "%Y-%m-%d %H:%M:%S")
time_delta_now = expiry_target_obj - datetime.now()
if time_delta_now.total_seconds() > 0:
    days = time_delta_now.days
    hours, remainder = divmod(time_delta_now.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    countdown_clock_string = f"⏱️ Time Remaining: **{days} days {hours} hours {minutes} minutes {seconds} seconds**"
else:
    countdown_clock_string = "🚨 Package Plan Validity Status: **Expired!**"

st.markdown(f"""
<div style="background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%); padding: 22px; border-radius: 12px; color: white; margin-bottom: 25px; border-left: 6px solid #4facfe;">
    <h3 style='margin:0; color: white;'>✨ Active Dashboard Profile: {active_username.upper()} Console</h3>
    <p style='margin:8px 0; font-size:17px; color: #6dd5ed;'>{countdown_clock_string}</p>
    <p style='margin:0; font-size:14px; opacity:0.85;'>Character Available Wallet Limit Size: <b>{account_profile['remaining_chars']:,} / {account_profile['total_limit']:,} Chars</b></p>
</div>
""", unsafe_allow_html=True)

user_voice_dir = f"cloud_vault/{active_username}/voices"
os.makedirs(user_voice_dir, exist_ok=True)
existing_voices = [f for f in os.listdir(user_voice_dir) if f.endswith(".wav")]

# --- PAGE ROUTER: HAMBURGER SCREEN SEPARATION SPLIT ---
if saas_mode == "🎤 Reference Voice Cloning":
    st.subheader("🎤 Reference Speakers Database Bank (Max 5 Limit)")
    st.caption(f"Storage allocation metrics tracker: {len(existing_voices)} / 5 templates utilized.")
    
    if len(existing_voices) < 5:
