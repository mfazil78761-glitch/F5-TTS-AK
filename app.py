import streamlit as st
import json
import os
import subprocess
import urllib.parse
from datetime import datetime, timedelta
import requests

st.set_page_config(
    page_title="F5-TTS Cloud Multi-Tenant SaaS",
    page_icon="👑",
    layout="wide"
)

# --- CENTRAL GITHUB DATABASE CONFIG ---
REPO_OWNER = "mfazil78761-glitch"
REPO_NAME = "F5-TTS-AK"
DB_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/users_db.json"

# Store the GitHub PAT in Streamlit secrets instead of hard-coding it.
GITHUB_PAT_TOKEN = st.secrets.get("GITHUB_PAT_TOKEN", "")


def fetch_live_database():
    try:
        res = requests.get(DB_URL, timeout=15)
        if res.status_code == 200:
            return res.json().get("users", {})
    except Exception:
        pass

    # Fallback structure matching the expected JSON data mapping.
    return {
        "AKKHAN": {
            "password": "AKKHAN90",
            "expiry_timestamp": "2030-12-31 23:59:59",
            "total_limit": 99999999,
            "remaining_chars": 99999999,
            "is_revoked": False,
            "is_admin": True,
        }
    }


def push_database_updates_to_github(updated_db_dict):
    if not GITHUB_PAT_TOKEN:
        st.warning(
            "⚠️ Admin GitHub PAT Token missing. "
            "Web UI updates won't save automatically!"
        )
        return False

    api_url = (
        f"https://api.github.com/repos/{REPO_OWNER}/"
        f"{REPO_NAME}/contents/users_db.json"
    )

    headers = {
        "Authorization": f"token {GITHUB_PAT_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    try:
        get_res = requests.get(api_url, headers=headers, timeout=15)

        if get_res.status_code == 200:
            sha = get_res.json().get("sha")

            payload = {
                "message": "Automated update from Web UI Panel Admin Action",
                "content": requests.utils.base64.b64encode(
                    json.dumps(
                        {"users": updated_db_dict},
                        indent=2
                    ).encode()
                ).decode(),
                "sha": sha,
            }

            # Fixed indentation: this belongs inside the try block.
            put_res = requests.put(
                api_url,
                headers=headers,
                json=payload,
                timeout=15,
            )

            # GitHub Contents API normally returns 200 for update
            # and 201 for creation.
            if put_res.status_code in (200, 201):
                return True

            st.error(
                f"GitHub update failed: HTTP {put_res.status_code} "
                f"- {put_res.text}"
            )
        else:
            st.error(
                f"GitHub database read failed: HTTP {get_res.status_code}"
            )

    except Exception as e:
        st.error(f"GitHub Sync pipeline error logs: {str(e)}")

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
                    st.error(
                        "🚨 Ask admin for access. Your access is revoked!"
                    )

                elif target_user["password"] == password_input:
                    exp_time = datetime.strptime(
                        target_user["expiry_timestamp"],
                        "%Y-%m-%d %H:%M:%S"
                    )

                    if (
                        exp_time < datetime.now()
                        and not target_user.get("is_admin", False)
                    ):
                        st.error(
                            "🚨 Your plan validity package has expired! "
                            "Contact Admin M Yousaf."
                        )
                    else:
                        st.session_state.auth_session = True
                        st.session_state.current_user = username_input
                        st.success("Access Granted!")
                        st.rerun()

                else:
                    st.error("Invalid password key parameters.")
            else:
                st.error("Unauthorized profile handle record missing.")

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


# --- MASTER ADMIN INTERFACE CONSOLE VIEW ---
if account_profile.get("is_admin", False):
    st.title("👑 Master Administrator User Management Dashboard")

    tab_admin_list, tab_admin_add = st.tabs(
        ["🗃️ Active Users Registry", "➕ Deploy New SaaS Client"]
    )

    with tab_admin_list:
        st.subheader("Manage Global Users Parameters")
        active_users_exist = False

        for u_name, u_info in list(user_db.items()):
            if u_info.get("is_admin", False):
                continue

            active_users_exist = True

            status_badge = (
                "🟢 Active Status"
                if not u_info.get("is_revoked", False)
                else "🔴 Access Revoked"
            )

            st.markdown(
                f"#### Profile Handle: `{u_name}` | "
                f"Status: **{status_badge}**"
            )

            col_u1, col_u2, col_u3, col_u4 = st.columns(
                [1.5, 1.2, 1, 1]
            )

            with col_u1:
                new_limit_chars = st.number_input(
                    "Characters Balance Remaining:",
                    value=int(u_info["remaining_chars"]),
                    key=f"char_{u_name}",
                )

            with col_u2:
                extend_extra_days = st.number_input(
                    "Extend Plan Days (Add):",
                    min_value=0,
                    value=0,
                    key=f"days_{u_name}",
                )

            with col_u4:
                st.write(
                    "<div style='margin-top:25px;'></div>",
                    unsafe_allow_html=True,
                )

                revoked_state_toggle = u_info.get("is_revoked", False)
                btn_txt = (
                    "🟢 Grant Access"
                    if revoked_state_toggle
                    else "🔴 Revoke Access"
                )

                if st.button(
                    btn_txt,
                    key=f"rev_btn_{u_name}",
                    use_container_width=True,
                ):
                    user_db[u_name]["is_revoked"] = not revoked_state_toggle

                    if push_database_updates_to_github(user_db):
                        st.success("Status changed successfully!")
                        st.rerun()

            with col_u3:
                st.write(
                    "<div style='margin-top:25px;'></div>",
                    unsafe_allow_html=True,
                )

                if st.button(
                    "💾 Save Changes",
                    key=f"save_edit_{u_name}",
                    use_container_width=True,
                ):
                    user_db[u_name]["remaining_chars"] = new_limit_chars

                    if extend_extra_days > 0:
                        curr_exp = datetime.strptime(
                            u_info["expiry_timestamp"],
                            "%Y-%m-%d %H:%M:%S"
                        )

                        if curr_exp < datetime.now():
                            curr_exp = datetime.now()

                        user_db[u_name]["expiry_timestamp"] = (
                            curr_exp
                            + timedelta(days=int(extend_extra_days))
                        ).strftime("%Y-%m-%d %H:%M:%S")

                    if push_database_updates_to_github(user_db):
                        st.success(f"Saved changes for {u_name}!")
                        st.rerun()

            st.write("---")

        if not active_users_exist:
            st.info(
                "Filhal database registry mein koi regular user add nahi hai. "
                "Naya user add karne ke liye barabar waale tab par jayein."
            )

    with tab_admin_add:
        st.subheader("Register New Client Instance")

        with st.form("new_user_registration_form"):
            reg_user = st.text_input(
                "New Client Username"
            ).upper().strip()

            reg_pass = st.text_input(
                "Set Login Secret Password"
            )

            reg_days = st.number_input(
                "Assign Duration (In Days)",
                min_value=1,
                value=30,
            )

            reg_chars = st.number_input(
                "Assign Character Allocation",
                min_value=1000,
                value=1000000,
            )

            create_user_btn = st.form_submit_button(
                "🚀 Deploy User to GitHub DB"
            )

            if create_user_btn:
                if not reg_user or not reg_pass:
                    st.error("Fields cannot be blank parameters.")

                elif reg_user in user_db:
                    st.error("🚨 Username handle already exists!")

                else:
                    calculated_expiry_timestamp = (
                        datetime.now()
                        + timedelta(days=int(reg_days))
                    ).strftime("%Y-%m-%d %H:%M:%S")

                    user_db[reg_user] = {
                        "password": reg_pass,
                        "expiry_timestamp": calculated_expiry_timestamp,
                        "total_limit": int(reg_chars),
                        "remaining_chars": int(reg_chars),
                        "is_revoked": False,
                        "is_admin": False,
                    }

                    if push_database_updates_to_github(user_db):
                        st.success(
                            f"🎉 User '{reg_user}' successfully deployed "
                            "and auto-committed!"
                        )
                        st.rerun()

    st.stop()


# --- REGULAR CLIENT INTERFACE PANEL ---
st.title("🎛 Premium F5-TTS Interface Workflow Dashboard")

expiry_target_obj = datetime.strptime(
    account_profile["expiry_timestamp"],
    "%Y-%m-%d %H:%M:%S"
)

time_delta_now = expiry_target_obj - datetime.now()

if time_delta_now.total_seconds() > 0:
    days = time_delta_now.days
    hours, remainder = divmod(time_delta_now.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    st.info(
        f"⏳ Plan remaining: {days} days, "
        f"{hours} hours, {minutes} minutes, {seconds} seconds"
    )
else:
    st.error("🚨 Your plan has expired.")
