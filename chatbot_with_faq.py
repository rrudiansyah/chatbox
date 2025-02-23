import streamlit as st
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode, DataReturnMode, GridUpdateMode
import os
import bcrypt

# File paths
DATA_FILE = "faq_data.csv"
USER_FILE = "users.csv"
LOG_FILE = "audit_log.csv"
USER_QUESTIONS_FILE = "user_questions.csv"

# Initialize files if they don't exist
if not os.path.exists(DATA_FILE):
    df = pd.DataFrame({"tag": [], "question": [], "answer": []})
    df.to_csv(DATA_FILE, index=False)

if not os.path.exists(USER_FILE):
    users_df = pd.DataFrame({"username": [], "password": [], "role": []})
    users_df.to_csv(USER_FILE, index=False)

if not os.path.exists(LOG_FILE):
    log_df = pd.DataFrame({"username": [], "action": [], "details": []})
    log_df.to_csv(LOG_FILE, index=False)

if not os.path.exists(USER_QUESTIONS_FILE):
    user_questions_df = pd.DataFrame({"question": []})
    user_questions_df.to_csv(USER_QUESTIONS_FILE, index=False)

# Helper functions
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

def check_password(password, hashed_password):
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode()
    return bcrypt.checkpw(password.encode(), hashed_password)

def load_faq():
    try:
        return pd.read_csv(DATA_FILE)
    except Exception as e:
        st.error(f"Gagal memuat file FAQ: {e}")
        return pd.DataFrame({"tag": [],"question": [], "answer": []})

def save_faq(df):
    try:
        df.to_csv(DATA_FILE, index=False)
    except Exception as e:
        st.error(f"Gagal menyimpan file FAQ: {e}")

def load_users():
    try:
        return pd.read_csv(USER_FILE)
    except Exception as e:
        st.error(f"Gagal memuat file pengguna: {e}")
        return pd.DataFrame({"username": [], "password": [], "role": []})

def save_users(df):
    try:
        df.to_csv(USER_FILE, index=False)
    except Exception as e:
        st.error(f"Gagal menyimpan file pengguna: {e}")

def load_logs():
    try:
        return pd.read_csv(LOG_FILE)
    except Exception as e:
        st.error(f"Gagal memuat file log: {e}")
        return pd.DataFrame({"username": [], "action": [], "details": []})

def save_log(username, action, details):
    try:
        log_df = load_logs()
        new_log = pd.DataFrame({"username": [username], "action": [action], "details": [details]})
        log_df = pd.concat([log_df, new_log], ignore_index=True)
        log_df.to_csv(LOG_FILE, index=False)
    except Exception as e:
        st.error(f"Gagal menyimpan log: {e}")

def load_user_questions():
    try:
        return pd.read_csv(USER_QUESTIONS_FILE)
    except Exception as e:
        st.error(f"Gagal memuat file pertanyaan user: {e}")
        return pd.DataFrame({"question": []})

def save_user_questions(df):
    try:
        df.to_csv(USER_QUESTIONS_FILE, index=False)
    except Exception as e:
        st.error(f"Gagal menyimpan file pertanyaan user: {e}")

# @st.cache
def compute_tfidf(questions):
    vectorizer = TfidfVectorizer(stop_words="english")
    return vectorizer.fit_transform(questions)

def chatbot_response(user_input, faq_data):
    if faq_data.empty:
        st.warning("Database FAQ kosong. Admin perlu menambahkan pertanyaan dan jawaban.")
        return None
    
    questions = faq_data['question'].tolist() + [user_input]
    tfidf_matrix = compute_tfidf(questions)
    cosine_similarities = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1])
    best_match_idx = cosine_similarities.argmax()
    highest_similarity = cosine_similarities[0, best_match_idx]
    
    if highest_similarity < 0.3:
        return None
    
    return faq_data.iloc[best_match_idx]['answer']

def authenticate(username, password):
    users_df = load_users()
    user = users_df[users_df["username"] == username]
    if not user.empty:
        hashed_password = user.iloc[0]["password"]
        if check_password(password, hashed_password):
            return user.iloc[0]["role"]
    return None

def register_user(username, password, role="user"):
    users_df = load_users()
    if username in users_df["username"].values:
        return False  # Username already exists
    hashed_password = hash_password(password)
    new_user = pd.DataFrame({"username": [username], "password": [hashed_password], "role": [role]})
    users_df = pd.concat([users_df, new_user], ignore_index=True)
    save_users(users_df)
    return True

def reset_password(username, new_password):
    users_df = load_users()
    if username in users_df["username"].values:
        hashed_password = hash_password(new_password)
        users_df.loc[users_df["username"] == username, "password"] = hashed_password
        save_users(users_df)
        return True
    return False

# Session State untuk menyimpan state aplikasi
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "role" not in st.session_state:
    st.session_state.role = None

def logout():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.sidebar.success("Anda telah berhasil logout.")

def admin_login():
    st.sidebar.title("Login Admin")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login", key="login_button"):
        if not username or not password:
            st.sidebar.error("Username dan password tidak boleh kosong.")
        else:
            role = authenticate(username, password)
            if role == "admin":
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.role = role
                st.sidebar.success(f"Login berhasil sebagai {role}!")
                save_log(username, "Login", "Admin logged in successfully")
            else:
                st.sidebar.error("Login gagal. Periksa kembali username dan password.")

# Session State untuk menyimpan user_input sementara
if "user_input" not in st.session_state:
    st.session_state.user_input = ""
if "new_question" not in st.session_state:
    st.session_state.new_question = ""
if "new_answer" not in st.session_state:
    st.session_state.new_answer = ""

def main():
    st.title("Chatbot FAQ dengan Rahmad Rudiansyah Siregar")
    st.write("Tanyakan sesuatu, dan saya akan mencoba menjawab!")
    # Tampilkan form untuk memasukkan pertanyaan
    faq_df = load_faq()
    user_input = st.text_input("Anda:")
    tombol_tanya = st.button("Tanya")
    if user_input.strip() or tombol_tanya:
        response = chatbot_response(user_input,faq_df)
        if response:
            st.write(f"🤖 Bot : {response}")
        else:
            st.write("🤖 Bot : Saya belum tahu jawabannya. Anda bisa menambahkannya.")
            # tanya_baru = st.text_input("Tambahkan Pertanyaan Anda")
            tanya_baru = st.button("Ajukan Pertanyaan")
            if tanya_baru:
                 user_questions_df = load_user_questions()
                 if user_input not in user_questions_df["question"].values:
                    tambah_question = pd.DataFrame({"question": [user_input]})
                    user_questions_df = pd.concat([user_questions_df, tambah_question], ignore_index=True)
                    save_user_questions(user_questions_df)
                    st.success("Pertanyaan Anda telah diajukan. Terima kasih!")
                    st.session_state.user_input = ""
                 else:
                    st.warning("Pertanyaan ini sudah pernah diajukan sebelumnya.")
                    user_input = ""

    # Fitur admin (hanya untuk admin yang login)
    if st.session_state.logged_in and st.session_state.role == "admin":
        with st.sidebar.expander("Manajemen FAQ"):
            st.write("Tambahkan pertanyaan dan jawaban ke FAQ:")
            new_tag = st.selectbox("Pilih Tag :",
                                   ("Satyalancana Karya Satya SLKS",
                                    "Cuti PNS",
                                    "Cuti PPPK",
                                    "Aplikasi Ekinerja BKN",
                                    "Aplikasi Ekinerja Sumut"),
                                    key="input_new_tag")
            new_question = st.text_area("Pertanyaan Baru", key="input_new_question")
            new_answer = st.text_area("Jawaban Baru", st.session_state.new_answer, key="input_new_answer")
            if st.button("Tambahkan ke FAQ",key="tambah_faq_button"):
                if new_question.strip() and new_answer.strip():
                    faq_df = load_faq()
                    if new_question not in faq_df["question"].values:
                        new_entry = pd.DataFrame({"tag": [new_tag], "question": [new_question], "answer": [new_answer]})
                        faq_df = pd.concat([faq_df, new_entry], ignore_index=True)
                        save_faq(faq_df)
                        st.success("Pertanyaan dan jawaban berhasil ditambahkan ke FAQ!")
                        # Bersihkan input fields
                        new_question = ""
                    else:
                        st.error("Pertanyaan ini sudah pernah diajukan sebelumnya")
                else:
                    st.error("Pertanyaan dan jawaban tidak boleh kosong.")
        
        with st.sidebar.expander("FAQ Log"):
            if st.button("Tampilkan FAQ Log",key="tampil_faq_log_button"):
                if not faq_df.empty:
                    logs = load_faq()
                    st.dataframe(logs)
                else:
                    st.write("Tidak ada data FAQ.")
                    
            # if not faq_df.empty:
            #     st.write("Daftar FAQ Log:")
                
            #     # Tambahkan kolom "Hapus" ke DataFrame
            #     # faq_df["Hapus"] = "❌"
                
            #     # Konfigurasi AgGrid
            #     gb = GridOptionsBuilder.from_dataframe(faq_df)
            #     gb.configure_column("Hapus", header_name="Hapus", width=50, cellRenderer="DeleteButton")
            #     gb.configure_selection("single", use_checkbox=False)
            #     gb.configure_grid_options(enableRangeSelection=True, rowSelection="single")
            #     grid_options = gb.build()
                
            #     # Tampilkan AgGrid
            #     grid_response = AgGrid(
            #         faq_df,
            #         gridOptions=grid_options,
            #         update_mode=GridUpdateMode.SELECTION_CHANGED,
            #         data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            #         columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
            #         theme="streamlit"
            #     )
                
            #     # Tangani aksi hapus
            #     # if grid_response["selected_rows"]:
            #     #     selected_row = grid_response["selected_rows"][0]
            #     #     if selected_row["Hapus"] == "❌":
            #     #         faq_df = faq_df[faq_df["question"] != selected_row["question"]]
            #     #         save_faq(faq_df)
            #     #         st.success(f"Pertanyaan '{selected_row['question']}' berhasil dihapus!")
            #     #         st.experimental_rerun()  # Refresh tampilan
            

        with st.sidebar.expander("Pertanyaan dari User"):
            user_questions_df = load_user_questions()
            if not user_questions_df.empty:
                st.write("Pertanyaan yang diajukan user:")
                st.dataframe(user_questions_df)
                selected_question = st.selectbox("Pilih Pertanyaan untuk Ditambahkan ke FAQ", user_questions_df["question"])
                new_answer = st.text_input("Masukkan Jawaban untuk Pertanyaan Terpilih")
                if st.button("Tambahkan ke FAQ",key="tambah_faq_user"):
                    if new_answer.strip():
                        faq_df = load_faq()
                        new_entry = pd.DataFrame({"question": [selected_question], "answer": [new_answer]})
                        faq_df = pd.concat([faq_df, new_entry], ignore_index=True)
                        save_faq(faq_df)
                        user_questions_df = user_questions_df[user_questions_df["question"] != selected_question]
                        save_user_questions(user_questions_df)
                        st.success("Pertanyaan dan jawaban berhasil ditambahkan ke FAQ!")
                    else:
                        st.error("Jawaban tidak boleh kosong.")
            else:
                st.write("Tidak ada pertanyaan dari user.")

        with st.sidebar.expander("Audit Log"):
            if st.button("Tampilkan Log",key="tampil_log_button"):
                logs = load_logs()
                st.dataframe(logs)

        # Fitur login admin di sidebar
    if not st.session_state.logged_in:
        admin_login()
    else:
        tombol_logout = st.sidebar.button("Logout")
        if tombol_logout:
            logout()

if __name__ == "__main__":
    main()
