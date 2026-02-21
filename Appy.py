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
    """Reliable TTS using the beta modality-switch."""
    try:
        pace = "very slowly" if slow else "at a natural pace"
        # 2026 Fix: We request BOTH text and audio to prevent a 400 error 
        # when the model generates its 'thoughts' as text first.
        audio_res = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=f"Say this {pace} in Japanese: {text}",
            config=types.GenerateContentConfig(
                response_modalities=['TEXT', 'AUDIO'] 
            )
        )
        
        if audio_res.candidates:
            for part in audio_res.candidates[0].content.parts:
                if part.inline_data:
                    st.audio(part.inline_data.data, format="audio/wav", autoplay=True)
                    return
        st.warning("Voice is currently unavailable. Displaying text instead.")
    except Exception as e:
        st.error(f"Voice Error (Likely Region/Quota): {str(e)}")

if st.session_state.api_key and uploaded_file:
    # 2026 Setup: Simplified client. The SDK defaults to v1beta 
    # for gemini-2.5 models if version is not specified.
    client = genai.Client(api_key=st.session_state.api_key)
    
    vocab_text = get_pdf_text(uploaded_file)

    if st.button("Sensei, ask me a question!"):
        with st.spinner("Sensei is writing..."):
            try:
                txt_prompt = f"Using {vocab_text[:1000]}, ask a short N5 Japanese question. Format: Japanese, Romaji, English."
                response = client.models.generate_content(
                    model='gemini-2.5-flash', 
                    contents=txt_prompt
                )
                st.session_state.current_question = response.text
                st.rerun()
            except Exception as e:
                st.error(f"Text Error: {e}")

    if st.session_state.current_question:
        st.info(st.session_state.current_question)
        if st.button("🔈 Hear Question"):
            # Improved regex to grab the Japanese text more safely
            match = re.search(r"Japanese:\s*(.*)", st.session_state.current_question)
            jap_line = match.group(1) if match else st.session_state.current_question.split('\n')[0]
            play_audio(client, jap_line, slow=True)

    st.divider()
    st.subheader("Your Answer")
    student_audio = st.audio_input("Record response", key="mic")

    if student_audio is not None:
        with st.spinner("Sensei is listening..."):
            try:
                # Direct multimodal upload
                feedback_res = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        f"Question: {st.session_state.current_question}. Correct the student's Japanese pronunciation and grammar.",
                        types.Part.from_bytes(data=student_audio.read(), mime_type="audio/wav")
                    ]
                )
                st.success("Sensei's Feedback:")
                st.write(feedback_res.text)
                
                # Feedback Audio (First sentence only)
                sentences = re.split(r'[.!?！？]', feedback_res.text)
                if sentences:
                    play_audio(client, sentences[0], slow=False)
            except Exception as e:
                st.error(f"Analysis Error: {e}")
else:
    st.info("Please enter your API Key and upload an N5 PDF to begin.")
