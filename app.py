import streamlit as st
import json
import os
import base64
from datetime import datetime, timedelta
from pathlib import Path
import requests

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
GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/users_db.json"

GITHUB_PAT_TOKEN = str(st.secrets.get("GITHUB_PAT_TOKEN", "")).strip()

BASE_VOICE_DIR = Path("cloud_vault")
BASE_VOICE_DIR.mkdir(parents=True, exist_ok=True)

# Optional Kaggle notebook/API endpoint.
# Set this in Streamlit Secrets as KAGGLE_TTS_ENDPOINT when the Kaggle
# notebook exposes an authenticated generation endpoint.
KAGGLE_TTS_ENDPOINT = str(
    st.secrets.get("KAGGLE_TTS_ENDPOINT", "")
).strip()

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

# -------------------- GITHUB DATABASE --------------------

def fallback_database():
    return {
        "AKKHAN": {
            "password": "AKKHAN90",
            "expiry_timestamp": "2030-12-31 23:59:59",
            "total_limit": 99999999,
            "remaining_chars": 99999999,
            "is_revoked": False,
            "is_admin": True,
            "kaggle_username": "",
            "kaggle_token": "",
        }
    }


def fetch_live_database():
    try:
        res = requests.get(DB_URL, timeout=15)
        if res.status_code == 200:
            users = res.json().get("users", {})
            if users:
                return users
    except Exception:
        pass

    return fallback_database()


def push_database_updates_to_github(updated_db_dict):
    if not GITHUB_PAT_TOKEN:
        st.error(
            "GitHub PAT missing. Add GITHUB_PAT_TOKEN to Streamlit Secrets."
        )
        return False

    headers = {
        "Authorization": f"Bearer {GITHUB_PAT_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "F5-TTS-Cloud-App",
    }

    try:
        get_res = requests.get(
            GITHUB_API_URL,
            headers=headers,
            timeout=15,
        )

        if get_res.status_code != 200:
            st.error(
                f"GitHub database read failed: {get_res.status_code}"
            )
            return False

        sha = get_res.json().get("sha")

        content = json.dumps(
            {"users": updated_db_dict},
            indent=2,
            ensure_ascii=False,
        ).encode("utf-8")

        encoded_content = base64.b64encode(content).decode("ascii")

        payload = {
            "message": "Update users database from F5-TTS Web UI",
            "content": encoded_content,
            "sha": sha,
        }

        put_res = requests.put(
            GITHUB_API_URL,
            headers=headers,
            json=payload,
            timeout=15,
        )

        if put_res.status_code in (200, 201):
            return True

        st.error(
            f"GitHub database update failed: {put_res.status_code}"
        )
        return False

    except Exception as exc:
        st.error(f"GitHub update error: {exc}")
        return False


# -------------------- SESSION --------------------

user_db = fetch_live_database()

defaults = {
    "auth_session": False,
    "current_user": "",
    "current_password": "",
    "page": "Dashboard",
}

for key, default in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default


# -------------------- LOGIN --------------------

query_params = st.query_params

if (
    not st.session_state.auth_session
    and "user" in query_params
    and "auth" in query_params
):
    u_state = query_params["user"]
    p_state = query_params["auth"]

    if (
        u_state in user_db
        and user_db[u_state].get("password") == p_state
    ):
        st.session_state.auth_session = True
        st.session_state.current_user = u_state
        st.session_state.current_password = p_state


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

        login_triggered = st.form_submit_button(
            "🔐 Authorize Access",
            use_container_width=True,
        )

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
                    exp_time = datetime.strptime(
                        target_user["expiry_timestamp"],
                        "%Y-%m-%d %H:%M:%S",
                    )

                    if (
                        exp_time < datetime.now()
                        and not target_user.get("is_admin", False)
                    ):
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


# -------------------- ACTIVE PROFILE --------------------

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


# -------------------- HELPERS --------------------

def get_voice_dir():
    path = BASE_VOICE_DIR / active_username / "voices"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_saved_voices():
    voice_dir = get_voice_dir()
    supported = {".wav", ".mp3", ".m4a", ".ogg", ".flac"}

    return sorted(
        [
            p
            for p in voice_dir.iterdir()
            if p.is_file() and p.suffix.lower() in supported
        ],
        key=lambda p: p.name.lower(),
    )


def character_count(text):
    # Counts every Unicode character entered by the user,
    # including spaces and newline characters.
    return len(text)


def deduct_characters(amount):
    current = int(account_profile.get("remaining_chars", 0))

    if amount > current:
        return False

    account_profile["remaining_chars"] = current - amount
    return push_database_updates_to_github(user_db)


def save_kaggle_settings(username, token):
    account_profile["kaggle_username"] = username.strip()
    account_profile["kaggle_token"] = token.strip()
    return push_database_updates_to_github(user_db)


def generate_with_kaggle(text, voice_path):
    """
    Optional connector for a Kaggle notebook/API endpoint.

    The endpoint must accept JSON containing:
        username
        token
        text
        voice_name
        voice_path

    It may return JSON or an audio response.
    """
    if not KAGGLE_TTS_ENDPOINT:
        return None, (
            "Kaggle TTS endpoint is not configured yet. "
            "Set KAGGLE_TTS_ENDPOINT in Streamlit Secrets."
        )

    kaggle_username = str(
        account_profile.get("kaggle_username", "")
    ).strip()

    kaggle_token = str(
        account_profile.get("kaggle_token", "")
    ).strip()

    if not kaggle_username or not kaggle_token:
        return None, (
            "Add your Kaggle username and API token in Settings first."
        )

    payload = {
        "username": kaggle_username,
        "token": kaggle_token,
        "text": text,
        "voice_name": voice_path.stem,
        "voice_path": str(voice_path),
    }

    try:
        response = requests.post(
            KAGGLE_TTS_ENDPOINT,
            json=payload,
            timeout=300,
        )

        if response.status_code != 200:
            return None, (
                f"Kaggle generation failed: HTTP "
                f"{response.status_code}"
            )

        content_type = response.headers.get("content-type", "")

        if "audio" in content_type:
            return response.content, None

        try:
            data = response.json()
            return data, None
        except Exception:
            return response.content, None

    except Exception as exc:
        return None, f"Kaggle connection error: {exc}"


# -------------------- SIDEBAR --------------------

with st.sidebar:
    st.markdown("## 👑 F5-TTS")
    st.write(f"**User:** {active_username}")

    if account_profile.get("is_admin", False):
        st.info("Master Administrator")

        admin_page = st.radio(
            "Navigation",
            [
                "Dashboard",
                "Active Users Registry",
                "Deploy New SaaS Client",
                "Settings",
            ],
            key="admin_navigation",
        )

        st.session_state.page = admin_page

    else:
        st.info("Authorized Client")

        client_page = st.radio(
            "Navigation",
            [
                "Dashboard",
                "🎤 Voice Cloning",
                "🔊 Text To Speech",
                "⚙️ Settings",
            ],
            key="client_navigation",
        )

        st.session_state.page = client_page

    st.divider()

    if st.button(
        "🔒 Terminate Secure Session",
        use_container_width=True,
    ):
        st.session_state.auth_session = False
        st.session_state.current_user = ""
        st.session_state.current_password = ""
        st.query_params.clear()
        st.rerun()


page = st.session_state.page


# ============================================================
# DASHBOARD
# ============================================================

if page == "Dashboard":
    st.markdown(
        f"""
        <div class="hero">
            <h1>Welcome, {active_username.upper()} 👋</h1>
            <p>
                Your F5-TTS cloud workspace is ready.
                Manage voices, generate speech and configure your account
                from one place.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)

    remaining = int(account_profile.get("remaining_chars", 0))
    total = int(account_profile.get("total_limit", 0))

    with col1:
        st.metric("Characters Remaining", f"{remaining:,}")

    with col2:
        st.metric("Total Allocation", f"{total:,}")

    with col3:
        st.metric(
            "Saved Voices",
            len(get_saved_voices()),
        )

    st.markdown(
        """
        <div class="card">
            <h2>🚀 Get Started</h2>
            <p class="small-muted">
                Upload a reference voice first, give it a name, then select
                that saved voice from the Text To Speech page.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button(
        "🚀 Get Started — Voice Cloning",
        type="primary",
        use_container_width=True,
    ):
        st.session_state.page = "🎤 Voice Cloning"
        st.rerun()


# ============================================================
# VOICE CLONING
# ============================================================

elif page == "🎤 Voice Cloning":
    st.title("🎤 Voice Cloning")
    st.caption(
        "Upload a reference voice and save it with your own voice name."
    )

    st.markdown(
        '<div class="card">',
        unsafe_allow_html=True,
    )

    voice_name = st.text_input(
        "Voice Name",
        placeholder="Example: My Voice",
        max_chars=80,
    )

    uploaded_voice = st.file_uploader(
        "Upload Reference Voice",
        type=["wav", "mp3", "m4a", "ogg", "flac"],
    )

    save_voice = st.button(
        "💾 Save Voice",
        type="primary",
        use_container_width=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)

    if save_voice:
        clean_name = voice_name.strip()

        if not clean_name:
            st.error("Please enter a voice name.")
        elif uploaded_voice is None:
            st.error("Please upload a voice file.")
        else:
            safe_name = "".join(
                c
                if c.isalnum() or c in (" ", "_", "-")
                else "_"
                for c in clean_name
            ).strip()

            if not safe_name:
                st.error("Invalid voice name.")
            else:
                extension = Path(uploaded_voice.name).suffix.lower()
                destination = get_voice_dir() / f"{safe_name}{extension}"

                destination.write_bytes(
                    uploaded_voice.getbuffer()
                )

                st.success(
                    f'Voice "{clean_name}" saved successfully.'
                )
                st.rerun()

    voices = get_saved_voices()

    if voices:
        st.subheader("Your Saved Voices")

        for voice in voices:
            st.write(
                f"🎙️ **{voice.stem}** — `{voice.name}`"
            )
    else:
        st.info("No saved voices yet.")


# ============================================================
# TEXT TO SPEECH
# ============================================================

elif page == "🔊 Text To Speech":
    st.title("🔊 Text To Speech")

    voices = get_saved_voices()

    if not voices:
        st.warning(
            "No saved voice found. Go to Voice Cloning and save a voice first."
        )

        if st.button("🎤 Open Voice Cloning"):
            st.session_state.page = "🎤 Voice Cloning"
            st.rerun()

    else:
        voice_names = [v.stem for v in voices]

        selected_voice = st.selectbox(
            "🎙️ My Voice",
            voice_names,
        )

        selected_path = next(
            p for p in voices if p.stem == selected_voice
        )

        st.caption(
            f"Selected voice: {selected_path.name}"
        )

        text_input = st.text_area(
            "Enter Text",
            height=260,
            placeholder="Type your text here...",
        )

        current_count = character_count(text_input)
        remaining = int(
            account_profile.get("remaining_chars", 0)
        )

        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                "Current Characters",
                f"{current_count:,}",
            )

        with col2:
            st.metric(
                "Balance After Generation",
                f"{max(remaining - current_count, 0):,}",
            )

        if current_count > remaining:
            st.error(
                "Not enough characters in your balance."
            )

        generate = st.button(
            "⚡ Generate",
            type="primary",
            use_container_width=True,
        )

        if generate:
            if not text_input:
                st.error("Please enter text.")

            elif current_count > remaining:
                st.error(
                    "Character balance is insufficient."
                )

            else:
                generated, error = generate_with_kaggle(
                    text_input,
                    selected_path,
                )

                if error:
                    st.error(error)

                else:
                    # Deduct only after the external generation request
                    # succeeds. This prevents charging failed requests.
                    if deduct_characters(current_count):
                        if isinstance(generated, bytes):
                            st.audio(
                                generated,
                                format="audio/wav",
                            )
                            st.success(
                                f"{current_count:,} characters deducted."
                            )
                        elif isinstance(generated, dict):
                            audio_url = generated.get(
                                "audio_url"
                            )

                            if audio_url:
                                st.audio(audio_url)
                            else:
                                st.json(generated)

                            st.success(
                                f"{current_count:,} characters deducted."
                            )
                        else:
                            st.success(
                                "Generation completed."
                            )

                        st.rerun()
                    else:
                        st.error(
                            "Generation completed but character "
                            "balance could not be updated. "
                            "Contact the administrator."
                        )


# ============================================================
# SETTINGS
# ============================================================

elif page in ("⚙️ Settings", "Settings"):
    if (
        page == "Settings"
        and not account_profile.get("is_admin", False)
    ):
        st.title("⚙️ Settings")
    elif page == "⚙️ Settings":
        st.title("⚙️ Settings")
    else:
        st.title("⚙️ Administrator Settings")

    if account_profile.get("is_admin", False):
        st.info(
            "System-level GITHUB_PAT_TOKEN remains in Streamlit Secrets."
        )
    else:
        st.subheader("Kaggle Connection")

        st.info(
            "Enter your Kaggle username and API token. "
            "The actual GPU execution still requires a Kaggle "
            "Notebook/API endpoint configured by the administrator."
        )

        saved_username = account_profile.get(
            "kaggle_username",
            "",
        )

        saved_token = account_profile.get(
            "kaggle_token",
            "",
        )

        with st.form("kaggle_settings_form"):
            kaggle_username = st.text_input(
                "Kaggle Username",
                value=saved_username,
            )

            kaggle_token = st.text_input(
                "Kaggle API Token",
                value=saved_token,
                type="password",
            )

            save_kaggle = st.form_submit_button(
                "💾 Save Kaggle Settings",
                use_container_width=True,
            )

            if save_kaggle:
                if (
                    not kaggle_username.strip()
                    or not kaggle_token.strip()
                ):
                    st.error(
                        "Enter both Kaggle username and API token."
                    )

                elif save_kaggle_settings(
                    kaggle_username,
                    kaggle_token,
                ):
                    st.success(
                        "Kaggle settings saved."
                    )
                    st.rerun()


# ============================================================
# ADMIN USER REGISTRY
# ============================================================

elif page == "Active Users Registry":
    if not account_profile.get("is_admin", False):
        st.error("Administrator access required.")
        st.stop()

    st.title("👑 Active Users Registry")

    regular_users = [
        (name, info)
        for name, info in user_db.items()
        if not info.get("is_admin", False)
    ]

    if not regular_users:
        st.info(
            "No regular users are registered."
        )

    for u_name, u_info in regular_users:
        with st.expander(
            f"{u_name} — "
            f"{'🔴 Revoked' if u_info.get('is_revoked') else '🟢 Active'}"
        ):
            new_limit = st.number_input(
                "Remaining Characters",
                min_value=0,
                value=int(
                    u_info.get(
                        "remaining_chars",
                        0,
                    )
                ),
                key=f"limit_{u_name}",
            )

            add_days = st.number_input(
                "Extend Plan Days",
                min_value=0,
                value=0,
                key=f"days_{u_name}",
            )

            col1, col2 = st.columns(2)

            with col1:
                if st.button(
                    "🔴 Revoke / 🟢 Grant",
                    key=f"toggle_{u_name}",
                    use_container_width=True,
                ):
                    u_info["is_revoked"] = not u_info.get(
                        "is_revoked",
                        False,
                    )

                    if push_database_updates_to_github(
                        user_db
                    ):
                        st.rerun()

            with col2:
                if st.button(
                    "💾 Save Changes",
                    key=f"save_{u_name}",
                    use_container_width=True,
                ):
                    u_info["remaining_chars"] = int(
                        new_limit
                    )

                    if add_days > 0:
                        curr_exp = datetime.strptime(
                            u_info["expiry_timestamp"],
                            "%Y-%m-%d %H:%M:%S",
                        )

                        if curr_exp < datetime.now():
                            curr_exp = datetime.now()

                        u_info["expiry_timestamp"] = (
                            curr_exp
                            + timedelta(
                                days=int(add_days)
                            )
                        ).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )

                    if push_database_updates_to_github(
                        user_db
                    ):
                        st.rerun()


# ============================================================
# ADMIN DEPLOY
# ============================================================

elif page == "Deploy New SaaS Client":
    if not account_profile.get("is_admin", False):
        st.error("Administrator access required.")
        st.stop()

    st.title("➕ Deploy New SaaS Client")

    with st.form(
        "new_user_registration_form"
    ):
        reg_user = st.text_input(
            "New Client Username"
        ).upper().strip()

        reg_pass = st.text_input(
            "Set Login Password",
            type="password",
        )

        reg_days = st.number_input(
            "Plan Duration (Days)",
            min_value=1,
            value=30,
        )

        reg_chars = st.number_input(
            "Character Allocation",
            min_value=1000,
            value=1000000,
        )

        create_user = st.form_submit_button(
            "🚀 Deploy User",
            use_container_width=True,
        )

        if create_user:
            if not reg_user or not reg_pass:
                st.error(
                    "Username and password are required."
                )

            elif reg_user in user_db:
                st.error(
                    "That username already exists."
                )

            else:
                expiry = (
                    datetime.now()
                    + timedelta(
                        days=int(reg_days)
                    )
                ).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                user_db[reg_user] = {
                    "password": reg_pass,
                    "expiry_timestamp": expiry,
                    "total_limit": int(reg_chars),
                    "remaining_chars": int(reg_chars),
                    "is_revoked": False,
                    "is_admin": False,
                    "kaggle_username": "",
                    "kaggle_token": "",
                }

                if push_database_updates_to_github(
                    user_db
                ):
                    st.success(
                        f"User {reg_user} created successfully."
                    )
                    st.rerun()


# -------------------- FOOTER --------------------

st.markdown("---")
st.caption(
    "F5-TTS Premium SaaS Enterprise • Secure user workspace"
)
