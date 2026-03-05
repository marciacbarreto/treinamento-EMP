import streamlit as st
import io
import hashlib
from openai import OpenAI
from audio_recorder_streamlit import audio_recorder
import PyPDF2
import docx

# --- CONFIGURAÇÃO E ESTADO ---
st.set_page_config(page_title="Treinamento EMP", layout="wide")

defaults = {
    "logged": False, "analise_gerada": False, "modo_entrevista": False,
    "empresa": "", "vaga": "", "analise_estrategica": "",
    "transcricao": "", "resposta_ideal": "", "last_audio_hash": ""
}
for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

def get_client():
    api_key = st.secrets.get("OPENAI_API_KEY", "")
    return OpenAI(api_key=api_key)

# INTEGRAÇÃO: Função de leitura profunda de arquivos
def extrair_texto_cv(uploaded_file):
    if uploaded_file is None: return ""
    name = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        pdf = PyPDF2.PdfReader(uploaded_file)
        return "\n".join([p.extract_text() for p in pdf.pages])
    elif name.endswith(".docx"):
        doc = docx.Document(uploaded_file)
        return "\n".join([p.text for p in doc.paragraphs])
    else:
        return uploaded_file.read().decode("utf-8", errors="ignore")

# --- PÁGINA 1: LOGIN ---
if not st.session_state.logged:
    st.title("🔐 Login - Treinamento EMP")
    u = st.text_input("Usuário")
    p = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if u and p:
            st.session_state.logged = True
            st.rerun()
    st.stop()

# --- PÁGINA 2: SISTEMA ---
st.title("🎯 Treinamento EMP")

# BLOCO 1: DADOS ESTRATÉGICOS
st.header("🔷 BLOCO 1 — DADOS ESTRATÉGICOS")
c1, c2 = st.columns(2)

with c1:
    emp = st.text_input("Empresa", value=st.session_state.empresa)
    desc = st.text_area("Descrição da Vaga", value=st.session_state.vaga, height=150)
    uploaded_cv = st.file_uploader("Upload do Currículo", type=["pdf", "docx", "txt"])

    if st.button("Atualizar Análise"):
        if emp and desc and uploaded_cv:
            with st.spinner("Analisando currículo e vaga..."):
                cv_text = extrair_texto_cv(uploaded_cv)
                st.session_state.empresa, st.session_state.vaga = emp, desc
                client = get_client()
                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Analise o CV e a vaga. Forneça pontos fortes e uma estratégia de resposta."},
                        {"role": "user", "content": f"Empresa: {emp}\nVaga: {desc}\nCV: {cv_text}"}
                    ]
                )
                st.session_state.analise_estrategica = res.choices[0].message.content
                st.session_state.analise_gerada = True
                st.rerun()

with c2:
    st.subheader("Análise Estratégica")
    st.info(st.session_state.analise_estrategica or "Aguardando Bloco 1...")

st.divider()

# BLOCO 2: SIMULAÇÃO
st.header("🔷 BLOCO 2 — SIMULAÇÃO DE ENTREVISTA")

if st.session_state.analise_gerada:
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("▶️ Iniciar"): st.session_state.modo_entrevista = True
    with col2:
        if st.button("🛑 Encerrar"):
            st.session_state.clear()
            st.rerun()

    if st.session_state.modo_entrevista:
        st.write("🎤 Fale sua pergunta:")
        audio = audio_recorder(text="", neutral_color="#2ecc71")

        if audio:
            audio_hash = hashlib.sha1(audio).hexdigest()
            if audio_hash != st.session_state.last_audio_hash:
                st.session_state.last_audio_hash = audio_hash
                client = get_client()
                with st.spinner("Processando áudio..."):
                    audio_file = io.BytesIO(audio)
                    audio_file.name = "audio.wav"
                    tr = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
                    st.session_state.transcricao = tr.text
                    
                    # INTEGRAÇÃO: Resposta amarrada à estratégia do Bloco 1
                    resp = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": f"Use esta estratégia: {st.session_state.analise_estrategica}"},
                            {"role": "user", "content": f"Pergunta: {tr.text}"}
                        ]
                    )
                    st.session_state.resposta_ideal = resp.choices[0].message.content
                    st.rerun()

        st.text_input("Pergunta detectada", value=st.session_state.transcricao, disabled=True)
        nova_resp = st.text_area("Sugestão de Resposta", value=st.session_state.resposta_ideal, height=200)
        if st.button("🔄 Refinar Resposta"):
            st.session_state.resposta_ideal = nova_resp
            st.success("Refinado!")
