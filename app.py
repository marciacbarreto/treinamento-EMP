import streamlit as st
import io
import hashlib
import time
from openai import OpenAI
from audio_recorder_streamlit import audio_recorder
import PyPDF2
import docx

# ------------------------------
# CONFIGURAÇÃO
# ------------------------------
st.set_page_config(page_title="Treinamento EMP PRO", layout="wide")

# ------------------------------
# ESTADO
# ------------------------------
defaults = {
    "transcricao": "",
    "resposta": "",
    "cv_text": "",
    "last_audio_hash": "",
    "buffer": "",
    "last_update": time.time(),
    "history": [],
    "resposta_parcial": ""
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ------------------------------
# OPENAI
# ------------------------------
def get_client():
    api_key = st.secrets.get("OPENAI_API_KEY", "")
    return OpenAI(api_key=api_key)

client = get_client()

# ------------------------------
# CV
# ------------------------------
def extrair_texto_cv(uploaded_file):
    if uploaded_file is None:
        return ""

    name = uploaded_file.name.lower()

    if name.endswith(".pdf"):
        pdf = PyPDF2.PdfReader(uploaded_file)
        return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])

    elif name.endswith(".docx"):
        doc = docx.Document(uploaded_file)
        return "\n".join([p.text for p in doc.paragraphs])

    else:
        return uploaded_file.read().decode("utf-8", errors="ignore")

# ------------------------------
# UI
# ------------------------------
st.title("Treinamento EMP PRO (Tempo Real)")

empresa = st.text_input("Empresa")
vaga = st.text_area("Descrição da vaga")

uploaded_cv = st.file_uploader("Currículo", type=["pdf","docx","txt"])

if uploaded_cv:
    st.session_state.cv_text = extrair_texto_cv(uploaded_cv)

# ------------------------------
# PREDIÇÃO
# ------------------------------
def prever_intencao(texto):
    texto = texto.lower()

    if "tell me about" in texto:
        return "behavioral"
    if "how" in texto:
        return "situational"
    if "why" in texto:
        return "reasoning"

    return "general"

# ------------------------------
# PROMPT DINÂMICO
# ------------------------------
def build_prompt(pergunta):
    return f"""
Você está em uma entrevista.

Pergunta:
{pergunta}

Empresa:
{empresa}

Vaga:
{vaga}

Currículo:
{st.session_state.cv_text}

Responda:
- Natural
- Curto
- Como humano
- Sem parecer IA
"""

# ------------------------------
# RESPOSTA
# ------------------------------
def gerar_resposta(pergunta):
    prompt = build_prompt(pergunta)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=120
    )

    return response.choices[0].message.content

# ------------------------------
# UI DE RESPOSTA DINÂMICA
# ------------------------------
placeholder_resposta = st.empty()

# ------------------------------
# ÁUDIO
# ------------------------------
audio = audio_recorder(text="Gravar pergunta")

if audio:
    audio_hash = hashlib.sha1(audio).hexdigest()

    if audio_hash != st.session_state.last_audio_hash:

        st.session_state.last_audio_hash = audio_hash

        audio_file = io.BytesIO(audio)
        audio_file.name = "audio.wav"

        transcricao = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )

        texto = transcricao.text

        # ------------------------------
        # BUFFER DE FRAGMENTOS
        # ------------------------------
        st.session_state.buffer += " " + texto
        st.session_state.last_update = time.time()

        buffer_texto = st.session_state.buffer.strip()

        st.subheader("🧠 Pergunta em construção")
        st.write(buffer_texto)

        # ------------------------------
        # RESPOSTA ANTECIPADA
        # ------------------------------
        if len(buffer_texto.split()) > 4:

            resposta_parcial = gerar_resposta(buffer_texto)

            st.session_state.resposta_parcial = resposta_parcial

            placeholder_resposta.markdown(
                f"💬 **Resposta em tempo real:**\n\n{resposta_parcial}"
            )

# ------------------------------
# FINALIZAÇÃO (SIMULA VAD)
# ------------------------------
tempo_parado = time.time() - st.session_state.last_update

if st.session_state.buffer and tempo_parado > 2:

    pergunta_final = st.session_state.buffer.strip()

    st.subheader("✅ Pergunta final detectada")
    st.write(pergunta_final)

    resposta_final = gerar_resposta(pergunta_final)

    st.session_state.resposta = resposta_final

    placeholder_resposta.markdown(
        f"🎯 **Resposta final:**\n\n{resposta_final}"
    )

    # ------------------------------
    # HISTÓRICO
    # ------------------------------
    st.session_state.history.append({
        "pergunta": pergunta_final,
        "resposta": resposta_final
    })

    # Reset
    st.session_state.buffer = ""
