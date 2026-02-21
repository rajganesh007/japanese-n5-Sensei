import streamlit as st
from google import genai
from google.genai import types
from PyPDF2 import PdfReader
import re

# 1. Page Configuration
st.set_page_config(page_title="N5 Voice Sensei", page_icon="🎤", layout="centered")
st.title("🎤 N5 Japanese Voice Tutor")

# 2. State Management
if 'api_key' not in st.session_state: st.session_state.api_key = ""
if 'current_question' not in st.session_state: st.session_state.current_question = ""

with st.sidebar:
    st.header("Setup")
    st.session_state.api_key = st.text_input("Enter Gemini API Key:", value=st.session_state.api_key, type="password")
    uploaded_file = st.file_uploader("Upload N5 Vocab PDF", type="pdf")
    st.markdown("---")
    st.info("Ensure `google-genai` is in your `requirements.txt`.")

# 3. Helper Functions
@st.cache_data
def get_pdf_text(file_buffer):
    """Extracts text from the uploaded PDF."""
    reader = PdfReader(file_buffer)
    return "".join([p.extract_text() for p in reader.pages[:10]])

def play_audio(client, text, slow=True):
    """2026 Optimized TTS: Uses the most stable configuration for audio."""
    try:
        # Pacing is handled better via text instructions in the 2.5 models
        pace_instruction = "VERY SLOWLY and clearly" if slow else "at a natural pace"
        
        # We simplify the call to avoid the 'responseModalities' schema error
        # By using the specific TTS model, it knows to return audio.
        audio_res = client.models.generate_content(
            model='gemini-2.5-flash-tts',
            contents=f"Say this {pace_instruction} in Japanese: {text}",
            # We use a simple config to avoid triggering version mismatches
            config=types.GenerateContentConfig(
                temperature=0.1
            )
        )
        
        if audio_res.candidates and audio_res.candidates[0].content.parts:
            for part in audio_res.candidates[0].content.parts:
                if part.inline_data:
                    st.audio(part.inline_data.data, format="audio/wav", autoplay=True)
                    return
        st.warning("Sensei is thinking, but didn't speak. Try again!")
            
    except Exception as e:
        st.error(f"Voice Error: {str(e)}")
# 4. Main Application Logic
if st.session_state.api_key and uploaded_file:
    # Initialize 2026 Client with stable v1 API version
    client = genai.Client(
        api_key=st.session_state.api_key,
        http_options={'api_version': 'v1'}
    )
    
    vocab_text = get_pdf_text(uploaded_file)

    # Question Generation
    if st.button("Sensei, ask me a question!"):
        with st.spinner("Sensei is thinking..."):
            txt_prompt = f"""
            Using this vocab: {vocab_text[:2000]}
            Ask a short N5 Japanese question. 
            Strictly follow this format:
            Japanese: [Text]
            Romaji: [Text]
            English: [Text]
            """
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash', 
                    contents=txt_prompt
                )
                st.session_state.current_question = response.text
                st.rerun()
            except Exception as e:
                st.error(f"Text Error: {str(e)}")

    # Display and Voice for Question
    if st.session_state.current_question:
        st.markdown(f"### Sensei's Question\n{st.session_state.current_question}")
        
        if st.button("🔈 Hear Question (Slowly)"):
            # Extract just the Japanese line for the TTS engine
            lines = st.session_state.current_question.split('\n')
            jap_text = lines[0].replace('Japanese:', '').strip()
            play_audio(client, jap_text, slow=True)

    st.divider()
    st.subheader("Your Answer")
    
    # st.audio_input returns None if empty, and a file-like object if full
    student_audio = st.audio_input("Record your response", key="sensei_mic")

    # Feedback Logic
    if student_audio is not None:
        with st.spinner("Sensei is listening..."):
            try:
                # Convert the recording into a format Gemini understands
                audio_bytes = student_audio.read()
                audio_part = types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav")
                
                feedback_prompt = f"""
                The student is answering this question: {st.session_state.current_question}.
                Analyze their spoken Japanese. Correct errors and provide Romaji for your feedback.
                """
                
                feedback_res = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[feedback_prompt, audio_part]
                )
                
                feedback_text = feedback_res.text
                st.success("Sensei's Feedback:")
                st.write(feedback_text)
                
                # Automatically play the first sentence of feedback
                first_feedback_sentence = re.split(r'[.!?।।！？]', feedback_text)[0]
                play_audio(client, first_sentence=first_feedback_sentence, slow=False)
                
            except Exception as e:
                st.error(f"Analysis failed: {str(e)}")
else:
    st.info("👈 Enter your API Key and upload an N5 PDF in the sidebar to start!")
