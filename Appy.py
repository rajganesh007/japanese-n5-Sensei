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
                if part.inline_data:
                    st.audio(part.inline_data.data, format="audio/wav", autoplay=True)
                    return
        st.warning("Sensei is silent for a moment. Try again.")
    except Exception as e:
        st.error(f"Voice Error: {str(e)}")

if st.session_state.api_key and uploaded_file:
    # UPDATE #1: Initializing with v1beta
    client = genai.Client(
        api_key=st.session_state.api_key,
        http_options={'api_version': 'v1beta'}
    )
    
    vocab_text = get_pdf_text(uploaded_file)

    if st.button("Sensei, ask me a question!"):
        with st.spinner("Thinking..."):
            txt_prompt = f"Using {vocab_text[:1000]}, ask a short N5 Japanese question. Format: Japanese, Romaji, English."
            response = client.models.generate_content(model='gemini-2.5-flash', contents=txt_prompt)
            st.session_state.current_question = response.text
            st.rerun()

    if st.session_state.current_question:
        st.info(st.session_state.current_question)
        if st.button("🔈 Hear Question"):
            # Grab just the Japanese part
            jap_line = st.session_state.current_question.split('\n')[0].replace('Japanese:', '').strip()
            play_audio(client, jap_line, slow=True)

    st.divider()
    st.subheader("Your Answer")
    student_audio = st.audio_input("Record response", key="mic")

    if student_audio is not None:
        with st.spinner("Analyzing..."):
            try:
                feedback_res = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        f"Question: {st.session_state.current_question}. Correct the student's Japanese.",
                        types.Part.from_bytes(data=student_audio.read(), mime_type="audio/wav")
                    ]
                )
                st.success("Feedback:")
                st.write(feedback_res.text)
                
                # Feedback Audio
                first_sent = re.split(r'[.!?！？]', feedback_res.text)[0]
                play_audio(client, first_sent, slow=False)
            except Exception as e:
                st.error(f"Error: {e}")
else:
    st.info("Awaiting API Key and PDF.")
