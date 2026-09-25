import streamlit as st
import json
import os
import base64
import subprocess
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import requests
import time

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
            "ngrok_auth_token": "",
            "ngrok_static_domain": "",
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


def save_kaggle_settings(
    username,
    token,
    ngrok_auth_token,
    ngrok_static_domain,
):
    account_profile["kaggle_username"] = username.strip()
    account_profile["kaggle_token"] = token.strip()
    account_profile["ngrok_auth_token"] = ngrok_auth_token.strip()
    account_profile["ngrok_static_domain"] = ngrok_static_domain.strip()
    return push_database_updates_to_github(user_db)


def generate_with_kaggle(text, voice_path, progress_callback=None):
    """
    Start a private Kaggle T4 worker, wait for its authenticated API to come
    online, upload the selected reference voice + text, and return the
    generated WAV bytes to Streamlit.
    """
    def report(percent, message):
        if progress_callback is not None:
            try:
                progress_callback(percent, message)
            except Exception:
                pass

    try:
        report(5, "Checking Kaggle and Ngrok connection fields...")

        k_user = str(account_profile.get("kaggle_username", "")).strip()
        k_token = str(account_profile.get("kaggle_token", "")).strip()
        n_auth = str(account_profile.get("ngrok_auth_token", "")).strip()
        n_domain = str(account_profile.get("ngrok_static_domain", "")).strip()

        if not k_user:
            return None, "Kaggle Username is missing in Settings."
        if not k_token:
            return None, "Kaggle API Token is missing in Settings."
        if not n_auth:
            return None, "Ngrok Auth Token is missing in Settings."
        if not n_domain:
            return None, "Ngrok Static Domain is missing in Settings."

        n_domain = (
            n_domain.replace("https://", "")
            .replace("http://", "")
            .strip("/")
        )

        if any(ch.isspace() for ch in n_domain):
            return None, "Ngrok Static Domain contains whitespace."

        worker_key = uuid.uuid4().hex + uuid.uuid4().hex

        raw_slug = (
            f"f5tts-{active_username.lower()}-"
            f"{uuid.uuid4().hex[:10]}"
        )
        kernel_slug = "".join(
            c if c.isalnum() or c == "-" else "-"
            for c in raw_slug
        ).strip("-")[:80]

        report(15, "Credentials look valid. Preparing the private Kaggle T4 worker...")

        workspace = Path(tempfile.mkdtemp(prefix="f5tts_kaggle_"))
        notebook_path = workspace / "active_worker.ipynb"
        server_path = workspace / "f5tts_worker_server.py"
        metadata_path = workspace / "kernel-metadata.json"

        server_code = '''import os
import tempfile
import threading
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse

PORT = 7860
WORKER_KEY = os.environ.get("F5_WORKER_KEY", "").strip()
NGROK_AUTH = os.environ.get("F5_NGROK_AUTH_TOKEN", "").strip()
NGROK_DOMAIN = os.environ.get("F5_NGROK_STATIC_DOMAIN", "").strip()

if not WORKER_KEY:
    raise RuntimeError("F5_WORKER_KEY is missing.")
if not NGROK_AUTH:
    raise RuntimeError("F5_NGROK_AUTH_TOKEN is missing.")
if not NGROK_DOMAIN:
    raise RuntimeError("F5_NGROK_STATIC_DOMAIN is missing.")

app = FastAPI(title="F5-TTS Private GPU Worker")
model_holder = {"model": None}
model_lock = threading.Lock()
inference_lock = threading.Lock()


def get_model():
    if model_holder["model"] is None:
        with model_lock:
            if model_holder["model"] is None:
                print("Loading F5-TTS model on Kaggle GPU...", flush=True)
                from f5_tts.api import F5TTS
                model_holder["model"] = F5TTS(
                    model="F5TTS_v1_Base",
                    device="cuda",
                )
                print("F5-TTS model loaded.", flush=True)
    return model_holder["model"]


@app.get("/health")
def health():
    return {
        "status": "online",
        "model_loaded": model_holder["model"] is not None,
    }


@app.post("/generate")
async def generate(
    text: str = Form(...),
    voice: UploadFile = File(...),
    authorization: str = Header(default=""),
):
    if authorization != f"Bearer {WORKER_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized worker request.")

    if not text.strip():
        raise HTTPException(status_code=400, detail="Text is empty.")

    suffix = Path(voice.filename or "voice.wav").suffix.lower()
    if suffix not in {".wav", ".mp3", ".m4a", ".ogg", ".flac"}:
        suffix = ".wav"

    with tempfile.TemporaryDirectory(prefix="f5_request_") as tmp:
        ref_path = Path(tmp) / f"reference{suffix}"
        out_path = Path(tmp) / "generated.wav"
        ref_path.write_bytes(await voice.read())

        if ref_path.stat().st_size == 0:
            raise HTTPException(status_code=400, detail="Reference voice file is empty.")

        print("Received TTS request.", flush=True)
        print("Reference:", ref_path, flush=True)
        print("Text length:", len(text), flush=True)

        try:
            with inference_lock:
                tts = get_model()
                tts.infer(
                    ref_file=str(ref_path),
                    ref_text="",
                    gen_text=text,
                    file_wave=str(out_path),
                    remove_silence=False,
                )

            if not out_path.exists() or out_path.stat().st_size < 1000:
                raise RuntimeError("F5-TTS completed without producing a valid WAV file.")

            print("Audio generated:", out_path.stat().st_size, "bytes", flush=True)
            return FileResponse(
                path=str(out_path),
                media_type="audio/wav",
                filename="f5tts_generated.wav",
            )

        except Exception as exc:
            print("Generation error:", repr(exc), flush=True)
            raise HTTPException(status_code=500, detail=str(exc)) from exc


def start_server():
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")


if __name__ == "__main__":
    from pyngrok import ngrok

    ngrok.set_auth_token(NGROK_AUTH)

    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    for _ in range(60):
        try:
            import requests
            response = requests.get(f"http://127.0.0.1:{PORT}/health", timeout=2)
            if response.ok:
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        raise RuntimeError("Local F5-TTS API did not start on port 7860.")

    tunnel = ngrok.connect(addr=PORT, proto="http", domain=NGROK_DOMAIN)
    print("F5-TTS public API:", tunnel.public_url, flush=True)
    print("F5-TTS worker is ready.", flush=True)

    while True:
        time.sleep(30)
'''

        server_path.write_text(server_code, encoding="utf-8")

        notebook_source = f'''import os
import subprocess
import sys
from pathlib import Path

os.environ["F5_WORKER_KEY"] = {worker_key!r}
os.environ["F5_NGROK_AUTH_TOKEN"] = {n_auth!r}
os.environ["F5_NGROK_STATIC_DOMAIN"] = {n_domain!r}

subprocess.check_call([
    sys.executable, "-m", "pip", "install", "-q", "--upgrade", "pip"
])

subprocess.check_call([
    sys.executable,
    "-m",
    "pip",
    "install",
    "-q",
    "f5-tts",
    "fastapi",
    "uvicorn",
    "python-multipart",
    "pyngrok",
    "requests",
])

subprocess.run(
    ["bash", "-lc", "fuser -k 7860/tcp || true"],
    check=False,
)

server_code = {server_code!r}
Path("/kaggle/working/f5tts_worker_server.py").write_text(
    server_code,
    encoding="utf-8",
)

print("Starting private F5-TTS T4 API worker...", flush=True)
subprocess.run(
    [sys.executable, "/kaggle/working/f5tts_worker_server.py"],
    check=True,
)
'''

        notebook = {
            "cells": [
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": notebook_source.splitlines(True),
                }
            ],
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3",
                },
                "language_info": {"name": "python"},
            },
            "nbformat": 4,
            "nbformat_minor": 5,
        }

        notebook_path.write_text(
            json.dumps(notebook, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        report(35, "Building the authenticated F5-TTS API worker...")

        metadata = {
            "id": f"{k_user}/{kernel_slug}",
            "title": kernel_slug,
            "code_file": "active_worker.ipynb",
            "language": "python",
            "kernel_type": "notebook",
            "is_private": True,
            "enable_gpu": True,
            "enable_internet": True,
            "machine_shape": "NvidiaTeslaT4",
            "dataset_sources": [],
            "competition_sources": [],
            "kernel_sources": [],
            "model_sources": [],
        }

        metadata_path.write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8",
        )

        report(50, "Worker package is ready. Connecting to your Kaggle account...")

        env = os.environ.copy()
        env["KAGGLE_USERNAME"] = k_user
        env["KAGGLE_API_TOKEN"] = k_token
        env["KAGGLE_KEY"] = k_token

        report(60, "Uploading notebook and requesting the Kaggle T4 GPU...")

        completed = subprocess.run(
            [
                "kaggle",
                "kernels",
                "push",
                "-p",
                str(workspace),
                "--timeout",
                "21600",
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )

        combined_output = (
            (completed.stdout or "").strip()
            + "\n"
            + (completed.stderr or "").strip()
        ).strip()

        if completed.returncode != 0:
            report(100, "Kaggle rejected the GPU worker request.")
            return None, (
                "Kaggle kernel push failed "
                f"(exit code {completed.returncode}).\n"
                f"{combined_output}"
            )

        report(68, "Kaggle accepted the notebook. Waiting for the GPU API to come online...")

        base_url = f"https://{n_domain}"
        health_url = f"{base_url}/health"
        generate_url = f"{base_url}/generate"

        last_health_error = ""
        for attempt in range(1, 121):
            try:
                health = requests.get(health_url, timeout=8)
                if health.ok:
                    report(75, "Kaggle GPU worker is online. Sending the reference voice and text...")
                    break
                last_health_error = f"HTTP {health.status_code}: {health.text[:500]}"
            except requests.RequestException as exc:
                last_health_error = str(exc)

            if attempt % 10 == 0:
                report(
                    min(88, 68 + attempt // 4),
                    f"Waiting for Kaggle worker startup... ({attempt}/120)",
                )
            time.sleep(3)
        else:
            return None, (
                "Kaggle accepted the notebook, but the F5-TTS API did not "
                "come online within 6 minutes.\n"
                f"Last health-check error: {last_health_error}\n\n"
                f"Worker URL: {base_url}"
            )

        report(80, "Uploading the selected voice to the Kaggle GPU worker...")

        with open(voice_path, "rb") as voice_file:
            files = {
                "voice": (
                    Path(voice_path).name,
                    voice_file,
                    "audio/wav",
                )
            }
            data = {"text": text}
            headers = {"Authorization": f"Bearer {worker_key}"}

            try:
                result = requests.post(
                    generate_url,
                    headers=headers,
                    data=data,
                    files=files,
                    timeout=1800,
                )
            except requests.RequestException as exc:
                return None, (
                    "Could not reach the Kaggle F5-TTS generation API.\n"
                    f"{exc}\n\nWorker URL: {base_url}"
                )

        if result.status_code != 200:
            detail = result.text[:5000]
            try:
                payload = result.json()
                detail = str(payload.get("detail", detail))
            except Exception:
                pass

            report(100, "Kaggle F5-TTS returned a generation error.")
            return None, (
                f"F5-TTS worker generation failed (HTTP {result.status_code}).\n"
                f"{detail}\n\nWorker URL: {base_url}"
            )

        audio_bytes = result.content
        if len(audio_bytes) < 1000 or not audio_bytes.startswith(b"RIFF"):
            report(100, "Worker responded, but the returned file was not a valid WAV audio file.")
            return None, (
                "The Kaggle worker responded successfully, but the returned "
                "payload was not a valid WAV audio file."
            )

        report(100, "F5-TTS generated the audio successfully and returned it to Streamlit.")
        return audio_bytes, None

    except FileNotFoundError:
        report(100, "Kaggle CLI is not installed on the Streamlit server.")
        return None, (
            "Kaggle CLI was not found on the Streamlit server. "
            "Install it with: pip install kaggle"
        )

    except subprocess.TimeoutExpired as exc:
        report(100, "Kaggle upload timed out.")
        details = ""
        if exc.stdout:
            details += str(exc.stdout)
        if exc.stderr:
            details += "\n" + str(exc.stderr)
        return None, (
            "Kaggle kernel push timed out after 600 seconds.\n"
            f"{details}".strip()
        )

    except Exception as exc:
        report(100, "The GPU worker setup stopped with an unexpected error.")
        return None, f"Kaggle infrastructure error: {exc}"


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
                progress_box = st.empty()
                progress_bar = st.progress(0)
                status_box = st.empty()

                def generation_progress(percent, message):
                    progress_bar.progress(
                        max(0, min(100, int(percent)))
                    )
                    status_box.info(
                        f"🔄 {message}"
                    )

                generation_progress(
                    2,
                    "Generation request started. Do not close this page.",
                )

                with st.status(
                    "⚙️ F5-TTS generation in progress...",
                    expanded=True,
                ) as generation_status:
                    generated, error = generate_with_kaggle(
                        text_input,
                        selected_path,
                        progress_callback=generation_progress,
                    )

                    if error:
                        generation_status.update(
                            label="❌ Generation stopped",
                            state="error",
                            expanded=True,
                        )
                        progress_bar.progress(100)
                        status_box.error(
                            "The request did not complete. See the diagnostic below."
                        )
                        st.error(error)
                        st.code(
                            error,
                            language="text",
                        )

                    else:
                        generation_status.update(
                            label="✅ Kaggle worker accepted the request",
                            state="complete",
                            expanded=True,
                        )

                        # Only charge the wallet when an actual audio
                        # result was returned. A workspace URL alone is
                        # not proof that audio was generated.
                        audio_received = False

                        if isinstance(generated, bytes):
                            audio_received = True
                            st.audio(
                                generated,
                                format="audio/wav",
                            )

                        elif isinstance(generated, dict):
                            audio_url = generated.get(
                                "audio_url"
                            )

                            if audio_url:
                                audio_received = True
                                st.audio(audio_url)
                            else:
                                st.json(generated)

                        elif isinstance(generated, str):
                            st.warning(
                                "⚠️ Kaggle accepted the worker, but this request "
                                "returned only the workspace URL — no audio file "
                                "was returned yet."
                            )
                            st.markdown(
                                f"**Secure workspace:** [{generated}]({generated})"
                            )

                        if audio_received:
                            if deduct_characters(current_count):
                                st.success(
                                    f"✅ Audio generated successfully. "
                                    f"{current_count:,} characters deducted."
                                )
                                status_box.success(
                                    "✅ Audio output received and wallet updated."
                                )
                            else:
                                st.error(
                                    "Audio was generated, but the character "
                                    "balance could not be updated. Contact the administrator."
                                )
                                status_box.warning(
                                    "⚠️ Audio received, but wallet update failed."
                                )
                        else:
                            status_box.warning(
                                "⚠️ No audio file was returned, so no characters were deducted."
                            )

                        progress_box.empty()



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
        st.subheader("Kaggle + Ngrok Connection")

        st.info(
            "Enter the four connection fields used by the GPU worker."
        )

        saved_username = account_profile.get(
            "kaggle_username",
            "",
        )

        saved_token = account_profile.get(
            "kaggle_token",
            "",
        )

        saved_ngrok_auth = account_profile.get(
            "ngrok_auth_token",
            "",
        )

        saved_ngrok_domain = account_profile.get(
            "ngrok_static_domain",
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

            ngrok_auth_token = st.text_input(
                "Ngrok Auth Token",
                value=saved_ngrok_auth,
                type="password",
            )

            ngrok_static_domain = st.text_input(
                "Ngrok Static Domain",
                value=saved_ngrok_domain,
                placeholder="your-domain.ngrok.app",
            )

            save_kaggle = st.form_submit_button(
                "💾 Save Connection Settings",
                use_container_width=True,
            )

            if save_kaggle:
                if (
                    not kaggle_username.strip()
                    or not kaggle_token.strip()
                    or not ngrok_auth_token.strip()
                    or not ngrok_static_domain.strip()
                ):
                    st.error(
                        "Enter Kaggle Username, Kaggle API Token, "
                        "Ngrok Auth Token and Ngrok Static Domain."
                    )

                elif save_kaggle_settings(
                    kaggle_username,
                    kaggle_token,
                    ngrok_auth_token,
                    ngrok_static_domain,
                ):
                    st.success(
                        "Kaggle + Ngrok settings saved."
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
                    "ngrok_auth_token": "",
                    "ngrok_static_domain": "",
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
