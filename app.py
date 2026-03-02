import streamlit as st
import io
from openai import OpenAI
from audio_recorder_streamlit import audio_recorder

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Treinamento EMP", layout="wide")

# Inicialização das variáveis de estado
if "logged" not in st.session_state:
    st.session_state.logged = False
if "analise_gerada" not in st.session_state:
    st.session_state.analise_gerada = False
if "modo_entrevista" not in st.session_state:
    st.session_state.modo_entrevista = False
if "empresa" not in st.session_state:
    st.session_state.empresa = ""
if "vaga" not in st.session_state:
    st.session_state.vaga = ""
if "analise_estrategica" not in st.session_state:
    st.session_state.analise_estrategica = ""
if "transcricao" not in st.session_state:
    st.session_state.transcricao = ""
if "resposta_ideal" not in st.session_state:
    st.session_state.resposta_ideal = ""
if "last_audio_len" not in st.session_state:
    st.session_state.last_audio_len = 0

def get_client():
    # Puxa a chave sk-... cadastrada nos Secrets do Streamlit
    api_key = st.secrets.get("OPENAI_API_KEY", "")
    return OpenAI(api_key=api_key)

# --- PÁGINA 1: LOGIN ---
if not st.session_state.logged:
    st.title("🔐 Login - Treinamento EMP")
    u = st.text_input("Usuário")
    p = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if u and p: # Aqui você pode definir um usuário/senha fixo se quiser
            st.session_state.logged = True
            st.rerun()
    st.stop()

# --- PÁGINA 2: SISTEMA PRINCIPAL ---
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
            with st.spinner("Gerando Análise Estratégica..."):
                st.session_state.empresa = emp
                st.session_state.vaga = desc
                client = get_client()
                # Chamada para o modelo correto gpt-4o-mini
                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Analise pontos fortes e lacunas do candidato para esta vaga."},
                        {"role": "user", "content": f"Empresa: {emp}\nVaga: {desc}"}
                    ]
                )
                st.session_state.analise_estrategica = res.choices[0].message.content
                st.session_state.analise_gerada = True
                st.rerun()

with c2:
    st.subheader("Análise Estratégica (Leitura)")
    st.info(st.session_state.analise_estrategica if st.session_state.analise_estrategica else "Aguardando dados...")

st.divider()

# BLOCO 2: SIMULAÇÃO DE ENTREVISTA
st.header("🔷 BLOCO 2 — SIMULAÇÃO DE ENTREVISTA")

if not st.session_state.analise_gerada:
    st.warning("⚠️ Você precisa gerar a análise no Bloco 1 primeiro.")
else:
    col_btn1, col_btn2 = st.columns([1, 5])
    with col_btn1:
        if st.button("▶️ Iniciar"):
            st.session_state.modo_entrevista = True
    with col_btn2:
        if st.button("🛑 Encerrar"):
            st.session_state.clear() # Limpa tudo conforme seu fluxo
            st.rerun()

    if st.session_state.modo_entrevista:
        st.write("🎤 Microfone ativo. Fale sua pergunta:")
        audio = audio_recorder(text="", neutral_color="#2ecc71")
        
        if audio and len(audio) != st.session_state.last_audio_len:
            st.session_state.last_audio_len = len(audio)
            client = get_client()
            with st.spinner("Processando..."):
                # Transcrição via Whisper-1
                tr = client.audio.transcriptions.create(model="whisper-1", file=("audio.wav", audio))
                st.session_state.transcricao = tr.text
                
                # Resposta baseada na estratégia
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Gere uma resposta ideal de até 8 linhas (ou 10 para cases)."},
                        {"role": "user", "content": f"Pergunta: {tr.text}\nEstratégia: {st.session_state.analise_estrategica}"}
                    ]
                )
                st.session_state.resposta_ideal = resp.choices[0].message.content
                st.rerun()

        st.text_input("Transcrição da Pergunta", value=st.session_state.transcricao, disabled=True)
        nova_resp = st.text_area("Resposta Estratégica (Editável)", value=st.session_state.resposta_ideal, height=200)
        
        if st.button("🔄 Atualizar Resposta"):
            st.session_state.resposta_ideal = nova_resp
            st.success("Resposta atualizada!")
