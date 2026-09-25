import streamlit as st
import json
import os
import base64
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import requests
import random

# ============================================================
# F5-TTS PREMIUM SAAS ENTERPRISE
# ============================================================

st.set_page_config(
    page_title="F5-TTS Premium SaaS Enterprise",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------- CONFIG --------------------

REPO_OWNER = "mfazil78761-glitch"
REPO_NAME = "F5-TTS-AK"
DB_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/users_db.json"

GITHUB_PAT_TOKEN = str(st.secrets.get("GITHUB_PAT_TOKEN", "")).strip()

BASE_VOICE_DIR = Path("cloud_vault")
BASE_VOICE_DIR.mkdir(parents=True, exist_ok=True)

# -------------------- UI STYLE --------------------

st.markdown(
    """
<style>
.main {
    background: #0b1220;
}
.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
}
.hero {
    padding: 34px;
    border-radius: 22px;
    background: linear-gradient(135deg, #111827, #1e3a5f, #0f766e);
    color: white;
    margin-bottom: 24px;
    box-shadow: 0 10px 35px rgba(0,0,0,.25);
}
.card {
    padding: 22px;
    border-radius: 18px;
    background: rgba(30,41,59,.72);
    border: 1px solid rgba(255,255,255,.08);
    margin-bottom: 18px;
}
.small-muted {
    opacity: .75;
}
</style>
""",
    unsafe_allow_html=True,
)

# -------------------- GITHUB DATABASE API --------------------

def fetch_live_database():
    if not GITHUB_PAT_TOKEN:
        return {"AKKHAN": {"password": "AKKHAN90", "expiry_timestamp": "2030-12-31 23:59:59", "total_limit": 99999999, "remaining_chars": 99999999, "is_revoked": False, "is_admin": True, "kaggle_username": "", "kaggle_token": "", "ngrok_auth": "", "ngrok_domain": ""}}
    
    api_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/users_db.json"
    headers = {
        "Authorization": f"Bearer {GITHUB_PAT_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "F5-TTS-Cloud-App",
    }
    try:
        # Cache protection dynamic layer mapping
        res = requests.get(f"{api_url}?v={int(datetime.now().timestamp())}&r={random.randint(100,999)}", headers=headers, timeout=15)
        if res.status_code == 200:
            content_b64 = res.json().get("content", "")
            raw_data = json.loads(base64.b64decode(content_b64).decode("utf-8"))
            raw_users = raw_data.get("users", {})
            
            normalized_db = {}
            for k, v in raw_users.items():
                normalized_db[str(k).upper().strip()] = v
            return normalized_db
    except Exception:
        pass

    return {"AKKHAN": {"password": "AKKHAN90", "expiry_timestamp": "2030-12-31 23:59:59", "total_limit": 99999999, "remaining_chars": 99999999, "is_revoked": False, "is_admin": True, "kaggle_username": "", "kaggle_token": "", "ngrok_auth": "", "ngrok_domain": ""}}


def push_database_updates_to_github(updated_db_dict):
    if not GITHUB_PAT_TOKEN:
        st.error("GitHub PAT missing. Add GITHUB_PAT_TOKEN to Streamlit Secrets.")
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

        final_payload_dict = {}
        for k, v in updated_db_dict.items():
            final_payload_dict[str(k).upper().strip()] = v

        content = json.dumps({"users": final_payload_dict}, indent=2, ensure_ascii=False).encode("utf-8")
        encoded_content = base64.b64encode(content).decode("ascii")

        payload = {
            "message": "Update users database from F5-TTS Web UI Action",
            "content": encoded_content,
            "sha": sha,
        }

        put_res = requests.put(api_url, headers=headers, json=payload, timeout=15)
        return put_res.status_code in (200, 201)
    except Exception:
        return False


# -------------------- PERSISTENT SESSION RECOVERY --------------------

user_db = fetch_live_database()

if "auth_session" not in st.session_state:
    st.session_state.auth_session = False
if "current_user" not in st.session_state:
    st.session_state.current_user = ""
if "current_password" not in st.session_state:
    st.session_state.current_password = ""
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

# Anti logout URL verification check on runtime refresh actions
query_params = st.query_params
if not st.session_state.auth_session and "user" in query_params and "auth" in query_params:
    u_state = str(query_params["user"]).upper().strip()
    p_state = query_params["auth"]

    if u_state in user_db and user_db[u_state].get("password") == p_state:
        st.session_state.auth_session = True
        st.session_state.current_user = u_state
        st.session_state.current_password = p_state


# -------------------- LOGIN GATEWAY --------------------

if not st.session_state.auth_session:
    st.markdown(
        """
        <div class="hero">
            <h1>👑 F5-TTS Premium SaaS</h1>
            <p>Secure cloud voice cloning and text-to-speech workspace.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("secure_gateway"):
        username_input = st.text_input("Username").upper().strip()
        password_input = st.text_input("Password", type="password")

        login_triggered = st.form_submit_button("🔐 Authorize Access", use_container_width=True)

        if login_triggered:
            if username_input not in user_db:
                st.error("Unauthorized profile.")
            else:
                target_user = user_db[username_input]

                if target_user.get("is_revoked", False):
                    st.error("🚨 Your access is revoked.")
                elif target_user.get("password") != password_input:
                    st.error("Invalid password.")
                else:
                    exp_time = datetime.strptime(target_user["expiry_timestamp"], "%Y-%m-%d %H:%M:%S")

                    if exp_time < datetime.now() and not target_user.get("is_admin", False):
                        st.error("🚨 Your plan has expired.")
                    else:
                        st.session_state.auth_session = True
                        st.session_state.current_user = username_input
                        st.session_state.current_password = password_input
                        st.session_state.page = "Dashboard"

                        st.query_params["user"] = username_input
                        st.query_params["auth"] = password_input
                        st.rerun()

    st.stop()


# -------------------- PROFILE HANDLING CONTROLS --------------------

active_username = st.session_state.current_user

if active_username not in user_db:
    st.session_state.auth_session = False
    st.query_params.clear()
    st.rerun()

account_profile = user_db[active_username]

if account_profile.get("is_revoked", False):
    st.session_state.auth_session = False
    st.query_params.clear()
    st.error("🚨 Access revoked by administrator.")
    st.stop()


# -------------------- SUBSCRIPTION CLOCK TIMER --------------------

expiry_target_obj = datetime.strptime(account_profile["expiry_timestamp"], "%Y-%m-%d %H:%M:%S")
time_delta_now = expiry_target_obj - datetime.now()

if time_delta_now.total_seconds() > 0:
    days = time_delta_now.days
    hours, remainder = divmod(time_delta_now.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    countdown_clock_string = f"⏱️ Time Remaining: **{days} days {hours} hours {minutes} minutes {seconds} seconds**"
else:
    countdown_clock_string = "🚨 Package Plan Validity Status: **Expired!**"


# -------------------- HELPERS --------------------

def get_voice_dir():
    path = BASE_VOICE_DIR / active_username / "voices"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_saved_voices():
    voice_dir = get_voice_dir()
    supported = {".wav", ".mp3", ".m4a", ".ogg", ".flac"}

    return sorted(
        [p for p in voice_dir.iterdir() if p.is_file() and p.suffix.lower() in supported],
        key=lambda p: p.name.lower(),
    )


def save_user_kaggle_settings(username, token, n_auth, n_domain):
    account_profile["kaggle_username"] = username.strip()
    account_profile["kaggle_token"] = token.strip()
    account_profile["ngrok_auth"] = n_auth.strip()
    account_profile["ngrok_domain"] = n_domain.strip()
    return push_database_updates_to_github(user_db)


# -------------------- SIDEBAR MENU NAVIGATION --------------------

with st.sidebar:
    st.markdown("## 👑 F5-TTS Hub")
    st.write(f"**Active User:** {active_username}")

    if account_profile.get("is_admin", False):
        st.info("Master Administrator")
        admin_page = st.radio("Navigation", ["Dashboard", "Active Users Registry", "Deploy New SaaS Client", "⚙️ Settings"])
        st.session_state.page = admin_page
    else:
        st.info("Authorized Client")
        client_page = st.radio("Navigation", ["Dashboard", "🎤 Voice Cloning", "🔊 Text To Speech", "⚙️ Settings"])
        st.session_state.page = client_page

    st.divider()

    if st.button("🔒 Terminate Secure Session", use_container_width=True):
        st.session_state.auth_session = False
        st.session_state.current_user = ""
        st.session_state.current_password = ""
        st.query_params.clear()
        st.rerun()


page = st.session_state.page


