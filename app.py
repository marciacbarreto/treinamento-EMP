import streamlit as st
from openai import OpenAI

# ------------------------------
# CONFIGURAÇÃO
# ------------------------------

st.set_page_config(page_title="Treinamento EMP", layout="wide")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ------------------------------
# PROMPT BASE (SEU PROMPT FINAL)
# ------------------------------

PROMPT_BASE = """
Você é um assistente de preparação para entrevistas.

Siga TODAS as regras abaixo rigorosamente:

- Sempre cruze as informações da vaga com o currículo antes de responder.

- Identifique as ferramentas, sistemas e metodologias mencionadas na vaga (ex: Excel, Power BI, SAP, SQL, CRM, Lean, Six Sigma, etc.).

- Utilize apenas ferramentas que:
  - estejam no currículo, ou  
  - façam sentido com a experiência descrita (sem inventar uso direto).

- Quando a vaga mencionar uma ferramenta:
  - Se estiver no currículo → afirmar experiência direta  
  - Se não estiver → demonstrar conhecimento ou similaridade (sem mentir)

- Explique sempre para que serve a ferramenta dentro da função da vaga, não apenas citar.

- Conecte a ferramenta com uma atividade real do currículo.

- Mostre impacto (ex: melhoria de processo, ganho de eficiência, controle, redução de erros, apoio à decisão).

- Evite respostas genéricas — sempre contextualizar com algo concreto.

- Linguagem natural, como conversa, sem parecer robótico.

---

- Sempre que a vaga mencionar ferramentas, sistemas ou metodologias, inclua essas ferramentas na resposta explicando o uso prático.

- Não apenas cite — explique o uso (ex: análise de dados, controle, automação, decisão).

- Se não estiver explícita na vaga, mas fizer sentido, pode incluir sem inventar experiência.

---

- Respostas entre 5 e 8 linhas, diretas e faláveis.

- Não parecer texto escrito — parecer fala natural de entrevista.

- Estrutura interna:
  contexto → conexão com vaga → ferramentas → impacto

- Adaptar conforme a pergunta:
  - comportamental → situação, ação, resultado
  - técnica → ferramentas + execução
  - carreira → narrativa coerente

- Tom seguro (sem "acho", "talvez").

- Variar início das respostas.

- Conectar sempre com a vaga.

- Nunca inventar experiência.

- Quando não tiver, usar aproximação inteligente.

- Sempre fechar com impacto (eficiência, controle, decisão).
"""

# ------------------------------
# INTERFACE
# ------------------------------

st.title("🎯 Treinamento de Entrevista (Estilo Parakeet)")

col1, col2 = st.columns(2)

with col1:
    curriculo = st.text_area("📄 Cole o currículo", height=300)

with col2:
    vaga = st.text_area("📋 Cole a descrição da vaga", height=300)

pergunta = st.text_input("❓ Pergunta da entrevista")

# ------------------------------
# CLASSIFICAÇÃO SIMPLES DE PERGUNTA
# ------------------------------

def classificar_pergunta(texto):
    texto = texto.lower()

    if any(p in texto for p in ["desafio", "erro", "conflito", "dificuldade"]):
        return "comportamental"
    elif any(p in texto for p in ["ferramenta", "tecnologia", "sistema", "processo"]):
        return "tecnica"
    elif any(p in texto for p in ["por que", "carreira", "mudou", "trajetoria"]):
        return "carreira"
    else:
        return "geral"

# ------------------------------
# GERAÇÃO DE RESPOSTA
# ------------------------------

if st.button("Gerar Resposta"):

    if not curriculo or not vaga or not pergunta:
        st.warning("Preencha currículo, vaga e pergunta.")
    else:
        tipo = classificar_pergunta(pergunta)

        prompt_final = f"""
{PROMPT_BASE}

CURRÍCULO:
{curriculo}

VAGA:
{vaga}

TIPO DE PERGUNTA:
{tipo}

PERGUNTA:
{pergunta}

Responda conforme todas as regras.
"""

        response = client.chat.completions.create(
            model="gpt-5.3",
            messages=[{"role": "user", "content": prompt_final}],
            temperature=0.4
        )

        resposta = response.choices[0].message.content

        st.subheader("💬 Resposta sugerida")
        st.write(resposta)
