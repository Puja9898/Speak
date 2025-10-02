import streamlit as st
import sqlite3
import hashlib
from googletrans import Translator
import speech_recognition as sr
import tempfile
import os

# -------------------- DATABASE --------------------
conn = sqlite3.connect("translations.db")
cursor = conn.cursor()

# Users table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    preferred_lang TEXT
)
""")

# Translations table
cursor.execute("""
CREATE TABLE IF NOT EXISTS translations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    original_text TEXT,
    translated_text TEXT,
    src_lang TEXT,
    dest_lang TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
""")
conn.commit()

# -------------------- HELPER FUNCTIONS --------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate(username, password):
    cursor.execute("SELECT id, preferred_lang, password FROM users WHERE username=?", (username,))
    result = cursor.fetchone()
    if result and result[2] == hash_password(password):
        return result[0], result[1]  # return user_id and preferred_lang
    return None, None

# -------------------- LOGIN / REGISTER --------------------
st.sidebar.title("🔐 Login / Register")
choice = st.sidebar.radio("Choose Action", ["Login", "Register"])

user_id = None
preferred_lang = None

if choice == "Register":
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    lang = st.sidebar.selectbox("Preferred Language", ["English","hindi","telugu","tamil","kannada","malayalam","marathi","bengali","gujarati","punjabi","urdu","spanish","french","german","chinese"])
    if st.sidebar.button("Register"):
        try:
            cursor.execute("INSERT INTO users (username, password, preferred_lang) VALUES (?, ?, ?)",
                           (username, hash_password(password), lang))
            conn.commit()
            st.sidebar.success("User registered! Please login.")
        except sqlite3.IntegrityError:
            st.sidebar.error("Username already exists!")

else:  # Login
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        user_id, preferred_lang = authenticate(username, password)
        if user_id:
            st.sidebar.success(f"Logged in as {username}")
        else:
            st.sidebar.error("Invalid credentials")

# -------------------- MAIN APP --------------------
if user_id:
    st.title(f"Welcome {username}! 🎓")
    
    LANGUAGES = {
        "English": "en", "hindi": "hi", "telugu": "te", "tamil": "ta",
        "kannada": "kn", "malayalam": "ml", "marathi": "mr", "bengali": "bn",
        "gujarati": "gu", "punjabi": "pa", "urdu": "ur", "spanish": "es",
        "french": "fr", "german": "de", "chinese": "zh-cn"
    }

    src_lang = st.selectbox("Source Language", list(LANGUAGES.keys()))
    dest_lang = st.selectbox("Target Language", list(LANGUAGES.keys()), index=list(LANGUAGES.keys()).index(preferred_lang))

    input_method = st.radio("Input Method", ["Text", "Audio File"], horizontal=True)

    user_input = ""
    if input_method == "Text":
        user_input = st.text_area("Enter Text")
    else:
        audio_file = st.file_uploader("Upload Audio", type=["wav"])
        if audio_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(audio_file.getvalue())
                recognizer = sr.Recognizer()
                with sr.AudioFile(tmp.name) as source:
                    audio = recognizer.record(source)
                    try:
                        user_input = recognizer.recognize_google(audio)
                        st.write("Detected Speech:", user_input)
                    except:
                        st.error("Could not recognize audio")
            os.unlink(tmp.name)

    if st.button("Translate") and user_input:
        translator = Translator()
        translated_text = translator.translate(user_input, src=LANGUAGES[src_lang], dest=LANGUAGES[dest_lang]).text
        st.success(translated_text)

        # Save to database
        cursor.execute("""
            INSERT INTO translations (user_id, original_text, translated_text, src_lang, dest_lang)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, user_input, translated_text, src_lang, dest_lang))
        conn.commit()

    # Show user-specific history
    st.markdown("### Your Translation History (Last 10)")
    cursor.execute("""
        SELECT original_text, translated_text, src_lang, dest_lang, timestamp 
        FROM translations WHERE user_id=? ORDER BY id DESC LIMIT 10
    """, (user_id,))
    rows = cursor.fetchall()
    for row in rows:
        st.write(f"[{row[4]}] **{row[2]} → {row[3]}**: {row[0]} → {row[1]}")

conn.close()
