import streamlit as st
import io
import hashlib
from openai import OpenAI
from audio_recorder_streamlit import audio_recorder
import PyPDF2
import docx

# --- 1. CONFIGURAÇÃO E PADRÕES OBRIGATÓRIOS ---
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
if "analise_gerada" not in st.session_state: st.session_state.logged = False
if "modo_entrevista" not in st.session_state: st.session_state.modo_entrevista = False
if "cv_text" not in st.session_state: st.session_state.cv_text = ""
if "transcricao" not in st.session_state: st.session_state.transcricao = ""
if "resposta_ideal" not in st.session_state: st.session_state.resposta_ideal = ""
if "last_audio_hash" not in st.session_state: st.session_state.last_audio_hash = ""

def get_client():
    return OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", ""))

def extrair_texto(file):
    if not file: return ""
    fname = file.name.lower()
    try:
        if fname.endswith(".pdf"):
            pdf = PyPDF2.PdfReader(file)
            return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
        elif fname.endswith(".docx"):
            doc = docx.Document(file)
            return "\n".join([p.text for p in doc.paragraphs])
        return file.read().decode("utf-8", errors="ignore")
    except: return "Erro na leitura."

# --- 3. LOGIN ---
if not st.session_state.logged:
    st.title("🔐 Login - Treinamento EMP")
    u, p = st.text_input("Usuário"), st.text_input("Senha", type="password")
    if st.button("Entrar") and u and p:
        st.session_state.logged = True
        st.rerun()
    st.stop()

# --- 4. INTERFACE (SEQUÊNCIA RIGOROSA) ---
st.title("🎯 Treinamento EMP")

# 1. Empresa
empresa = st.text_input("Empresa", key="emp_p", placeholder="Digite o nome da empresa...")

# 2. Descrição da vaga | Currículo
col_vaga, col_cv = st.columns(2)
with col_vaga:
    vaga = st.text_area("Descrição da vaga", height=150, key="vaga_p")
with col_cv:
    uploaded_cv = st.file_uploader("Currículo", type=["pdf", "docx", "txt"])

# 3. Ferramentas que a empresa trabalha
ferramentas = st.text_area("Ferramentas que a empresa trabalha (explicação)", height=100, key="ferr_p")

# 4. Botões: [ Iniciar ] [ Atualizar ] [ Encerrar ]
st.write("")
c_ini, c_atu, c_enc = st.columns([1, 1, 1])

with c_atu:
    if st.button("🔄 Atualizar", use_container_width=True):
        if empresa and vaga and uploaded_cv:
            with st.spinner("Processando cruzamento de dados..."):
                st.session_state.cv_text = extrair_texto(uploaded_cv)
                st.session_state.analise_gerada = True
                st.success("Dados prontos para a simulação!")

with c_ini:
    if st.button("▶️ Iniciar", use_container_width=True):
        st.session_state.modo_entrevista = True

with c_enc:
    if st.button("🛑 Encerrar", use_container_width=True):
        st.session_state.modo_entrevista = False
        st.session_state.transcricao = ""
        st.session_state.resposta_ideal = ""
        st.rerun()

st.divider()

# 5. Microfone / Áudio
if st.session_state.modo_entrevista and st.session_state.analise_gerada:
    st.write("🎤 **Microfone / Áudio para escutar pergunta**")
    audio = audio_recorder(text="Clique para falar a pergunta", neutral_color="#2ecc71")
    
    if audio:
        a_hash = hashlib.sha1(audio).hexdigest()
        if a_hash != st.session_state.last_audio_hash:
            st.session_state.last_audio_hash = a_hash
            client = get_client()
            with st.spinner("Gerando resposta estratégica..."):
                # Transcrição (Whisper)
                tr = client.audio.transcriptions.create(model="whisper-1", file=("a.wav", io.BytesIO(audio)))
                st.session_state.transcricao = tr.text
                
                # Resposta Estratégica (GPT) - Cruzamento de Empresa + Vaga + CV + Pergunta
                prompt = f"""
                Contexto: Entrevista na empresa {empresa}. 
                Vaga: {vaga}. Ferramentas foco: {ferramentas}.
                Currículo do Candidato: {st.session_state.cv_text[:2500]}.
                
                Pergunta ouvida: "{tr.text}"
                
                Instruções de Resposta:
                - Seja convincente, use tom de conversa natural.
                - Use as competências: {', '.join(PALAVRAS_CHAVE)}.
                - Finalize obrigatoriamente com o rodapé: {RODAPE_FERRAMENTAS}
                """
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": prompt}]
                )
                st.session_state.resposta_ideal = resp.choices[0].message.content
                st.rerun()

    # 6. Transcrição da pergunta (Exibição após áudio)
    if st.session_state.transcricao:
        st.subheader("Transcrição da pergunta")
        st.info(st.session_state.transcricao)

    # 7. Resposta estratégica (Exibição final)
    if st.session_state.resposta_ideal:
        st.subheader("Resposta estratégica")
        st.write(st.session_state.resposta_ideal)
