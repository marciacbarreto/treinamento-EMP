import os
import io
import streamlit as st
import requests
from openai import OpenAI
from audio_recorder_streamlit import audio_recorder

# ================== CONFIG ==================
st.set_page_config(page_title="Treinamento EMP", layout="centered")
st.title("Treinamento EMP")

# ================== STATE ==================
def init_state():
    defaults = {
        "logged": False,
        "running": False,
        "start_voice": False,
        "last_audio_len": 0,
        "curriculo": "",
        "vaga": "",
        "empresa": "",
        "campo_transcricao": "",
        "campo_resposta": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ================== CLIENT (OpenAI via Streamlit Secrets) ==================
def get_openai_client() -> OpenAI:
    # Lê diretamente do Secrets para não depender de os.getenv
    api_key = st.secrets.get("OPENAI_API_KEY", "")
    if not api_key or not api_key.startswith("sk-"):
        st.error("OPENAI_API_KEY ausente ou inválida nos Secrets do Streamlit.")
        st.stop()
    return OpenAI(api_key=api_key)

# ================== FILE READERS ==================
def read_pdf(file_bytes: bytes) -> str:
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
        return (text or "").strip()
    except Exception:
        return ""

def read_docx(file_bytes: bytes) -> str:
    try:
        import docx
        doc = docx.Document(io.BytesIO(file_bytes))
        text = "\n".join(p.text for p in doc.paragraphs)
        return (text or "").strip()
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

# ================== GOOGLE CONTEXT (optional) ==================
def google_context(empresa: str) -> str:
    key = st.secrets.get("GOOGLE_CSE_API_KEY")
    cx = st.secrets.get("GOOGLE_CSE_CX")
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
        text = "\n".join(s for s in snippets if s).strip()
        return text if text else "Sem dados de mercado disponíveis."
    except Exception:
        return "Sem dados de mercado disponíveis."

# ================== LIMITS ==================
def is_case_question(text: str) -> bool:
    t = (text or "").lower()
    keys = ["case", "cenário", "situação", "situaçao", "como você faria", "como vc faria", "resolva", "resolveria", "desafio", "problema"]
    return any(k in t for k in keys)

def enforce_line_limit(answer: str, question: str) -> str:
    max_lines = 10 if is_case_question(question) else 8
    lines = [ln.strip() for ln in (answer or "").splitlines() if ln.strip()]
    return "\n".join(lines[:max_lines]).strip()

# ================== CORE IA ==================
def gerar_resposta(curriculo: str, vaga: str, empresa: str, pergunta: str) -> str:
    client = get_openai_client()
    mercado = google_context(empresa)

    dev = (
        "Você é um treinador de entrevista. Responda em PT-BR.\n"
        "Regras obrigatórias:\n"
        "1) Use APENAS currículo + vaga + contexto real de mercado.\n"
        "2) NÃO invente fatos que não constem no currículo e na vaga.\n"
        "3) Seja rápido e objetivo.\n"
        "4) Limite: até 8 linhas; se for case, até 10 linhas.\n"
        "5) A resposta deve soar como o recrutador gostaria de ouvir.\n"
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
        input=[
            {"role": "developer", "content": dev},
            {"role": "user", "content": user},
        ],
        reasoning={"effort": "low"},
    )
    return (resp.output_text or "").strip()

def ajustar_resposta_usuario(pergunta: str, resposta_editada: str, curriculo: str, vaga: str, empresa: str) -> str:
    """
    Ajusta (refina) o texto que VOCÊ editou, mantendo coerência com currículo+vaga e limite de linhas.
    """
    client = get_openai_client()
    mercado = google_context(empresa)

    dev = (
        "Você é um coach de entrevista.\n"
        "Regras obrigatórias:\n"
        "1) Refine o texto do usuário para ficar profissional e natural.\n"
        "2) NÃO invente fatos que não estejam no currículo e na vaga.\n"
        "3) Mantenha alinhado ao que a empresa e a vaga pedem.\n"
        "4) Limite: até 8 linhas; se for case, até 10 linhas.\n"
        "5) Entregue somente a resposta final (sem comentários).\n"
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

TEXTO QUE O CANDIDATO EDITOU (REFINAR):
{resposta_editada}
"""

    resp = client.responses.create(
        model="gpt-5.2",
        input=[
            {"role": "developer", "content": dev},
            {"role": "user", "content": user},
        ],
        reasoning={"effort": "low"},
    )
    return (resp.output_text or "").strip()

# ================== LOGIN (simple) ==================
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

# ================== SESSION CONTROLS ==================
st.subheader("Sessão de Treinamento")
c1, c2 = st.columns(2)

with c1:
    if st.button("Iniciar"):
        st.session_state.running = True

with c2:
    if st.button("Encerrar"):
        st.session_state.running = False
        st.session_state.start_voice = False
        st.session_state.last_audio_len = 0
        st.session_state.curriculo = ""
        st.session_state.vaga = ""
        st.session_state.empresa = ""
        st.session_state.campo_transcricao = ""
        st.session_state.campo_resposta = ""
        st.success("Sessão encerrada.")

if not st.session_state.running:
    st.stop()

# ================== INPUTS: EMPRESA + CURRÍCULO + VAGA ==================
empresa = st.text_input("Empresa", value=st.session_state.empresa)
curr_file = st.file_uploader("Anexar currículo (PDF/DOCX/TXT)", type=["pdf", "docx", "txt"])
vaga_text = st.text_area("Descrição da vaga", value=st.session_state.vaga)

if st.button("Carregar dados"):
    st.session_state.empresa = (empresa or "").strip()
    st.session_state.curriculo = extract_text(curr_file)
    st.session_state.vaga = (vaga_text or "").strip()

# validações
if not st.session_state.empresa or not st.session_state.curriculo or not st.session_state.vaga:
    st.info("Preencha Empresa, anexe Currículo e cole a Vaga. Depois clique em 'Carregar dados'.")
    st.stop()

# ================== BOTÃO PARA INICIAR VOZ ==================
if not st.session_state.start_voice:
    if st.button("Iniciar pergunta"):
        st.session_state.start_voice = True
        st.rerun()

# ================== ÁREA DE VOZ + CAMPOS ==================
st.markdown("## Pesquisa de voz")

# Campos (sempre visíveis)
st.markdown("### Transcrição da pergunta")
st.text_area(
    label="",
    key="campo_transcricao",
    height=120,
    disabled=True
)

st.markdown("### Resposta sugerida (você pode ajustar)")
st.text_area(
    label="",
    key="campo_resposta",
    height=190
)

# Botão para “arrumar” sua edição
colA, colB = st.columns([1, 1])
with colA:
    if st.button("Ajustar resposta"):
        if not st.session_state.campo_transcricao.strip():
            st.warning("Primeiro faça uma pergunta por voz para gerar a transcrição.")
        elif not st.session_state.campo_resposta.strip():
            st.warning("Escreva/ajuste algo no campo de resposta antes de clicar em Ajustar.")
        else:
            with st.spinner("Ajustando resposta..."):
                txt = ajustar_resposta_usuario(
                    pergunta=st.session_state.campo_transcricao,
                    resposta_editada=st.session_state.campo_resposta,
                    curriculo=st.session_state.curriculo,
                    vaga=st.session_state.vaga,
                    empresa=st.session_state.empresa,
                )
            st.session_state.campo_resposta = enforce_line_limit(txt, st.session_state.campo_transcricao)
            st.rerun()

with colB:
    if st.button("Limpar campos"):
        st.session_state.campo_transcricao = ""
        st.session_state.campo_resposta = ""
        st.session_state.last_audio_len = 0
        st.rerun()

# Microfone só aparece depois do "Iniciar pergunta"
if st.session_state.start_voice:
    audio_bytes = audio_recorder(text="Falar agora", recording_color="#e74c3c", neutral_color="#2ecc71")

    # quando terminar de falar (novo áudio), transcreve e responde
    if audio_bytes and len(audio_bytes) != st.session_state.last_audio_len:
        st.session_state.last_audio_len = len(audio_bytes)

        client = get_openai_client()

        with st.spinner("Transcrevendo..."):
            tr = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=("pergunta.wav", audio_bytes),
            )
            pergunta = (tr.text or "").strip()

        st.session_state.campo_transcricao = pergunta

        with st.spinner("Gerando resposta..."):
            resp = gerar_resposta(
                st.session_state.curriculo,
                st.session_state.vaga,
                st.session_state.empresa,
                pergunta,
            )

        st.session_state.campo_resposta = enforce_line_limit(resp, pergunta)

        # volta a exigir clicar em "Iniciar pergunta" para a próxima
        st.session_state.start_voice = False
        st.rerun()
else:
    st.caption("Clique em **Iniciar pergunta** para habilitar o microfone.")
