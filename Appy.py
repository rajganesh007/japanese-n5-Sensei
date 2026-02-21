import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

st.set_page_config(page_title="N5 Voice Coach", page_icon="🎤")
st.title("🎤 N5 Japanese Voice Tutor")

with st.sidebar:
    st.header("Setup")
    api_key = st.text_input("Enter Google Gemini API Key:", type="password")
    uploaded_file = st.file_uploader("Upload your 55MB PDF", type="pdf")

# This "Cache" function is the key for large files
@st.cache_data
def get_pdf_text(file_buffer):
    reader = PdfReader(file_buffer)
    full_text = ""
    # We loop through and extract text (55MB may take 10-15 seconds)
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text += text
    return full_text

if api_key and uploaded_file:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # The app will show a spinner only the VERY FIRST time you upload
    with st.spinner("Processing large PDF... Please wait a moment."):
        vocab_text = get_pdf_text(uploaded_file)
    
    st.success("File Loaded! You can now talk.")

    # Microphone Section
    audio_value = st.audio_input("Record your Japanese")

    if audio_value:
        with st.spinner("Sensei is thinking..."):
            # We only send the first 15,000 characters to keep it fast
            context = vocab_text[:15000] 
            instruction = f"You are an N5 Sensei. Use this vocab context: {context}. Transcribe the user's voice, correct grammar, and reply in N5 Japanese."
            
            response = model.generate_content([instruction, {"mime_type": "audio/wav", "data": audio_value.read()}])
            st.markdown(response.text)
else:
    st.info("Please enter your API Key and upload your 55MB PDF in the sidebar.")
