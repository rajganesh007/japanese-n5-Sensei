import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

# Page setup
st.set_page_config(page_title="N5 Voice Coach", page_icon="🎤")
st.title("🎤 N5 Japanese Voice Tutor")

# Sidebar
with st.sidebar:
    st.header("Setup")
    api_key = st.text_input("Enter Google Gemini API Key:", type="password")
    uploaded_file = st.file_uploader("Upload your N5 Vocab PDF", type="pdf")

# PDF Reader Function
def get_pdf_text(pdf_file):
    reader = PdfReader(pdf_file)
    return "".join([page.extract_text() for page in reader.pages])

# Main Logic
if api_key and uploaded_file:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # This reads your uploaded Minna No Nihongo PDF
    with st.spinner("Sensei is reading your vocabulary..."):
        vocab_context = get_pdf_text(uploaded_file)

    # THE VOICE WIDGET
    st.subheader("Talk to Sensei")
    audio_value = st.audio_input("Click the mic, speak Japanese, then click stop.")

    if audio_value:
        with st.spinner("Sensei is listening..."):
            # Instructions for the AI
            instruction = f"""
            You are an N5 Japanese Sensei. 
            REFERENCE VOCAB: {vocab_context}
            TASK: 
            1. Transcribe what the user said.
            2. Correct any grammar mistakes in English.
            3. Reply in simple N5 Japanese (Kanji + Furigana + English).
            """
            response = model.generate_content([instruction, {"mime_type": "audio/wav", "data": audio_value.read()}])
            st.info("Sensei's Feedback:")
            st.markdown(response.text)
else:
    st.info("Please enter your API Key and upload your N5 PDF in the sidebar to start.")
