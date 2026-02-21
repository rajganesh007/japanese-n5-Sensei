import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

st.set_page_config(page_title="N5 Voice Coach", page_icon="🎤")
st.title("🎤 N5 Japanese Voice Tutor")

# Sidebar for Setup
with st.sidebar:
    st.header("Setup")
    # This stores the key for the current session
    if 'key' not in st.session_state:
        st.session_state.key = ""
    
    api_key = st.text_input("Enter Gemini API Key:", value=st.session_state.key, type="password")
    if api_key:
        st.session_state.key = api_key
        
    uploaded_file = st.file_uploader("Upload N5 PDF", type="pdf")

@st.cache_data
def get_pdf_text(file_buffer):
    reader = PdfReader(file_buffer)
    text = ""
    for i in range(min(15, len(reader.pages))): # Keep it light for speed
        text += reader.pages[i].extract_text()
    return text

if st.session_state.key and uploaded_file:
    # Use the stable v1 API (v1beta is deprecated)
    genai.configure(api_key=st.session_state.key)
    
    # UPDATE: Using the 2026 stable model
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    with st.spinner("Sensei is reading..."):
        vocab_text = get_pdf_text(uploaded_file)
    
    st.subheader("Talk to Sensei")
    audio_value = st.audio_input("Record your Japanese")

    if audio_value:
        with st.spinner("Analyzing voice..."):
            try:
                audio_data = audio_value.read()
                audio_part = {"mime_type": "audio/wav", "data": audio_data}
                
                prompt = f"Context: {vocab_text[:5000]}. Transcribe the audio, correct any N5 errors, and reply in Japanese."
                
                response = model.generate_content([prompt, audio_part])
                st.success("Sensei says:")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Error: {str(e)}. Try a shorter recording.")
else:
    st.info("Please enter your API Key and upload your PDF in the sidebar.")
