import streamlit as st
import json
import hashlib
from transformers import pipeline
from datetime import datetime
import os


USERS_FILE = "users.json"
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({}, f)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def add_chat(email, chat_name):
    users = load_users()
    if "chats" not in users[email]:
        users[email]["chats"] = {}
    if chat_name not in users[email]["chats"]:
        users[email]["chats"][chat_name] = []
    save_users(users)

def add_message(email, chat_name, role, message):
    users = load_users()
    users[email]["chats"][chat_name].append({
        "role": role,
        "message": message,
        "time": str(datetime.now())
    })
    save_users(users)


st.set_page_config(page_title="Generative AI App made by Prem Mishra", page_icon=None, layout="wide")
st.markdown("""
<style>
body {background-color:#0f111a; color:#f0f0f5; font-family:'Segoe UI', sans-serif;}
h1{color:#00f6ff; text-align:center;}
.stButton>button{background:linear-gradient(90deg,#00f6ff,#1e90ff); color:#0f111a; font-weight:bold; border-radius:12px; height:40px; width:220px;}
.stButton>button:hover{background:linear-gradient(90deg,#1e90ff,#00f6ff); color:#fff;}
.stTextInput>div>input{border-radius:12px; border:1px solid #00f6ff; height:35px; background-color:#1a1c2a; color:#f0f0f5; padding-left:10px;}
/* Chat bubbles */
.user-bubble {
    background-color:#1f1f2e; color:#00f6ff; padding:10px; border-radius:15px; max-width:60%; margin-bottom:5px; float:left;
}
.ai-bubble {
    background-color:#1e90ff; color:#0f111a; padding:10px; border-radius:15px; max-width:60%; margin-bottom:5px; float:right;
}
.clear {clear:both;}
.avatar {
    width:30px; height:30px; border-radius:50%; background-color:#00f6ff; display:inline-block; margin-right:5px;
}
.sidebar .block-container {padding-top:1rem;}
</style>
""", unsafe_allow_html=True)

st.title("Generative AI App")  #
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "email" not in st.session_state:
    st.session_state.email = ""
if "current_chat" not in st.session_state:
    st.session_state.current_chat = ""
if "chat_list" not in st.session_state:
    st.session_state.chat_list = []


def signup_page():
    st.subheader("Signup")
    email = st.text_input("Email", key="signup_email")
    phone = st.text_input("Phone", key="signup_phone")
    password = st.text_input("Create Password", type="password", key="signup_pass")
    if st.button("Signup"):
        users = load_users()
        if email in users:
            st.error("Email already registered! Please login.")
        elif email=="" or password=="":
            st.warning("Email and Password required!")
        else:
            users[email] = {"password": hash_password(password), "phone": phone, "chats": {}}
            save_users(users)
            st.success("User registered! Please login.")

def login_page():
    st.subheader("Login")
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_pass")
    if st.button("Login"):
        users = load_users()
        if email in users and users[email]["password"] == hash_password(password):
            st.success("Logged in successfully!")
            st.session_state.logged_in = True
            st.session_state.email = email
            st.session_state.chat_list = list(users[email].get("chats", {}).keys())
            if st.session_state.chat_list:
                st.session_state.current_chat = st.session_state.chat_list[-1]
        else:
            st.error("Invalid email or password. If new user, please signup.")


if not st.session_state.logged_in:
    action = st.sidebar.selectbox("Choose Action", ["Login", "Signup"])
    if action == "Login":
        login_page()
    else:
        signup_page()
    st.stop()


st.sidebar.success(f"Logged in as: {st.session_state.email}")
if st.sidebar.button("Logout"):
    st.session_state.update({"logged_in": False, "email": "", "current_chat": "", "chat_list": []})
    st.experimental_rerun()

st.sidebar.subheader("Chats")
if st.sidebar.button("New Chat"):
    new_chat_name = f"Chat {len(st.session_state.chat_list)+1}"
    add_chat(st.session_state.email, new_chat_name)
    st.session_state.chat_list.append(new_chat_name)
    st.session_state.current_chat = new_chat_name


selected_chat = st.sidebar.radio(
    "Select Chat", 
    st.session_state.chat_list, 
    index=st.session_state.chat_list.index(st.session_state.current_chat) 
        if st.session_state.current_chat else 0
)
st.session_state.current_chat = selected_chat


st.subheader(f"Conversation: {st.session_state.current_chat}")
users = load_users()
conversation = users[st.session_state.email]["chats"].get(st.session_state.current_chat, [])


user_input = st.text_input("Enter your message here:", key="chat_input")
if st.button("Send"):
    if user_input.strip() != "":
        
        add_message(st.session_state.email, st.session_state.current_chat, "user", user_input)

        
        prompt_text = f"{user_input}\nAnswer in simple words only:"

       
        try:
            generator = pipeline("text-generation", model="gpt2")
            result = generator(prompt_text, max_length=150)
            ai_text = result[0]['generated_text']
        except Exception as e:
            ai_text = f"Error: {e}"

        
        add_message(st.session_state.email, st.session_state.current_chat, "ai", ai_text)


users = load_users()
conversation = users[st.session_state.email]["chats"].get(st.session_state.current_chat, [])
for msg in conversation[-20:]:
    role = msg.get("role","user")
    if role=="user":
        st.markdown(f"""
        <div class="user-bubble">
        <div class="avatar"></div>{msg.get('message','')}
        </div>
        <div class="clear"></div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="ai-bubble">{msg.get('message','')}</div>
        <div class="clear"></div>
        """, unsafe_allow_html=True)

