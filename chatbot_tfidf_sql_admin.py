import streamlit as st
import mysql.connector
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import bcrypt
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Fungsi untuk menghubungkan ke database
def connect_to_database():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",  # Ganti dengan password MySQL Anda
            database="chatbot_db"
        )
        logger.info("Koneksi ke database berhasil!")
        return conn
    except mysql.connector.Error as err:
        logger.error(f"Error connecting to database: {err}")
        return None

# Inisialisasi database
def init_db():
    conn = connect_to_database()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS faq (
                id INT AUTO_INCREMENT PRIMARY KEY,
                question TEXT UNIQUE,
                answer TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pending (
                id INT AUTO_INCREMENT PRIMARY KEY,
                question TEXT UNIQUE,
                answer TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin (
                username VARCHAR(255) PRIMARY KEY,
                password VARCHAR(255)
            )
        """)
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully!")

# Load FAQ data
def load_faq():
    conn = connect_to_database()
    if conn:
        df = pd.read_sql("SELECT * FROM faq", conn)
        conn.close()
        return df
    return pd.DataFrame()

# Load pending questions
def load_pending():
    conn = connect_to_database()
    if conn:
        df = pd.read_sql("SELECT * FROM pending", conn)
        conn.close()
        return df
    return pd.DataFrame()

# Add pending question
def add_pending(question, answer):
    conn = connect_to_database()
    if conn:
        cursor = conn.cursor()
        cursor.execute("INSERT IGNORE INTO pending (question, answer) VALUES (%s, %s)", (question, answer))
        conn.commit()
        conn.close()
        logger.info("Pertanyaan berhasil ditambahkan ke pending.")

# Approve question to FAQ
def approve_question(question, answer):
    conn = connect_to_database()
    if conn:
        cursor = conn.cursor()
        cursor.execute("INSERT IGNORE INTO faq (question, answer) VALUES (%s, %s)", (question, answer))
        cursor.execute("DELETE FROM pending WHERE question = %s", (question,))
        conn.commit()
        conn.close()
        logger.info("Pertanyaan berhasil disetujui dan dipindahkan ke FAQ.")

# Reject question from pending
def reject_question(question):
    conn = connect_to_database()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pending WHERE question = %s", (question,))
        conn.commit()
        conn.close()
        logger.info("Pertanyaan berhasil ditolak dan dihapus dari pending.")

# Authenticate admin
def authenticate(username, password):
    conn = connect_to_database()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM admin WHERE username = %s", (username,))
        stored_password = cursor.fetchone()
        conn.close()
        if stored_password and bcrypt.checkpw(password.encode('utf-8'), stored_password[0].encode('utf-8')):
            logger.info("Admin login successful!")
            return True
    logger.warning("Admin login failed!")
    return False

# Chatbot response
def chatbot_response(user_input, faq_data):
    if faq_data.empty:
        st.warning("Database FAQ kosong. Admin perlu menambahkan pertanyaan dan jawaban.")
        return None
    
    vectorizer = TfidfVectorizer()
    questions = faq_data['question'].tolist() + [user_input]
    tfidf_matrix = vectorizer.fit_transform(questions)
    cosine_similarities = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1])
    best_match_idx = cosine_similarities.argmax()
    highest_similarity = cosine_similarities[0, best_match_idx]
    
    if highest_similarity < 0.3:
        return None
    
    return faq_data.iloc[best_match_idx]['answer']

# Streamlit UI
st.title("Chatbot dengan MySQL dan Login Admin")
st.write("Tanyakan sesuatu, dan jika tidak ada jawaban, admin bisa menambahkannya!")

# Initialize database and load FAQ
init_db()
faq_data = load_faq()

# User input
user_input = st.text_input("You: ", "")
if user_input:
    response = chatbot_response(user_input, faq_data)
    if response:
        st.write(f"Chatbot: {response}")
    else:
        st.write("Chatbot: Saya belum tahu jawabannya. Anda bisa menambahkannya.")
        new_answer = st.text_input("Tambahkan jawaban:")
        if new_answer:
            add_pending(user_input, new_answer)
            st.success("Jawaban telah dikirim ke admin untuk ditinjau.")

# Admin login
st.sidebar.subheader("Admin Login")
admin_username = st.sidebar.text_input("Username")
admin_password = st.sidebar.text_input("Password", type="password")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if st.sidebar.button("Login"):
    if authenticate(admin_username, admin_password):
        st.session_state.logged_in = True
        st.sidebar.success("Login berhasil!")
    else:
        st.sidebar.error("Login gagal. Coba lagi!")

# Admin moderation
if st.session_state.logged_in:
    st.subheader("Moderasi Admin")
    pending_data = load_pending()
    if not pending_data.empty:
        for _, row in pending_data.iterrows():
            st.write(f"**Pertanyaan:** {row['question']}")
            st.write(f"**Jawaban:** {row['answer']}")
            col1, col2 = st.columns([0.3, 0.7])
            with col1:
                if st.button(f"✔️ Setujui {row['question']}", key=f"approve_{row['question']}"):
                    approve_question(row['question'], row['answer'])
                    st.experimental_rerun()
            with col2:
                if st.button(f"❌ Tolak {row['question']}", key=f"reject_{row['question']}"):
                    reject_question(row['question'])
                    st.experimental_rerun()
    else:
        st.write("Tidak ada pertanyaan yang menunggu moderasi.")