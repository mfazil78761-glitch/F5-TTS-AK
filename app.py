import streamlit as st
import json
import os
import subprocess
import urllib.parse
from datetime import datetime, timedelta
import requests
import base64

st.set_page_config(
    page_title="F5-TTS Cloud Multi-Tenant SaaS",
    page_icon="👑",
    layout="wide"
)

# --- CENTRAL GITHUB DATABASE CONFIG ---
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
        auth_res = requests.get("https://api.github.com/user", headers=headers, timeout=15)
        if auth_res.status_code == 401:
            st.error("GitHub PAT authentication failed (HTTP 401).")
            return False

        get_res = requests.get(api_url, headers=headers, timeout=15)
        if get_res.status_code != 200:
            return False

        sha = get_res.json().get("sha")
        encoded_content = base64.b64encode(json.dumps({"users": updated_db_dict}, indent=2).encode("utf-8")).decode("ascii")

        payload = {
            "message": "Automated update from Web UI Panel Admin Action",
            "content": encoded_content,
            "sha": sha,
        }

        put_res = requests.put(api_url, headers=headers, json=payload, timeout=15)
        if put_res.status_code in (200, 201):
            return True
    except Exception:
        pass
    return False


user_db = fetch_live_database()

if "auth_session" not in st.session_state:
    st.session_state.auth_session = False
if "current_user" not in st.session_state:
    st.session_state.current_user = ""


# --- LOGIN GATEWAY ---
if not st.session_state.auth_session:
    st.title("🔐 Secure Cloud Infrastructure Portal Login")
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
                        st.rerun()
                else:
                    st.error("Invalid password.")
            else:
                st.error("Unauthorized profile.")
    st.stop()


active_username = st.session_state.current_user
account_profile = user_db[active_username]


with st.sidebar:
    st.write(f"### 🤗 Active User: **{active_username.upper()}**")
    if account_profile.get("is_admin", False):
        st.info("Role Tier: Master Administrator")
    else:
        st.info("Role Tier: Authorized Client User")
    st.write("---")
    if st.button("🔒 End Session", use_container_width=True):
        st.session_state.auth_session = False
        st.session_state.current_user = ""
        st.rerun()


# --- MASTER ADMIN INTERFACE ---
if account_profile.get("is_admin", False):
    st.title("👑 Master Administrator User Management Dashboard")
    tab_admin_list, tab_admin_add = st.tabs(["🗃️ Active Users Registry", "➕ Deploy New SaaS Client"])

    with tab_admin_list:
        st.subheader("Manage Global Users Parameters")
        active_users_exist = False
        for u_name, u_info in list(user_db.items()):
            if u_info.get("is_admin", False):
                continue
            active_users_exist = True
            status_badge = "🟢 Active Status" if not u_info.get("is_revoked", False) else "🔴 Access Revoked"
            st.markdown(f"#### Profile Handle: `{u_name}` | Status: **{status_badge}**")

            new_limit_chars = st.number_input("Characters Balance Remaining:", value=int(u_info["remaining_chars"]), key=f"char_{u_name}")
            extend_extra_days = st.number_input("Extend Plan Days (Add):", min_value=0, value=0, key=f"days_{u_name}")

            revoked_state_toggle = u_info.get("is_revoked", False)
            btn_txt = "🟢 Grant Access" if revoked_state_toggle else "🔴 Revoke Access"

            if st.button(btn_txt, key=f"rev_btn_{u_name}"):
                user_db[u_name]["is_revoked"] = not revoked_state_toggle
                if push_database_updates_to_github(user_db):
                    st.rerun()

            if st.button("💾 Save Changes", key=f"save_edit_{u_name}"):
                user_db[u_name]["remaining_chars"] = new_limit_chars
                if extend_extra_days > 0:
                    curr_exp = datetime.strptime(u_info["expiry_timestamp"], "%Y-%m-%d %H:%M:%S")
                    if curr_exp < datetime.now():
                        curr_exp = datetime.now()
                    user_db[u_name]["expiry_timestamp"] = (curr_exp + timedelta(days=int(extend_extra_days))).strftime("%Y-%m-%d %H:%M:%S")
                if push_database_updates_to_github(user_db):
                    st.rerun()
            st.write("---")

    with tab_admin_add:
        st.subheader("Register New Client Instance")
        with st.form("new_user_registration_form"):
            reg_user = st.text_input("New Client Username").upper().strip()
            reg_pass = st.text_input("Set Login Secret Password")
            reg_days = st.number_input("Assign Duration (In Days)", min_value=1, value=30)
            reg_chars = st.number_input("Assign Character Allocation", min_value=1000, value=1000000)
            create_user_btn = st.form_submit_button("🚀 Deploy User to GitHub DB")
            if create_user_btn:
                if reg_user and reg_pass and reg_user not in user_db:
                    calculated_expiry_timestamp = (datetime.now() + timedelta(days=int(reg_days))).strftime("%Y-%m-%d %H:%M:%S")
                    user_db[reg_user] = {"password": reg_pass, "expiry_timestamp": calculated_expiry_timestamp, "total_limit": int(reg_chars), "remaining_chars": int(reg_chars), "is_revoked": False, "is_admin": False}
                    if push_database_updates_to_github(user_db):
                        st.rerun()
    st.stop()


# --- REGULAR CLIENT INTERFACE PANEL (MOBILE FRIENDLY FIXED) ---
st.title("🎛️ Premium F5-TTS Interface Workflow Dashboard")

# Responsive layout trigger: Mobile ke liye columns ko full wide vertical render karna
st.markdown("""
<style>
@media (max-width: 640px) {
    div[data-testid="stHorizontalBlock"] {
        flex-direction: column !important;
    }
    div[data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
    }
}
</style>
""", unsafe_allow_html=True)

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
    <h3 style='margin:0; color: white;'>✨ Session Active: {active_username.capitalize()} Console</h3>
    <p style='margin:8px 0; font-size:17px; color: #6dd5ed;'>{countdown_clock_string}</p>
    <p style='margin:0; font-size:14px; opacity:0.85;'>Character Available Balance: <b>{account_profile['remaining_chars']:,} / {account_profile['total_limit']:,} Chars</b></p>
</div>
""", unsafe_allow_html=True)

# --- VERTICAL RESPONSIBLE LAYOUT FOR MOBILE ---
st.subheader("Reference Speakers Bank")
user_voice_dir = f"cloud_vault/{active_username}/voices"
os.makedirs(user_voice_dir, exist_ok=True)
existing_voices = [f for f in os.listdir(user_voice_dir) if f.endswith(".wav")]
st.caption(f"Storage allocation spaces: {len(existing_voices)} / 5 spots active.")

if len(existing_voices) < 5:
    with st.expander("➕ Register Naya Speaker Track Profile"):
        with st.form("voice_reg_form"):
            new_speaker_title = st.text_input("Speaker Designation Tag")
            uploaded_audio_blob = st.file_uploader("Select voice .wav sample tracking file", type=["wav"])
            save_voice_action = st.form_submit_button("💾 Save into Profile Database Bank")
            if save_voice_action and new_speaker_title and uploaded_audio_blob:
                clean_title = "".join([c for c in new_speaker_title if c.isalnum() or c in ['_', '-']]).strip()
                with open(os.path.join(user_voice_dir, f"{clean_title}.wav"), "wb") as f:
                    f.write(uploaded_audio_blob.getbuffer())
                st.success("Speaker saved successfully!")
                st.rerun()

selected_voice_path = None

if existing_voices:
    for voice_file in existing_voices:
        voice_row_left, voice_row_right = st.columns([4, 1], gap="small")
        with voice_row_left:
            st.audio(os.path.join(user_voice_dir, voice_file))
            st.caption(voice_file.replace(".wav", ""))
        with voice_row_right:
            if st.button("🗑️ Delete", key=f"del_{voice_file}", use_container_width=True):
                os.remove(os.path.join(user_voice_dir, voice_file))
                st.rerun()
    st.write("---")

    # --- TTS GENERATION PANEL ---
    st.subheader("🎙️ Generate Speech")
    voice_choices = [v.replace(".wav", "") for v in existing_voices]

    col_left, col_right = st.columns([1, 1.2], gap="large")

    with col_left:
        selected_voice_name = st.selectbox("Choose Reference Speaker", voice_choices)
        selected_voice_path = os.path.join(user_voice_dir, f"{selected_voice_name}.wav")
        speed_setting = st.slider("Speech Speed", min_value=0.5, max_value=2.0, value=1.0, step=0.1)
        generate_btn = st.button("🚀 Generate Audio", use_container_width=True, type="primary")

    with col_right:
        text_to_speak = st.text_area("Enter text to synthesize", height=220, placeholder="Type or paste your script here...")

    if generate_btn:
        if not text_to_speak.strip():
            st.warning("Pehle kuch text likhein generate karne ke liye.")
        elif len(text_to_speak) > account_profile["remaining_chars"]:
            st.error("🚨 Not enough character balance remaining for this text.")
        else:
            st.info("TTS generation pipeline yahan call hogi (F5-TTS engine integration).")
else:
    st.info("Speech generate karne se pehle upar se ek reference speaker add karein.")
