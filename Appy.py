import streamlit as st
from google import genai
from google.genai import types
from PyPDF2 import PdfReader
import re

st.set_page_config(page_title="N5 Voice Sensei", page_icon="🎤")
st.title("🎤 N5 Japanese Voice Tutor")

if 'api_key' not in st.session_state: st.session_state.api_key = ""
if 'current_question' not in st.session_state: st.session_state.current_question = ""

with st.sidebar:
    st.header("Setup")
    st.session_state.api_key = st.text_input("Enter API Key:", value=st.session_state.api_key, type="password")
    uploaded_file = st.file_uploader("Upload N5 PDF", type="pdf")

@st.cache_data
def get_pdf_text(file_buffer):
    reader = PdfReader(file_buffer)
    return "".join([p.extract_text() for p in reader.pages[:10]])

def play_audio(client, text, slow=True):
    """Uses the primary Flash model to generate speech via AUDIO modality."""
    try:
        pace = "Speak very slowly" if slow else "Speak naturally"
        # We use the main model name here because it's the most stable
        audio_res = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=f"{pace}: {text}",
            config=types.GenerateContentConfig(
                response_modalities=['AUDIO']
            )
        )
        
        if audio_res.candidates:
            for part in audio_res.candidates[0].content.parts:
                if part.inline
