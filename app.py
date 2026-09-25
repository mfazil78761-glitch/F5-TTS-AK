import streamlit as st
import json
import os
import subprocess
import urllib.parse
from datetime import datetime, timedelta
import requests
import base64

# --- STREAMLIT PAGE LAYOUT INITIALIZATION ---
st.set_page_config(
    page_title="F5-TTS Premium SaaS Enterprise",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- REPOSITORY DATABASE CORE STRATEGIES ---
REPO_OWNER = "mfazil78761-glitch"
REPO_NAME = "F5-TTS-AK"
DB_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/users_db.json"
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
        st.error("GitHub PAT missing. Add a valid GITHUB_PAT_TOKEN to Streamlit Secrets.")
        return False
    api_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/users_db.json"
    headers = {
        "Authorization": f"Bearer {GITHUB_PAT_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "F5-TTS-Cloud-App",
    }
    try:
        get_res = requests.get(api_url, headers=headers, timeout=15)
        if get_res.status_code != 200: return False
        sha = get_res.json().get("sha")
        encoded_content = base64.b64encode(json.dumps({"users": updated_db_dict}, indent=2).encode("utf-8")).decode("ascii")
        payload = {"message": "Automated update from Web UI Panel Admin Action", "content": encoded_content, "sha": sha}
        put_res = requests.put(api_url, headers=headers, json=payload, timeout=15)
        return put_res.status_code in (200, 201)
    except Exception:
        return False

# --- PERSISTENT STATE RECOVERY MANAGER (ANTI REFRESH LOGOUT) ---
user_db = fetch_live_database()

# Session load storage validation checks
if "auth_session" not in st.session_state:
    st.session_state.auth_session = False
if "current_user" not in st.session_state:
    st.session_state.current_user = ""
if "current_password" not in st.session_state:
    st.session_state.current_password = ""

# Recovery block logs detection
query_params = st.query_params
if not st.session_state.auth_session and "user" in query_params and "auth" in query_params:
    u_state = query_params["user"]
    p_state = query_params["auth"]
    if u_state in user_db and user_db[u_state]["password"] == p_state:
        st.session_state.auth_session = True
        st.session_state.current_user = u_state
        st.session_state.current_password = p_state

# --- LOGIN GATEWAY ---
if not st.session_state.auth_session:
    st.title(" Arden 🔐 Secure Cloud Infrastructure Portal Login")
    with st.form("secure_gateway"):
        username_input = st.text_input("Username").upper().strip()
        password_input = st.text_input("Password", type="password")
        login_triggered = st.form_submit_button("Authorize Access")

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
                        st.session_state.current_password = password_input
                        st.query_params["user"] = username_input
                        st.query_params["auth"] = password_input
                        st.rerun()
                else:
                    st.error("Invalid password.")
            else:
                st.error("Unauthorized profile.")
    st.stop()

# --- RE-VALIDATING LIVE USER PROFILE VARIABLES IN MEMORY ---
active_username = st.session_state.current_user
account_profile = user_db[active_username]

# HARD ACCESS REFACTOR CHECKS ON LIVE REFRESH SESSIONS
if account_profile.get("is_revoked", False):
    st.session_state.auth_session = False
    st.query_params.clear()
    st.error("🚨 Access Revoked by Admin. Session Terminated!")
    st.stop()

# --- SIDEBAR INTERFACE (HAMBURGER ROUTER NAVIGATION CONTROLLER) ---
with st.sidebar:
    st.write(f"### 🤗 Active User: **{active_username.upper()}**")
    if account_profile.get("is_admin", False):
        st.info("Role Tier: Master Administrator")
        app_page_mode = st.radio("🛠️ Navigation Controller", ["🗃️ Active Users Registry", "➕ Deploy New SaaS Client"])
    else:
        st.info("Role Tier: Authorized Client User")
        app_page_mode = st.radio("🎛️ Navigation Controller", ["🎤 Reference Voice Cloning", "🔊 Text To Speech Engine"])
    
    st.write("---")
    if st.button("🔒 Terminate Secure Session", use_container_width=True):
        st.session_state.auth_session = False
        st.session_state.current_user = ""
        st.session_state.current_password = ""
        st.query_params.clear()
        st.rerun()

# --- ADMINISTRATIVE SYSTEM WORKFLOW VIEWS ---
if account_profile.get("is_admin", False):
    if app_page_mode == "🗃️ Active Users Registry":
        st.title("👑 Master Administrator User Management Dashboard")
        st.subheader("Manage Global Users Parameters")
        active_users_exist = False
        for u_name, u_info in list(user_db.items()):
            if u_info.get("is_admin", False): continue
            active_users_exist = True
            
            status_badge = "🟢 Active Status" if not u_info.get("is_revoked", False) else "🔴 Access Revoked"
            st.markdown(f"#### Profile Handle: `{u_name}` | Status: **{status_badge}**")

            new_limit_chars = st.number_input("Characters Balance Remaining:", value=int(u_info["remaining_chars"]), key=f"char_{u_name}")
            extend_extra_days = st.number_input("Extend Plan Days (Add):", min_value=0, value=0, key=f"days_{u_name}")

            revoked_state_toggle = u_info.get("is_revoked", False)
            btn_txt = "🟢 Grant Access" if revoked_state_toggle else "🔴 Revoke Access"

            if st.button(btn_txt, key=f"rev_btn_{u_name}"):
                user_db[u_name]["is_revoked"] = not revoked_state_toggle
                if push_database_updates_to_github(user_db): st.rerun()

            if st.button("💾 Save Changes", key=f"save_edit_{u_name}"):
                user_db[u_name]["remaining_chars"] = new_limit_chars
                if extend_extra_days > 0:
                    curr_exp = datetime.strptime(u_info["expiry_timestamp"], "%Y-%m-%d %H:%M:%S")
                    if curr_exp < datetime.now(): curr_exp = datetime.now()
                    user_db[u_name]["expiry_timestamp"] = (curr_exp + timedelta(days=int(extend_extra_days))).strftime("%Y-%m-%d %H:%M:%S")
                if push_database_updates_to_github(user_db): st.rerun()
            st.write("---")
            
        if not active_users_exist:
            st.info("Filhal database registry mein koi regular user add nahi hai.")

    elif app_page_mode == "➕ Deploy New SaaS Client":
        st.title("👑 Register New Client Instance")
        with st.form("new_user_registration_form"):
            reg_user = st.text_input("New Client Username").upper().strip()
            reg_pass = st.text_input("Set Login Secret Password")
            reg_days = st.number_input("Assign Duration (In Days)", min_value=1, value=30)
            reg_chars = st.number_input("Assign Character Allocation", min_value=1000, value=1000000)
            create_user_btn = st.form_submit_button("🚀 Deploy User to GitHub DB")
            if create_user_btn and reg_user and reg_pass and reg_user not in user_db:
                calculated_expiry_timestamp = (datetime.now() + timedelta(days=int(reg_days))).strftime("%Y-%m-%d %H:%M:%S")
                user_db[reg_user] = {"password": reg_pass, "expiry_timestamp": calculated_expiry_timestamp, "total_limit": int(reg_chars), "remaining_chars": int(reg_chars), "is_revoked": False, "is_admin": False}
                if push_database_updates_to_github(user_db): st.rerun()
    st.stop()

# --- CLIENT AREA DYNAMIC COUNTDOWN INTERFACE ---
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
<div style="background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%); padding: 25px; border-radius: 12px; color: white; margin-bottom: 25px; border-left: 6px solid #4facfe;">
    <h3 style='margin:0; color: white;'>✨ Session Active: {active_username.upper()} Console</h3>
    <p style='margin:8px 0; font-size:17px; color: #6dd5ed;'>{countdown_clock_string}</p>
    <p style='margin:0; font-size:14px; opacity:0.85;'>Character Available Balance: <b>{account_profile['remaining_chars']:,} / {account_profile['total_limit']:,} Chars</b></p>
</div>
