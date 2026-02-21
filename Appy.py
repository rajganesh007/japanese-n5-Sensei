import streamlit as st
from google import genai
from google.api_core import exceptions
from google.genai import types
from PyPDF2 import PdfReader
import re
import time
import io

st.set_page_config(page_title="N5 Voice Sensei", page_icon="🎤")
st.title("🎤 N5 Japanese Voice Tutor")

# --- Initialization ---
if 'api_key' not in st.session_state: st.session_state.api_key = ""
if 'current_question' not in st.session_state: st.session_state.current_question = ""
if 'feedback' not in st.session_state: st.session_state.feedback = ""

with st.sidebar:
    st.header("Setup")
    st.session_state.api_key = st.text_input("Enter API Key:", value=st.session_state.api_key, type="password")
    uploaded_file = st.file_uploader("Upload N5 PDF", type="pdf")

@st.cache_data
def get_pdf_text(file_buffer):
    try:
        reader = PdfReader(file_buffer)
        # Japanese text often needs a cleaner join to avoid broken kanji
        text = " ".join([p.extract_text() for p in reader.pages[:5]])
        return re.sub(r'\s+', ' ', text) # Remove excessive whitespace/newlines
    except Exception as e:
        return f"Error reading PDF: {e}"

import streamlit.components.v1 as components

def play_audio(client, text, slow=True):
    """Hybrid TTS: Gemini Flash 2.5 (if supported) -> Browser Fallback."""
    try:
        # Note: AUDIO output in generate_content requires specific model support 
        # For 2026, we ensure the prompt asks for speech synthesis specifically
        audio_res = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=f"Read this Japanese text clearly: {text}",
            config=types.GenerateContentConfig(response_modalities=['AUDIO'])
        )
        if audio_res.candidates and audio_res.candidates[0].content.parts[0].inline_data:
            st.audio(audio_res.candidates[0].content.parts[0].inline_data.data, format="audio/wav")
            return
            
    except Exception:
        # Fallback: JavaScript Browser Speech (Very reliable for Japanese)
        rate = 0.7 if slow else 1.0
        js_code = f"""
        <script>
        var msg = new SpeechSynthesisUtterance({repr(text)});
        msg.lang = 'ja-JP';
        msg.rate = {rate};
        window.speechSynthesis.speak(msg);
        </script>
        """
        components.html(js_code, height=0)

# --- Main App Logic ---
if st.session_state.api_key and uploaded_file:
    client = genai.Client(api_key=st.session_state.api_key)
    vocab_context = get_pdf_text(uploaded_file)

    if st.button("Sensei, ask me a question!"):
        with st.spinner("Sensei is thinking..."):
            # Stronger prompt to ensure the regex works later
            txt_prompt = f"""
            Context: {vocab_context[:1500]}
            Task: Ask a simple N5 Japanese question based on the context.
            Format your response exactly like this:
            Japanese: [Japanese Text]
            Romaji: [Romaji Text]
            English: [English Translation]
            """
            response = client.models.generate_content(
                model='gemini-2.5-flash-lite', 
                contents=txt_prompt
            )
            st.session_state.current_question = response.text
            st.session_state.feedback = "" # Clear old feedback
            st.rerun()

    if st.session_state.current_question:
        st.markdown("### 📖 Current Question")
        st.info(st.session_state.current_question)
        
        if st.button("🔈 Hear Question"):
            # Improved extraction logic
            jap_match = re.search(r"Japanese:\s*(.*)", st.session_state.current_question)
            text_to_speak = jap_match.group(1) if jap_match else st.session_state.current_question
            play_audio(client, text_to_speak)

        st.divider()
        st.subheader("Your Answer")
        # Ensure student_audio is captured correctly
        student_audio = st.audio_input("Record your Japanese response")

        if student_audio:
            if st.button("Submit Answer"):
                with st.spinner("Sensei is checking your pronunciation..."):
                    audio_bytes = student_audio.read()
                    
                    analysis_prompt = f"""
                    The student is answering the question: {st.session_state.current_question}
                    1. Transcribe their Japanese.
                    2. Evaluate their grammar and pronunciation.
                    3. Provide a response in: Japanese, Romaji, and English.
                    """
                    
                    try:
                        feedback_res = client.models.generate_content(
                            model='gemini-2.5-flash-lite', 
                            contents=[
                                analysis_prompt,
                                types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav")
                            ]
                        )
                        st.session_state.feedback = feedback_res.text
                    except Exception as e:
                        st.error(f"Sensei couldn't hear you clearly: {e}")

    if st.session_state.feedback:
        st.success("Sensei's Feedback:")
        st.write(st.session_state.feedback)
        if st.button("🔈 Hear Feedback"):
            # Speak only the first sentence of the feedback
            fb_match = re.search(r"Japanese:\s*(.*)", st.session_state.feedback)
            fb_text = fb_match.group(1) if fb_match else st.session_state.feedback.split('\n')[0]
            play_audio(client, fb_text, slow=False)
