import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

st.set_page_config(page_title="N5 Voice Coach", page_icon="🎤")
st.title("🎤 N5 Japanese Voice Tutor")

with st.sidebar:
    st.header("Setup")
    api_key = st.text_input("Enter Google Gemini API Key:", type="password")
    uploaded_file = st.file_uploader("Upload your N5 Vocab PDF", type="pdf")

def get_pdf_text(pdf_file):
    reader = PdfReader(pdf_file)
    return "".join([page.extract_text() for page in reader.pages])

if api_key and uploaded_file:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    vocab_context = get_pdf_text(uploaded_file)

    # THIS ADDS THE MICROPHONE
    audio_value = st.audio_input("Record your Japanese sentence")

    if audio_value:
        st.audio(audio_value)
        with st.spinner("Sensei is listening..."):
            # System prompt for voice correction
            prompt = f"Using this vocab: {vocab_context}. Listen to the audio, transcribe it, correct any N5 grammar errors in English, then reply in N5 Japanese."
            response = model.generate_content([prompt, {"mime_type": "audio/wav", "data": audio_value.read()}])
            st.markdown(response.text)
else:
    st.info("Please enter your API Key and upload your PDF in the sidebar.")
