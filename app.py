import os
import io
import streamlit as st
import requests
from openai import OpenAI

# ================== CONFIGURAÇÃO BÁSICA ==================
st.set_page_config(page_title="Treinamento EMP", layout="centered")
st.title("Treinamento EMP")

# ================== CONTROLE DE SESSÃO ==================
if "logged" not in st.session_state:
    st.session_state.logged = False
if "running" not in st.session_state:
    st.session_state.running = False
if "curriculo" not in st.session_state:
    st.session_state.curriculo = ""
if "vaga" not in st.session_state:
    st.session_state.vaga = ""
if "transcricao" not in st.session_state:
    st.session_state.transcricao = ""

# ================== LOGIN SIMPLES ==================
if not st.session_state.logged:
    st.subheader("Login")
    user = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if user and password:
            st.session_state.logged = True
            st.rerun()
        else:
            st.warning("Informe usuário e senha.")
    st.stop()

# ================== FUNÇÕES ==================
def read_pdf(file_bytes: bytes) -> str:
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        return "\n".join((p.extract_text() or "") for p in reader.pages).strip()
    except Exception:
        return ""

def read_docx(file_bytes: bytes) -> str:
    try:
        import docx
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs).strip()
    except Exception:
        return ""

def extract_text(uploaded_file) -> str:
    if not uploaded_file:
        return ""
    data = uploaded_file.read()
    name = (uploaded_file.name or "").lower()
    if name.endswith(".pdf"):
        return read_pdf(data)
    if name.endswith(".docx"):
        return read_docx(data)
    try:
        return data.decode("utf-8", errors="ignore").strip()
    except Exception:
        return ""

def google_search(empresa: str) -> str:
    key = os.getenv("GOOGLE_CSE_API_KEY")
    cx = os.getenv("GOOGLE_CSE_CX")
    if not key or not cx:
        return "Sem dados de mercado disponíveis."
    params = {
        "key": key,
        "cx": cx,
        "q": f"{empresa} requisitos vaga competências mercado",
        "num": 5,
    }
    r = requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=15)
    data = r.json()
    textos = []
    for item in data.get("items", []):
        textos.append(item.get("snippet", ""))
    return "\n".join(textos)

def gerar_resposta(curriculo, vaga, empresa, pergunta):
    client = OpenAI()
    contexto_google = google_search(empresa)

    prompt_dev = (
        "Você é um treinador de entrevista.\n"
        "Use apenas currículo, vaga e contexto real de mercado.\n"
        "Não invente informações.\n"
        "Responda rápido.\n"
        "Limite: até 8 linhas; se for case, até 10 linhas."
    )

    prompt_user = f"""
CURRÍCULO:
{curriculo}

VAGA:
{vaga}

MERCADO (Google):
{contexto_google}

PERGUNTA DO RECRUTADOR:
{pergunta}

Responda como candidato.
"""

    resp = client.responses.create(
        model="gpt-5.2",
        input=[
            {"role": "developer", "content": prompt_dev},
            {"role": "user", "content": prompt_user},
        ],
        reasoning={"effort": "low"},
    )
    return resp.output_text.strip()

# ================== INTERFACE PRINCIPAL ==================
st.subheader("Sessão de Treinamento")

col1, col2 = st.columns(2)
with col1:
    if st.button("Iniciar"):
        st.session_state.running = True
with col2:
    if st.button("Encerrar"):
        st.session_state.running = False
        st.session_state.curriculo = ""
        st.session_state.vaga = ""
        st.session_state.transcricao = ""
        st.success("Sessão encerrada.")

if not st.session_state.running:
    st.stop()

empresa = st.text_input("Empresa")

curr_file = st.file_uploader("Anexar currículo", type=["pdf", "docx", "txt"])
vaga_text = st.text_area("Descrição da vaga")

if st.button("Carregar dados"):
    st.session_state.curriculo = extract_text(curr_file)
    st.session_state.vaga = vaga_text.strip()

if not st.session_state.curriculo or not st.session_state.vaga or not empresa:
    st.info("Informe empresa, currículo e vaga.")
    st.stop()

audio_file = st.file_uploader("Pergunta em áudio (mp3/wav/m4a)", type=["mp3", "wav", "m4a"])

if st.button("Transcrever pergunta"):
    client = OpenAI()
    tr = client.audio.transcriptions.create(
        model="gpt-4o-mini-transcribe",
        file=(audio_file.name, audio_file.read()),
    )
    st.session_state.transcricao = tr.text

if st.session_state.transcricao:
    st.markdown("**Pergunta transcrita:**")
    st.write(st.session_state.transcricao)

if st.button("Gerar resposta"):
    resposta = gerar_resposta(
        st.session_state.curriculo,
        st.session_state.vaga,
        empresa,
        st.session_state.transcricao,
    )
    st.markdown("### Resposta")
    st.write(resposta)
