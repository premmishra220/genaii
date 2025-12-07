import html
import streamlit as st
import json
import hashlib
from transformers import pipeline
from datetime import datetime
import os

# -----------------------------
# Files & helpers
# -----------------------------
USERS_FILE = "users.json"
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({}, f)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def load_users() -> dict:
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users: dict):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def ensure_user_record(email: str):
    users = load_users()
    if email not in users:
        users[email] = {"password": "", "phone": "", "chats": {}}
        save_users(users)

def add_chat(email: str, chat_name: str):
    users = load_users()
    ensure_user_record(email)
    if "chats" not in users[email]:
        users[email]["chats"] = {}
    if chat_name not in users[email]["chats"]:
        users[email]["chats"][chat_name] = []
    save_users(users)

def add_message(email: str, chat_name: str, role: str, message: str):
    users = load_users()
    ensure_user_record(email)
    if "chats" not in users[email]:
        users[email]["chats"] = {}
    if chat_name not in users[email]["chats"]:
        users[email]["chats"][chat_name] = []
    users[email]["chats"][chat_name].append({
        "role": role,
        "message": message,
        "time": str(datetime.now())
    })
    save_users(users)

# -----------------------------
# Page header / config
# -----------------------------
st.set_page_config(page_title="Generative AI App", page_icon=None, layout="wide")
st.markdown("""
<style>
/* Basic dark theme + header */
body {background-color:#0f111a; color:#f0f0f5; font-family:'Segoe UI', sans-serif;}
.header-title {text-align: left; font-size: 28px; font-weight: 700; color:#ffffff; margin-bottom: 0.1rem;}
.header-sub {text-align: left; font-size: 14px; color:#9ad1ff; margin-top:0;}
.app-container { padding-top: 10px; }
/* Controls */
.stButton>button { background: linear-gradient(90deg,#00f6ff,#1e90ff); color:#0f111a; font-weight:600; border-radius:10px; height:36px; width:180px; }
.stButton>button:hover { opacity:0.95; }
/* Inputs */
.stTextInput>div>input { border-radius:8px; border:1px solid #00f6ff; height:36px; background-color:#1a1c2a; color:#f0f0f5; padding-left:10px; }
/* Chat bubbles */
.user-bubble { background-color:#151526; color:#cbefff; padding:10px; border-radius:12px; max-width:70%; margin-bottom:8px; float:left; }
.ai-bubble { background-color:#00c2ff; color:#031021; padding:10px; border-radius:12px; max-width:70%; margin-bottom:8px; float:right; }
.clear { clear:both; }
.avatar { width:28px; height:28px; border-radius:50%; background-color:#00f6ff; display:inline-block; margin-right:8px; vertical-align:middle; }
.sidebar .block-container { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)

# Header with your name (clean)
st.markdown(f"""
<div style="display:flex; align-items:center; justify-content:space-between;">
  <div>
    <div class="header-title">Generative AI App</div>
    <div class="header-sub">Made by <strong>Prem Prakash Mishra</strong></div>
  </div>
  <div style="text-align:right; color:#9aaed8; font-size:12
  </div>
</div>
<hr>
""", unsafe_allow_html=True)

# -----------------------------
# Session state defaults
# -----------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "email" not in st.session_state:
    st.session_state.email = ""
if "current_chat" not in st.session_state:
    st.session_state.current_chat = ""
if "chat_list" not in st.session_state:
    st.session_state.chat_list = []
if "generator_loaded" not in st.session_state:
    st.session_state.generator_loaded = False
if "generator" not in st.session_state:
    st.session_state.generator = None

# -----------------------------
# Auth: Signup / Login
# -----------------------------
def signup_form():
    st.subheader("Signup")
    email = st.text_input("Email", key="signup_email")
    phone = st.text_input("Phone", key="signup_phone")
    password = st.text_input("Create Password", type="password", key="signup_pass")
    if st.button("Signup"):
        if not email or not password:
            st.warning("Email and Password are required.")
            return
        users = load_users()
        if email in users:
            st.error("Email already registered. Please login.")
            return
        users[email] = {"password": hash_password(password), "phone": phone, "chats": {}}
        save_users(users)
        st.success("Signup successful. Please switch to Login and sign in.")

def login_form():
    st.subheader("Login")
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_pass")
    if st.button("Login"):
        users = load_users()
        if email in users and users[email]["password"] == hash_password(password):
            st.success("Logged in successfully.")
            st.session_state.logged_in = True
            st.session_state.email = email
            # load chat list
            st.session_state.chat_list = list(users[email].get("chats", {}).keys())
            # if no chat present create default
            if not st.session_state.chat_list:
                add_chat(email, "Chat 1")
                st.session_state.chat_list = list(load_users()[email].get("chats", {}).keys())
            # set current chat to last
            st.session_state.current_chat = st.session_state.chat_list[-1]
        else:
            st.error("Invalid credentials. If you're new, please Signup.")

# Show auth options in sidebar
if not st.session_state.logged_in:
    choice = st.sidebar.selectbox("Account", ["Login", "Signup"])
    if choice == "Login":
        login_form()
    else:
        signup_form()
    st.stop()

# -----------------------------
# Sidebar: user info, chats
# -----------------------------
st.sidebar.success(f"Logged in as: {st.session_state.email}")
if st.sidebar.button("Logout"):
    st.session_state.update({"logged_in": False, "email": "", "current_chat": "", "chat_list": []})
    st.experimental_rerun()

st.sidebar.subheader("Chats")
if st.sidebar.button("New Chat"):
    # create a new chat and switch to it
    new_name = f"Chat {len(st.session_state.chat_list) + 1}"
    add_chat(st.session_state.email, new_name)
    st.session_state.chat_list.append(new_name)
    st.session_state.current_chat = new_name

# chat list radio - only show if there are chats
if st.session_state.chat_list:
    selected = st.sidebar.radio("Select Chat", st.session_state.chat_list, index=st.session_state.chat_list.index(st.session_state.current_chat) if st.session_state.current_chat in st.session_state.chat_list else 0)
    st.session_state.current_chat = selected
else:
    st.sidebar.info("No chats yet. Click 'New Chat' to start.")

# -----------------------------
# Main chat area
# -----------------------------
st.subheader(f"Conversation: {st.session_state.current_chat or 'No chat selected'}")
users = load_users()
# ensure current chat exists (defensive)
if st.session_state.current_chat == "" or st.session_state.current_chat not in users.get(st.session_state.email, {}).get("chats", {}):
    # create default if missing
    default_name = "Chat 1"
    add_chat(st.session_state.email, default_name)
    st.session_state.chat_list = list(load_users()[st.session_state.email].get("chats", {}).keys())
    st.session_state.current_chat = default_name

conversation = load_users()[st.session_state.email]["chats"].get(st.session_state.current_chat, [])

# input area
user_input = st.text_input("Enter your message here:", key="chat_input")
if st.button("Send"):
    if user_input and user_input.strip():
        # save user message
        add_message(st.session_state.email, st.session_state.current_chat, "user", user_input.strip())

        
        prompt_text = f"{user_input.strip()}\nAnswer in simple words only."

       
        if not st.session_state.generator_loaded:
            try:
                st.info("Loading text-generation model (first-time, may take a while)...")
                st.session_state.generator = pipeline("text-generation", model="gpt2")
                st.session_state.generator_loaded = True
            except Exception as e:
                # model failed to load; save error in chat and continue
                add_message(st.session_state.email, st.session_state.current_chat, "ai", f"Model load error: {e}")
                st.error("Model load failed. Check logs and requirements.")
                st.experimental_rerun()

      
        try:
            gen = st.session_state.generator
            res = gen(prompt_text, max_length=150, do_sample=False)
            ai_text = res[0]["generated_text"]
        except Exception as e:
            ai_text = f"Generation error: {e}"

        
        add_message(st.session_state.email, st.session_state.current_chat, "ai", ai_text)

        
        conversation = load_users()[st.session_state.email]["chats"].get(st.session_state.current_chat, [])

#
conversation = load_users()[st.session_state.email]["chats"].get(st.session_state.current_chat, [])
for msg in conversation[-50:]:
    role = msg.get("role", "user")
    if role == "user":
        st.markdown(f"""
        <div class="user-bubble">
          <div style="display:flex; align-items:center;">
            <div class="avatar"></div>
           <div style="display:inline-block; vertical-align:middle;">{msg.get('message','')}</div>

          </div>
        </div>
        <div class="clear"></div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
      <div class="ai-bubble">{msg.get('message','')}</div>

        <div class="clear"></div>
        """, unsafe_allow_html=True)


st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center; color:#9aaed8; font-size:13px; margin-top:8px;">
Made with care by <strong>Prem Prakash Mishra</strong>
</div>
""", unsafe_allow_html=True)



