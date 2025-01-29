import streamlit as st
import pandas as pd
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Cek apakah file dataset sudah ada
file_path = "faq_data.csv"

# File untuk menyimpan pertanyaan yang menunggu moderasi
pending_file = "pending_data.csv"

# Membuat file CSV jika belum ada
if not os.path.exists(file_path):
    pd.DataFrame(columns=["question", "answer"]).to_csv(file_path, index=False)

if not os.path.exists(pending_file):
    pd.DataFrame(columns=["question", "answer"]).to_csv(pending_file, index=False)

# Memuat dataset utama dan daftar pending
faq_data = pd.read_csv(file_path)
pending_data = pd.read_csv(pending_file)



# Fungsi untuk memproses input pengguna dan mencari jawaban menggunakan TF-IDF
def chatbot_response(user_input):
    if faq_data.empty:
        return "Saya belum memiliki data jawaban. Anda bisa menambahkan jawaban baru."
    
    # Membuat TF-IDF vectorizer
    vectorizer = TfidfVectorizer()

    # Menggabungkan pertanyaan dari dataset dan input pengguna menjadi satu set
    questions = faq_data['question'].tolist() + [user_input]

    # Mengubah teks menjadi vektor TF-IDF
    tfidf_matrix = vectorizer.fit_transform(questions)

    # Menghitung kemiripan kosinus antara input pengguna dan pertanyaan di dataset
    cosine_similarities = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1])

    # Menemukan indeks pertanyaan dengan kemiripan tertinggi
    best_match_idx = cosine_similarities.argmax()
    highest_similarity = cosine_similarities[0, best_match_idx]

    # Jika tingkat kemiripan di bawah ambang batas, anggap pertanyaan belum ada
    threshold = 0.3
    if highest_similarity < threshold:
        return None  # Menandakan pertanyaan belum ada dalam dataset

    # Mendapatkan respons dari chatbot berdasarkan kecocokan terbaik
    # response = faq_data.iloc[best_match_idx]['answer']
    # return response

    # Kembalikan jawaban dari pertanyaan yang paling mirip
    return faq_data.iloc[best_match_idx]['answer']

# Fungsi menambahkan data ke daftar pending (belum masuk dataset utama)
def add_pending_data(question, answer):
    global pending_data
    new_data = pd.DataFrame([[question, answer]], columns=["question", "answer"])
    pending_data = pd.concat([pending_data, new_data], ignore_index=True)
    pending_data.to_csv(pending_file, index=False)

# Fungsi untuk menyetujui data dan memindahkannya ke dataset utama
def approve_data(index):
    global faq_data, pending_data
    if 0 <= index < len(pending_data):
        approved_entry = pending_data.iloc[index]
        faq_data = pd.concat([faq_data, pd.DataFrame([approved_entry])], ignore_index=True)
        faq_data.to_csv(file_path, index=False)
        pending_data = pending_data.drop(index).reset_index(drop=True)
        pending_data.to_csv(pending_file, index=False)

# Fungsi untuk menolak data (menghapus dari daftar pending)
def reject_data(index):
    global pending_data
    if 0 <= index < len(pending_data):
        pending_data = pending_data.drop(index).reset_index(drop=True)
        pending_data.to_csv(pending_file, index=False)

# Antarmuka Streamlit
st.title("Chatbot dengan Rahmad")
st.write("Masukkan pertanyaan:")

# Menyimpan pesan yang telah dikirim
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Input pengguna
user_input = st.text_input("You: ", "")

if user_input:
    # Simpan pesan pengguna ke dalam session_state
    st.session_state.messages.append(f"You: {user_input}")
    
    # Mendapatkan respons dari chatbot
    response = chatbot_response(user_input)
    if response:
        # Jika jawaban ditemukan, tampilkan jawaban chatbot
        st.session_state.messages.append(f"Chatbot: {response}")
    else:
        # Jika jawaban tidak ditemukan, minta pengguna untuk menambahkan jawaban baru
        st.session_state.messages.append("Chatbot: Saya belum tahu jawabannya. Anda bisa menambahkan jawaban.")
        new_answer = st.text_input("Tambahkan jawaban untuk pertanyaan ini:")

        if new_answer:
            add_pending_data(user_input, new_answer)
            st.session_state.messages.append(f"Chatbot: Jawaban telah dikirim ke admin untuk ditinjau.")
    # st.session_state.messages.append(f"Chatbot: {response}")

# Menampilkan log pesan
for message in st.session_state.messages:
    st.write(message)

# **Fitur Moderasi Admin**
st.subheader("Moderasi Admin - Persetujuan Pertanyaan Baru")
if not pending_data.empty:
    for index, row in pending_data.iterrows():
        st.write(f"**Pertanyaan:** {row['question']}")
        st.write(f"**Jawaban:** {row['answer']}")
        
        col1, col2 = st.columns([0.3, 0.7])
        with col1:
            if st.button(f"✔️ Setujui {index}", key=f"approve_{index}"):
                approve_data(index)
                st.experimental_rerun()
        with col2:
            if st.button(f"❌ Tolak {index}", key=f"reject_{index}"):
                reject_data(index)
                st.experimental_rerun()
else:
    st.write("Tidak ada pertanyaan baru yang menunggu moderasi.")

