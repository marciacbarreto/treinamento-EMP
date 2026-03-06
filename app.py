import streamlit as st
import io
import hashlib
from openai import OpenAI
from audio_recorder_streamlit import audio_recorder
import PyPDF2
import docx

st.set_page_config(page_title="Treinamento EMP", layout="wide")

# -------------------------
# ESTADO DA SESSÃO
# -------------------------

defaults = {
    "transcricao": "",
    "resposta": "",
    "cv_text": "",
    "last_audio_hash": ""
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# -------------------------
# OPENAI
# -------------------------

def get_client():
    api_key = st.secrets.get("OPENAI_API_KEY", "")
    return OpenAI(api_key=api_key)

# -------------------------
# EXTRAIR TEXTO DO CV
# -------------------------

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

# -------------------------
# INTERFACE
# -------------------------

st.title("Treinamento EMP")

# 1️⃣ EMPRESA
empresa = st.text_input("Empresa")

# 2️⃣ DESCRIÇÃO DA VAGA + CURRÍCULO

col1, col2 = st.columns(2)

with col1:

    vaga = st.text_area(
        "Descrição da vaga",
        height=200
    )

with col2:

    uploaded_cv = st.file_uploader(
        "Currículo",
        type=["pdf","docx","txt"]
    )

    if uploaded_cv:
        st.session_state.cv_text = extrair_texto_cv(uploaded_cv)
        st.success("Currículo carregado")

# 3️⃣ FERRAMENTAS

st.subheader("Ferramentas que a empresa trabalha (Explicação)")

st.info("""
Jira (gestão de backlog e tarefas ágeis) /
Confluence (documentação e governança de processos) /
Miro (mapas colaborativos e desenho de jornadas) /
Google Analytics (análise de comportamento no e-commerce) /
Power BI (monitoramento de indicadores e dashboards) /
Adobe Experience Manager (gestão de conteúdo digital) /
Slack (comunicação entre áreas) /
ChatGPT (IA para análise e otimização de processos)
""")

# 4️⃣ BOTÕES

colb1, colb2, colb3 = st.columns(3)

with colb1:
    iniciar = st.button("Iniciar")

with colb2:
    atualizar = st.button("Atualizar")

with colb3:
    encerrar = st.button("Encerrar")

st.divider()

# 5️⃣ MICROFONE

st.subheader("🎤 Microfone / Áudio")

audio = audio_recorder(text="Click to record")

# -------------------------
# PROCESSAR ÁUDIO
# -------------------------

if audio:

    audio_hash = hashlib.sha1(audio).hexdigest()

    if audio_hash != st.session_state.last_audio_hash:

        st.session_state.last_audio_hash = audio_hash

        client = get_client()

        with st.spinner("Transcrevendo pergunta..."):

            audio_file = io.BytesIO(audio)
            audio_file.name = "audio.wav"

            transcricao = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )

            st.session_state.transcricao = transcricao.text

        with st.spinner("Gerando resposta estratégica..."):

            resposta = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[

                    {
                        "role": "system",
                        "content": f"""
Você é um candidato ideal.

Use as informações abaixo para responder.

Empresa:
{empresa}

Descrição da vaga:
{vaga}

Currículo:
{st.session_state.cv_text}

A resposta deve demonstrar:

- gestão de projetos
- análise de dados e indicadores
- melhoria contínua
- uso de tecnologia e IA
- integração entre áreas
"""
                    },

                    {
                        "role": "user",
                        "content": st.session_state.transcricao
                    }
                ]
            )

            st.session_state.resposta = resposta.choices[0].message.content

# 6️⃣ CAMPO TRANSCRIÇÃO

st.subheader("Transcrição da pergunta")

st.text_area(
    "Pergunta detectada",
    value=st.session_state.transcricao,
    height=100
)

# 7️⃣ CAMPO RESPOSTA

st.subheader("Resposta estratégica")

st.text_area(
    "Resposta baseada na vaga, currículo e pergunta",
    value=st.session_state.resposta,
    height=250
)
