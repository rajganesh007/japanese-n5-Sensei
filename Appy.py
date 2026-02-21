import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

st.set_page_config(page_title="N5 Voice Coach", page_icon="🎤")
st.title("🎤 N5 Japanese Voice Tutor")

with st.sidebar:
    st.header("Setup")
    api_key = st.text_input("Enter Google Gemini API Key:", type="password")
    uploaded_file = st.file_uploader("Upload N5 PDF", type="pdf")

@st.cache_data
def get_pdf_text(file_buffer):
    reader = PdfReader(file_buffer)
    # We only take the first 20 pages to prevent server timeouts
    text = ""
    for i in range(min(20, len(reader.pages))):
        text += reader.pages[i].extract_text()
    return text

if api_key and uploaded_file:
    genai.configure(api_key=api_key)
    # Using 'gemini-1.5-flash' because it is much faster for audio
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    with st.spinner("Preparing sensei..."):
        vocab_text = get_pdf_text(uploaded_file)
    
    st.subheader("Talk to Sensei")
    audio_value = st.audio_input("Record your Japanese")

    if audio_value:
        with st.spinner("Sensei is analyzing your voice..."):
            try:
                # Prepare the audio part correctly
                audio_data = audio_value.read()
                audio_part = {"mime_type": "audio/wav", "data": audio_data}
                
                # Simple prompt to avoid '400' errors
                prompt = f"Context: {vocab_text[:5000]}. Transcribe this audio, correct any N5 errors, and reply in Japanese."
                
                response = model.generate_content([prompt, audio_part])
                st.success("Sensei says:")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Server Busy: Please try speaking a bit more clearly or shorter. Error: {str(e)}")
else:
    st.info("Awaiting API Key and PDF upload.")
