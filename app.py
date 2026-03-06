import streamlit as st
import io
import hashlib
from openai import OpenAI
from audio_recorder_streamlit import audio_recorder
import PyPDF2
import docx

# --- 1. CONFIGURAÇÃO E PADRÕES ---
st.set_page_config(page_title="Treinamento EMP", layout="wide", initial_sidebar_state="collapsed")

RODAPE_FERRAMENTAS = (
    "Jira (backlog e tarefas ágeis) / Confluence (documentação e governança) / "
    "Miro (mapas e jornadas) / Google Analytics (comportamento no e-commerce) / "
    "Power BI (KPIs e dashboards) / Adobe Experience Manager (conteúdo digital) / "
    "Slack (colaboração entre áreas) / ChatGPT (IA para análise e otimização)"
)

PALAVRAS_CHAVE = [
    "gestão de projetos e estruturação de governança",
    "análise de dados e monitoramento de indicadores",
    "melhoria contínua de processos",
    "uso de tecnologia e inteligência artificial para otimização",
    "capacidade de conectar áreas e garantir alinhamento estratégico"
]

# --- 2. GESTÃO DE ESTADO (SESSION STATE) ---
if "logged" not in st.session_state: st.session_state.logged = False
if "analise_gerada" not in st.session_state: st.session_state.analise_gerada = False
if "modo_entrevista" not in st.session_state: st.session_state.modo_entrevista = False
if "analise_estrategica" not in st.session_state: st.session_state.analise_estrategica = ""
if "resposta_ideal" not in st.session_state: st.session_state.resposta_ideal = ""
if "cv_text" not in st.session_state: st.session_state.cv_text = ""
if "last_audio_hash" not in st.session_state: st.session_state.last_audio_hash = ""

def get_client():
    return OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", ""))

def extrair_texto(file):
    if not file: return ""
    try:
        fname = file.name.lower()
        if fname.endswith(".pdf"):
            pdf = PyPDF2.PdfReader(file)
            return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
        elif fname.endswith(".docx"):
            doc = docx.Document(file)
            return "\n".join([p.text for p in doc.paragraphs])
        return file.read().decode("utf-8", errors="ignore")
    except: return "Erro na leitura do arquivo."

# --- 3. LOGIN ---
if not st.session_state.logged:
    st.title("🔐 Login - Treinamento EMP")
    u, p = st.text_input("Usuário"), st.text_input("Senha", type="password")
    if st.button("Entrar") and u and p:
        st.session_state.logged = True
        st.rerun()
    st.stop()

# --- 4. INTERFACE (ORDEM DO DESENHO) ---
st.title("🎯 Treinamento EMP")

# EMPRESA
empresa = st.text_input("Empresa", key="emp_persist", placeholder="Nome da empresa...")

# LINHA: VAGA | CURRÍCULO
col_vaga, col_cv = st.columns(2)
with col_vaga:
    vaga = st.text_area("Descrição da Vaga", height=150, key="vaga_persist")
with col_cv:
    uploaded_cv = st.file_uploader("Upload do Currículo", type=["pdf", "docx", "txt"])
    if st.session_state.analise_gerada:
        with st.expander("📄 Ver Análise Estratégica Atual", expanded=True):
            st.write(st.session_state.analise_estrategica)

# FERRAMENTAS
ferramentas = st.text_area("Ferramentas que a empresa trabalha (explicação)", height=100, key="ferr_persist")

# BOTÕES DE CONTROLE
st.write("")
c_ini, c_atu, c_enc = st.columns([1, 1, 1])

with c_atu:
    if st.button("🔄 Atualizar", use_container_width=True):
        if empresa and vaga and uploaded_cv:
            with st.spinner("Cruzando dados..."):
                cv_txt = extrair_texto(uploaded_cv)
                st.session_state.cv_text = cv_txt
                client = get_client()
                prompt_b1 = f"Analise CV para {empresa}. Use obrigatoriamente: {', '.join(PALAVRAS_CHAVE)}."
                try:
                    res = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "system", "content": prompt_b1},
                                  {"role": "user", "content": f"VAGA: {vaga}\nCV: {cv_txt}"}]
                    )
                    st.session_state.analise_estrategica = res.choices[0].message.content
                    st.session_state.analise_gerada = True
                    st.rerun()
                except: st.error("Erro na API. Verifique os Secrets.")

with c_ini:
    if st.button("▶️ Iniciar", use_container_width=True):
        st.session_state.modo_entrevista = True

with c_enc:
    if st.button("🛑 Encerrar", use_container_width=True):
        st.session_state.modo_entrevista = False
        st.session_state.resposta_ideal = ""
        st.rerun()

st.divider()

# BLOCO 2 — SIMULAÇÃO
if st.session_state.modo_entrevista and st.session_state.analise_gerada:
    st.write("🎤 **Microfone / áudio para escutar pergunta**")
    audio = audio_recorder(text="Fale a pergunta agora", neutral_color="#2ecc71")
    
    if audio:
        a_hash = hashlib.sha1(audio).hexdigest()
        if a_hash != st.session_state.last_audio_hash:
            st.session_state.last_audio_hash = a_hash
            client = get_client()
            with st.spinner("Gerando resposta estratégica..."):
                try:
                    tr = client.audio.transcriptions.create(model="whisper-1", file=("a.wav", io.BytesIO(audio)))
                    prompt_final = f"""
                    Empresa: {empresa}. Estratégia: {st.session_state.analise_estrategica}.
                    CV: {st.session_state.cv_text[:2000]}.
                    Regras: Responda diretamente à pergunta. Use tom de conversa. 
                    Inclua: {', '.join(PALAVRAS_CHAVE)}.
                    Termine com: {RODAPE_FERRAMENTAS}
                    """
                    resp = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "system", "content": prompt_final},
                                  {"role": "user", "content": f"Pergunta: {tr.text}"}]
                    )
                    st.session_state.resposta_ideal = resp.choices[0].message.content
                    st.rerun()
                except: st.error("Erro no processamento do áudio.")

    if st.session_state.resposta_ideal:
        st.subheader("Resposta de acordo com: vaga + empresa + currículo + pergunta")
        st.success(st.session_state.resposta_ideal)
