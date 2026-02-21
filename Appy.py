1:  import streamlit as st
2:  from google import genai
3:  from google.genai import types
4:  from PyPDF2 import PdfReader
5:  import re
6:  import time
7:  import streamlit.components.v1 as components
8:  
9:  st.set_page_config(page_title="N5 Voice Sensei", page_icon="🎤")
10: st.title("🎤 N5 Japanese Voice Tutor")
11: 
12: # --- Initialization ---
13: if 'api_key' not in st.session_state: st.session_state.api_key = ""
14: if 'current_question' not in st.session_state: st.session_state.current_question = ""
15: if 'feedback' not in st.session_state: st.session_state.feedback = ""
16: 
17: with st.sidebar:
18:     st.header("Setup")
19:     st.session_state.api_key = st.text_input("Enter API Key:", value=st.session_state.api_key, type="password")
20:     uploaded_file = st.file_uploader("Upload N5 PDF", type="pdf")
21: 
22: @st.cache_data
23: def get_pdf_text(file_buffer):
24:     try:
25:         reader = PdfReader(file_buffer)
26:         # Extracting first 5 pages to stay within token limits and avoid messy data
27:         raw_text = "".join([p.extract_text() for p in reader.pages[:5]])
28:         # Clean up whitespace and non-printable characters common in PDFs
29:         clean_text = re.sub(r'\s+', ' ', raw_text)
30:         return clean_text
31:     except Exception:
32:         return ""
33: 
34: def play_audio(client, text, slow=True):
35:     """Uses Browser Speech Synthesis for unlimited, reliable Japanese audio."""
36:     rate = 0.6 if slow else 1.0
37:     # Escaping single quotes for JavaScript safety
38:     safe_text = text.replace("'", "\\'")
39:     js_code = f"""
40:     <script>
41:     var msg =
