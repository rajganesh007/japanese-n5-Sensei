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

import streamlit.components.v1 as components

def play_audio(client, text, slow=True):
    """Hybrid TTS: Tries Gemini first, falls back to Browser Voice."""
    try:
        # 1. Attempt Gemini Voice (High Quality)
        audio_res = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=f"Say this very slowly in Japanese: {text}",
            config=types.GenerateContentConfig(response_modalities=['AUDIO'])
        )
        if audio_res.candidates and audio_res.candidates[0].content.parts[0].inline_data:
            st.audio(audio_res.candidates[0].content.parts[0].inline_data.data, format="audio/wav", autoplay=True)
            return
            
    except Exception as e:
        if "429" in str(e):
            st.warning("Sensei is tired! Switching to system voice...")
            # 2. Fallback: Use the browser's built-in Japanese voice (Unlimited Quota)
            js_code = f"""
            <script>
            var msg = new SpeechSynthesisUtterance('{text}');
            msg.lang = 'ja-JP';
            msg.rate = {0.6 if slow else 1.0};
            window.speechSynthesis.speak(msg);
            </script>
            """
            components.html(js_code, height=0)
        else:
            st.error(f"Voice Error: {e}")
if st.session_state.api_key and uploaded_file:
    # 2026 Setup: Simplified client. The SDK defaults to v1beta 
    # for gemini-2.5 models if version is not specified.
    client = genai.Client(api_key=st.session_state.api_key)
    
    vocab_text = get_pdf_text(uploaded_file)

    if st.button("Sensei, ask me a question!"):
        # These lines MUST be indented further than the 'if'
        with st.spinner("Sensei is writing..."):
            try:
                txt_prompt = f"Using {vocab_text[:1000]}, ask a short N5 Japanese question. Format: Japanese, Romaji, English."
                # We use Lite for the text to save your quota
                response = client.models.generate_content(
                    model='gemini-2.5-flash-lite', 
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
                # 2026 PRO-TIP: We use 1.5-flash-8b for audio analysis 
                # because it has a 1,500 RPD limit vs 2.5-flash's 20 RPD.
                def analyze_with_retry(attempts=3):
                    for i in range(attempts):
                        try:
                            return client.models.generate_content(
                                model='gemini-1.5-flash-8b', 
                                contents=[
                                    f"Question: {st.session_state.current_question}. Correct the student's Japanese.",
                                    types.Part.from_bytes(data=student_audio.read(), mime_type="audio/wav")
                                ]
                            )
                        except Exception as e:
                            if "429" in str(e) and i < attempts - 1:
                                time.sleep(8) # Wait for the 7s cooldown
                                continue
                            raise e

                feedback_res = analyze_with_retry()
                st.success("Feedback:")
                st.write(feedback_res.text)
                
                # Feedback Audio (First sentence only)
                sentences = re.split(r'[.!?！？]', feedback_res.text)
                if sentences:
                    play_audio(client, sentences[0], slow=False)
                    
            except Exception as e:
                st.error(f"Analysis Error: {e}")
