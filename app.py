import os
import io
import streamlit as st
import requests
from openai import OpenAI
from audio_recorder_streamlit import audio_recorder

st.set_page_config(page_title="Treinamento EMP", layout="centered")
st.title("Treinamento EMP")

# ========= ESTADO =========
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
if "start_voice" not in st.session_state:
    st.session_state.start_voice = False
if "last_audio_len" not in st.session_state:
    st.session_state.last_audio_len = 0

# ========= LOGIN (SIMPLES) =========
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

# ========= FUNÇÕES =========
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

def google_context(empresa: str) -> str:
    key = os.getenv("GOOGLE_CSE_API_KEY")
    cx = os.getenv("GOOGLE_CSE_CX")
    if not key or not cx:
        return "Sem dados de mercado disponíveis."

    try:
        params = {
            "key": key,
            "cx": cx,
            "q": f"{empresa} requisitos competências perfil da vaga notícias recentes",
            "num": 5,
        }
        r = requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        snippets = [item.get("snippet", "") for item in data.get("items", [])]
        return "\n".join(s for s in snippets if s).strip() or "Sem dados de mercado disponíveis."
    except Exception:
        return "Sem dados de mercado disponíveis."

def is_case_question(text: str) -> bool:
    t = (text or "").lower()
    keys = ["case", "cenário", "situação", "situaçao", "como você faria", "como vc faria", "resolva", "resolveria", "desafio", "problema"]
    return any(k in t for k in keys)

def enforce_line_limit(answer: str, question: str) -> str:
    max_lines = 10 if is_case_question(question) else 8
    lines = [ln.strip() for ln in (answer or "").splitlines() if ln.strip()]
    if len(lines) <= max_lines:
        return "\n".join(lines).strip()
    return "\n".join(lines[:max_lines]).strip()

def gerar_resposta(curriculo: str, vaga: str, empresa: str, pergunta: str) -> str:
    client = OpenAI()
    mercado = google_context(empresa)

    dev = (
        "Você é um treinador de entrevista. Responda em PT-BR.\n"
        "Regras:\n"
        "1) Use APENAS currículo + vaga + contexto real de mercado.\n"
        "2) NÃO invente fatos que não constem no currículo e na vaga.\n"
        "3) Seja rápido e objetivo.\n"
        "4) Limite: até 8 linhas; se for case, até 10 linhas.\n"
    )

    user = f"""
EMPRESA:
{empresa}

CURRÍCULO:
{curriculo}

VAGA:
{vaga}

MERCADO (Google):
{mercado}

PERGUNTA DO RECRUTADOR:
{pergunta}

Gere a melhor resposta como candidato.
"""

    resp = client.responses.create(
        model="gpt-5.2",
        input=[{"role": "developer", "content": dev}, {"role": "user", "content": user}],
        reasoning={"effort": "low"},
    )
    return (resp.output_text or "").strip()

# ========= UI =========
st.subheader("Sessão de Treinamento")

c1, c2 = st.columns(2)
with c1:
    if st.button("Iniciar"):
        st.session_state.running = True
with c2:
    if st.button("Encerrar"):
        st.session_state.running = False
        st.session_state.curriculo = ""
        st.session_state.vaga = ""
        st.session_state.transcricao = ""
        st.session_state.start_voice = False
        st.session_state.last_audio_len = 0
        st.success("Sessão encerrada.")

if not st.session_state.running:
    st.stop()

empresa = st.text_input("Empresa")
curr_file = st.file_uploader("Anexar currículo (PDF/DOCX/TXT)", type=["pdf", "docx", "txt"])
vaga_text = st.text_area("Descrição da vaga")

if st.button("Carregar dados"):
    st.session_state.curriculo = extract_text(curr_file)
    st.session_state.vaga = (vaga_text or "").strip()

if not st.session_state.curriculo or not st.session_state.vaga or not empresa:
    st.info("Informe empresa, currículo e vaga.")
    st.stop()

# ====== BOTÃO INICIAR (MOSTRA VOZ) ======
if not st.session_state.start_voice:
    if st.button("Iniciar pergunta"):
        st.session_state.start_voice = True
        st.rerun()

# ====== VOZ (APARECE SÓ DEPOIS DO INICIAR) ======
if st.session_state.start_voice:
    st.subheader("Pesquisa de voz")
    audio_bytes = audio_recorder(text="Falar agora", recording_color="#e74c3c", neutral_color="#2ecc71")

    # Quando terminar de falar (novo áudio), transcreve e responde
    if audio_bytes and len(audio_bytes) != st.session_state.last_audio_len:
        st.session_state.last_audio_len = len(audio_bytes)

        client = OpenAI()
        with st.spinner("Transcrevendo..."):
            tr = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=("pergunta.wav", audio_bytes),
            )
            st.session_state.transcricao = (tr.text or "").strip()

        st.markdown("**Pergunta transcrita:**")
        st.write(st.session_state.transcricao)

        with st.spinner("Respondendo..."):
            resposta = gerar_resposta(
                st.session_state.curriculo,
                st.session_state.vaga,
                empresa,
                st.session_state.transcricao,
            )

        resposta_final = enforce_line_limit(resposta, st.session_state.transcricao)

        st.markdown("### Resposta")
        st.write(resposta_final)

        # volta para o botão "Iniciar pergunta" para próxima pergunta
        st.session_state.start_voice = False
        st.rerun()
