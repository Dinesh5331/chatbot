import streamlit as st
from dotenv import load_dotenv
import os
import sqlite3
import google.generativeai as genai

# Loading hte environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Database setup
conn = sqlite3.connect("chatbot_users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS chat_history (
    username TEXT,
    role TEXT,
    message TEXT
)
""")
conn.commit()

# Functions for signup/login
def signup_user(username, password):
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        return True
    except:
        return False

def login_user(username, password):
    cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    return cursor.fetchone()

def save_chat(username, role, message):
    cursor.execute("INSERT INTO chat_history (username, role, message) VALUES (?, ?, ?)", (username, role, message))
    conn.commit()

def get_chat_history(username):
    cursor.execute("SELECT role, message FROM chat_history WHERE username=?", (username,))
    return cursor.fetchall()

# Gemini model setup
model = genai.GenerativeModel("models/gemini-1.5-flash")
chat = model.start_chat(history=[])

def get_gemini_response(question):
    return chat.send_message(question, stream=True)

# Streamlit UI
st.set_page_config(page_title="Gemini Chatbot")
st.title("💬 Gemini Chatbot with Login")

# Session states
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = None

if not st.session_state.authenticated:
    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        login_user_input = st.text_input("Username", key="login_user")
        login_pass_input = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            if login_user(login_user_input, login_pass_input):
                st.session_state.authenticated = True
                st.session_state.username = login_user_input
                st.rerun()
            else:
                st.error("Invalid credentials.")

    with tab2:
        signup_user_input = st.text_input("New Username", key="signup_user")
        signup_pass_input = st.text_input("New Password", type="password", key="signup_pass")
        if st.button("Sign Up"):
            if signup_user(signup_user_input, signup_pass_input):
                st.success("Account created! Please log in.")
            else:
                st.error("Username already exists.")

else:
    st.success(f"Welcome, {st.session_state.username} 👋")
    
    # Load previous chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = get_chat_history(st.session_state.username)

    if "current_bot_response" not in st.session_state:
        st.session_state.current_bot_response = ""

    # handle user input when Enter is pressed
    def handle_input():
        user_message = st.session_state.chat_input.strip()
        if user_message:
            with st.spinner("Thinking..."):
                response_chunks = get_gemini_response(user_message)
                bot_response = ""
                for chunk in response_chunks:
                    bot_response += chunk.text

            st.session_state.current_bot_response = bot_response

            # Saving to database and session
            save_chat(st.session_state.username, "You", user_message)
            save_chat(st.session_state.username, "Bot", bot_response)

            st.session_state.chat_history.append(("You", user_message))
            st.session_state.chat_history.append(("Bot", bot_response))

            # Clearing input
            st.session_state.chat_input = ""

    # Input area with on_change
    st.text_input("Ask something...", key="chat_input", on_change=handle_input)

    # Show current response separately
    if st.session_state.current_bot_response:
        st.subheader("Chat Response")
        st.markdown(f"**Bot**: {st.session_state.current_bot_response}")

    # Show full chat history
    st.subheader("Chat History")
    for role, msg in st.session_state.chat_history:
        if role == "You":
            st.markdown(f"🧑 **{role}**: {msg}")
        else:
            st.markdown(f"🤖 **{role}**: {msg}")
