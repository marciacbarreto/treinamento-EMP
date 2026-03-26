import streamlit as st
import io
import hashlib
from openai import OpenAI
from audio_recorder_streamlit import audio_recorder
import PyPDF2
import docx

# ------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ------------------------------

st.set_page_config(page_title="Treinamento EMP", layout="wide")

# ------------------------------
# CLIENTE OPENAI
# ------------------------------

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ------------------------------
# ESTADO DA SESSÃO (MANTIDO)
# ------------------------------

defaults = {
    "transcricao": "",
    "resposta": "",
    "ultimo_prompt": ""
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ------------------------------
# FUNÇÕES DE LEITURA (ADICIONADO)
# ------------------------------

def ler_pdf(file):
    reader = PyPDF2.PdfReader(file)
    texto = ""
    for page in reader.pages:
        texto += page.extract_text() or ""
    return texto

def ler_docx(file):
    doc = docx.Document(file)
    return "\n".join([p.text for p in doc.paragraphs])

# ------------------------------
# PROMPT BASE (MANTIDO)
# ------------------------------

PROMPT_BASE = """
Você é um assistente de preparação para entrevistas.

Siga TODAS as regras abaixo rigorosamente:

- Sempre cruze as informações da vaga com o currículo antes de responder.
- Identifique as ferramentas mencionadas na vaga (Excel, Power BI, SAP, SQL, CRM, Lean, etc.).
- Utilize apenas ferramentas do currículo ou compatíveis (sem inventar).
- Se tiver experiência → afirmar.
- Se não tiver → aproximar com lógica (sem mentir).
- Explicar para que serve a ferramenta no contexto.
- Conectar com experiência real.
- Mostrar impacto (eficiência, controle, decisão).
- Linguagem natural, sem robô.

---

- Incluir ferramentas da vaga com explicação prática.
- Não só citar — explicar uso.

---

- Respostas de 5 a 8 linhas.
- Tom falado, natural.
- Estrutura interna:
  contexto → vaga → ferramentas → impacto

- Adaptar tipo:
  comportamental / técnica / carreira

- Não usar “acho”, “talvez”.
- Não repetir padrão.
- Conectar com a vaga.
- Nunca inventar.
- Fechar com impacto.
"""

# ------------------------------
# INTERFACE (MANTIDA)
# ------------------------------

st.title("🎯 Treinamento de Entrevista (Estilo Parakeet)")

col1, col2 = st.columns(2)

with col1:
    curriculo = st.text_area("📄 Cole o currículo", height=250)

    # ✅ ADIÇÃO (UPLOAD SEM REMOVER NADA)
    arquivo = st.file_uploader("Ou envie o currículo (PDF/DOCX)", type=["pdf", "docx"])

with col2:
    vaga = st.text_area("📋 Cole a descrição da vaga", height=250)

pergunta = st.text_input("❓ Pergunta da entrevista")

# ------------------------------
# PROCESSAMENTO CURRÍCULO (CORRIGIDO)
# ------------------------------

curriculo_final = curriculo.strip() if curriculo else ""

if arquivo:
    texto_arquivo = ""

    if arquivo.type == "application/pdf":
        texto_arquivo = ler_pdf(arquivo)
    elif "word" in arquivo.type:
        texto_arquivo = ler_docx(arquivo)

    if texto_arquivo.strip():
        curriculo_final = texto_arquivo

# ------------------------------
# CLASSIFICAÇÃO (MANTIDA)
# ------------------------------

def classificar_pergunta(texto):
    texto = texto.lower()

    if any(p in texto for p in ["desafio", "erro", "conflito"]):
        return "comportamental"
    elif any(p in texto for p in ["ferramenta", "processo", "dados"]):
        return "tecnica"
    elif any(p in texto for p in ["por que", "carreira", "trajetoria"]):
        return "carreira"
    else:
        return "geral"

# ------------------------------
# BOTÃO (MANTIDO + DEBUG)
# ------------------------------

if st.button("Gerar Resposta"):

    if not curriculo_final.strip() or not vaga.strip() or not pergunta.strip():
        st.warning("Preencha currículo (ou envie arquivo), vaga e pergunta.")
    else:
        tipo = classificar_pergunta(pergunta)

        prompt_final = f"""
{PROMPT_BASE}

CURRÍCULO:
{curriculo_final}

VAGA:
{vaga}

TIPO:
{tipo}

PERGUNTA:
{pergunta}

Responda seguindo todas as regras.
"""

        # ✅ DEBUG VISUAL
        st.subheader("🧠 DEBUG - PROMPT ENVIADO")
        st.text_area("Prompt completo", prompt_final, height=250)

        # ✅ DEBUG LOG
        print(prompt_final)

        # salvar histórico
        st.session_state["ultimo_prompt"] = prompt_final

        response = client.chat.completions.create(
            model="gpt-5.3",
            messages=[{"role": "user", "content": prompt_final}],
            temperature=0.4
        )

        st.subheader("💬 Resposta sugerida")
        st.write(response.choices[0].message.content)
