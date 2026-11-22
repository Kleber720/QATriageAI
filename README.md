# QA Triage AI (YouShop) — Triagem Local de Bugs para QA

Assistente de triagem para **e-commerce web e atendimento (YouShop / WhatsApp)** que transforma **relatos vagos** (*"Oi, não consegui comprar no site da YouShop, deu erro na hora de pagar"*) ou **rascunhos incompletos de tickets** em relatórios reproduzíveis para equipes de QA, rodando **100% localmente** com **Ollama** (`qwen3:4b-instruct`), **FastAPI (Python)** e **React + TypeScript**.

---

## Como o Fluxo Funciona

1. **Entrada (Relato Vago ou Rascunho):** o cliente/atendente envia o relato ou seleciona um dos 7 cenários corporativos em 1 clique.
2. **Diagnóstico Híbrido:** o backend compara o relato contra a checklist oficial do **Escopo do Bug**, calcula o score inicial de reprodutibilidade, identifica lacunas/ortografia/dados sensíveis e gera **no máximo 5 perguntas curtas de baixa fricção**.
3. **Perguntas + Etapa 4 (Logs da Plataforma):** o usuário responde apenas ao que sabe (ou clica em **"Não sei / Pular"**) e opcionalmente vincula uma sessão de log ou cola um log bruto.
4. **Ticket Estruturado com Separação Epistêmica na Tela:** a interface exibe o ticket no Escopo Oficial junto com **`O que não foi confirmado`**, **`Origem dos Dados`** e **`Divergências entre Relato e Log`**.
5. **Exportação Limpa & Histórico Local:** ao clicar em **Copiar Markdown**, **Copiar Jira**, **Copiar JSON** ou **Baixar .md**, vai para a área de transferência **apenas o ticket QA limpo** (sem os avisos internos da IA), mantendo o histórico salvo no navegador.

---

## Arquitetura (Pipeline Sanduíche)

```text
[Frontend — React + Vite + Tailwind]
  Entrada -> Perguntas + Etapa 4 (Logs) -> Ticket Estruturado + Histórico Local
                          │ HTTP JSON
                          ▼
[Backend — FastAPI + Pydantic v2]
  1. Pré-Análise Determinística (rule_engine.py + pii_sanitizer.py)
     • Valida estrutura do Escopo do Bug, marcador final e lacunas óbvias
     • Detecta e remove UUIDs, Product IDs e domínios corporativos (preserva CPU/RAM/x64)
  2. Inferência Local Estruturada (ollama_provider.py -> /api/chat JSON Schema)
     • Modelo local: qwen3:4b-instruct + rubrica e exemplos corporativos (knowledge/)
     • Detecta omissões semânticas (ex.: mouse vs teclado, etapas faltando)
  3. Trava Pós-LLM & Cruzamento de Logs (grounding_validator.py + platform_context/)
     • Impede inventar Taxa de Reprodução ou logs ausentes
     • Garante exatamente 1 marcador "É aqui que o bug é observado" ao final das etapas
     • Move itens pulados ou respondidos com "não sei" para "O que não foi confirmado"
     • Separa origem: user_report | platform_log | unconfirmed | ai_hypothesis
```

---

## Critério "Reconhecer os Limites" & Baixa Fricção na Prática

- **Separação explícita entre fato e lacuna ([`grounding_validator.py`](backend/app/domain/grounding_validator.py)):**
  - Se o usuário clicar em **"Não sei / Pular"** ou digitar respostas incertas (`"não sei"`, `"não lembro"`, `"n/a"`), o validador garante a inclusão do campo em `o_que_nao_foi_confirmado` e impede que o score de prontidão seja inflado.
  - Se não existir razão `X/Y` ou frequência explícita no relato/respostas, `taxa_de_reproducao` é forçada para `"Não informado"`, mesmo que o LLM tente fabricar `"1/1"`.
  - Fatos `platform_log` e `divergencias_com_logs` só são permitidos quando um log foi realmente anexado.
- **Baixa Fricção ([`triage_service.py`](backend/app/services/triage_service.py)):** perguntas que peçam specs de PC, CPU, RAM, IDs do Windows ou prints/vídeos/evidências ao cliente final são bloqueadas por código; dados técnicos só entram se enviados espontaneamente ou via telemetria.
- **Privacidade ([`pii_sanitizer.py`](backend/app/domain/pii_sanitizer.py)):** sanitiza IDs de máquina, Product IDs, e-mails, CPFs e domínios corporativos antes de enviar ao LLM e antes de exibir as `NOTAS`.

---

## Benchmark Real no Ollama Local (`qwen3:4b-instruct` — RTX 3050 8 GB)

Executado com `python tests\run_ollama_evals.py` sobre os casos de [`qa_evals.jsonl`](backend/dataset/qa_evals.jsonl):

| Caso | Categoria | Campos Faltantes | PII | Baixa Fricção | Placeholders | Tempo | Resultado |
|---|---|---|---|---|---|---|---|
| `youshop_ruim_1` | `bug_funcional` | `ok` | `ok` | `ok` | `ok` | `45.5s` | **PASS** |
| `youshop_ruim_2` | `bug_funcional` | `ok` | `ok` | `ok` | `ok` | `38.7s` | **PASS** |
| `youshop_ruim_3` | `bug_funcional` | `ok` | `ok` | `ok` | `ok` | `28.7s` | **PASS** |
| `youshop_ref_pix` | `erro_integracao` | `ok` | `ok` | `ok` | `ok` | `25.1s` | **PASS** |
| `youshop_ref_painel_pii` | `erro_bloqueante` | `ok` | `ok` | `ok` | `ok` | `20.7s` | **PASS** |
| `anti_hallucination_generate` *(tudo pulado)* | — | — | — | — | — | `25.5s` | **PASS** (`taxa='Não informado'`, `marker_count=1`) |

---

## Cenários de Demo em 30 Segundos

| Cenário na Tela Inicial | Sessão de Log Sugerida (Etapa 4) | O que demonstra |
|---|---|---|
| **WhatsApp — Relato Vago de Compra** | `PED-9042` | Relato curto de cliente vira ticket completo com perguntas objetivas |
| **Checkout Web — Divergência com Log** | `PED-9042` | Cliente acha que o cartão recusou; log revela `HTTP 504 Gateway Timeout` |
| **YouShop — Ticket Ruim #1 / #2 / #3** | `SESS-YS-104` | Detecção de resultados vazios, passos faltando no checkout, marcador fora do padrão e ortografia |
| **YouShop — Referência #1 (Integração PIX Safari)** | `SESS-YS-218` | Classificação `erro_integracao`, comparação Android Chrome vs Safari iOS e `ERR_IOS_CLIPBOARD_DENIED` |
| **YouShop — Referência #2 (Painel WhatsApp + PII)** | `SESS-YS-309` | Sanitização de UUID/Product ID mantendo specs úteis + erro `ERR_PANEL_ROW_0x4F` |

---

## Como Rodar Localmente

### Pré-requisitos
- **Python 3.12+** (testado em Python 3.14.5)
- **Node.js 20+** (testado em Node.js 26.13.0)
- **Ollama** instalado e rodando localmente

### 1. Preparar o Modelo no Ollama
```powershell
ollama pull qwen3:4b-instruct
```
*(Opcional)* Criar a persona dedicada com o `Modelfile` do projeto:
```powershell
ollama create qa-triage -f ollama/Modelfile
```

### 2. Backend (FastAPI)
```powershell
cd backend
.\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
```
Swagger UI: `http://127.0.0.1:8000/docs`

### 3. Frontend (React + Vite)
Em outro terminal:
```powershell
cd frontend
npm run dev
```
Acesse **`http://localhost:5173`**.

---

## Testes Automatizados & Evals

```powershell
# Backend (unitários + API com MockLLMProvider)
cd backend
.\.venv\Scripts\pytest.exe -v

# Eval determinístico offline (sem Ollama)
.\.venv\Scripts\python.exe tests\run_ollama_evals.py --offline

# Eval completo ao vivo contra o Ollama local
.\.venv\Scripts\python.exe tests\run_ollama_evals.py

# Frontend (testes nativos Node + build de produção)
cd ..\frontend
npm test
npm run build
```

---

## Extensibilidade para Produção

- **Trocar o provedor de LLM:** implemente [`LLMProvider`](backend/app/services/llm/base.py) (ex.: Gemini API, OpenAI ou Anthropic) e troque a fábrica em [`dependencies.py`](backend/app/dependencies.py).
- **Conectar telemetria real (Sentry, Datadog, backend de pedidos):** implemente [`PlatformContextProvider`](backend/app/services/platform_context/base.py) no lugar de [`MockLogsProvider`](backend/app/services/platform_context/mock_logs_provider.py).
