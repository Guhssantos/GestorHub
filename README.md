# GestorHub

Painel executivo mobile-first para gestão do dia a dia: agenda Microsoft 365, resumos de reuniões via tl;dv e acompanhamento de chamados via Power BI — tudo em um único lugar.

---

## Funcionalidades

| Módulo | Descrição |
|---|---|
| **Início** | Agenda sincronizada com Microsoft Calendar · navegação por datas · Day Pulse (analytics de ocupação) |
| **Resumos tl;dv** | Resumos de reuniões recebidos via webhook · busca por texto · ações extraídas |
| **Chamados** | Dashboard Power BI embarcado para acompanhamento de SLAs |

---

## Configuração

### 1. Clone e instale dependências

```bash
git clone https://github.com/Guhssantos/GestorHub.git
cd GestorHub
pip install -r requirements.txt
```

### 2. Configure os segredos

Copie o arquivo de exemplo e preencha com seus valores:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Edite `.streamlit/secrets.toml`:

```toml
AZURE_CLIENT_ID     = "seu-client-id-do-azure"
AZURE_CLIENT_SECRET = "seu-client-secret-do-azure"
REDIRECT_URI        = "https://gestor-app.streamlit.app"
POWER_BI_URL        = "https://app.powerbi.com/reportEmbed?reportId=SEU_REPORT_ID&autoAuth=true&ctid=SEU_TENANT_ID"
WEBHOOK_API_KEY     = "uma-chave-secreta-forte-aqui"
```

### 3. Execute

```bash
streamlit run app.py
```

---

## Integração tl;dv (gratuita)

Existem duas formas de integrar o tl;dv sem usar a API paga:

### Opção A — Zapier (recomendada, zero código)

> Plano gratuito: 100 tarefas/mês — suficiente para uso pessoal.

1. Suba o `api.py` em um servidor acessível (ex: Railway, Render, ou sua própria VPS)
2. Defina a variável de ambiente `WEBHOOK_API_KEY` no servidor
3. No [Zapier](https://zapier.com), crie um Zap:
   - **Trigger:** tl;dv → "New Meeting Recording"
   - **Action:** Webhooks by Zapier → "POST"
     - URL: `https://SEU_SERVIDOR/webhook/tldv`
     - Payload Type: `json`
     - Data:
       ```json
       {
         "title": "{{meeting_title}}",
         "date": "{{meeting_date}}",
         "summary": "{{summary}}",
         "url": "{{recording_url}}",
         "actions": []
       }
       ```
     - Headers: `X-API-Key: SUA_CHAVE_AQUI`

### Opção B — Gmail API (automático, sem Zapier)

O tl;dv envia um e-mail com o resumo após cada reunião. O script `tldv_email_sync.py` lê esses e-mails e salva em `resumos.json`.

**Configuração:**

```bash
pip install -r requirements-tldv.txt
```

1. Acesse [Google Cloud Console](https://console.cloud.google.com)
2. Crie um projeto → ative a **Gmail API**
3. Crie credenciais OAuth 2.0 (tipo "App de computador")
4. Baixe o JSON e salve como `gmail_credentials.json` na raiz do projeto
5. Execute uma vez para autorizar:
   ```bash
   python tldv_email_sync.py --days 7
   ```
6. Para manter sincronizado, agende a execução diária:
   - **Windows:** Task Scheduler → `python tldv_email_sync.py`
   - **Linux/Mac:** `crontab -e` → `0 8 * * * python /caminho/tldv_email_sync.py`

---

## Webhook API (Flask)

O `api.py` expõe um endpoint para receber resumos:

```
POST /webhook/tldv
Header: X-API-Key: SUA_CHAVE
Body: {
  "title": "Nome da reunião",
  "date": "2025-05-01",
  "summary": "Texto do resumo",
  "url": "https://tldv.io/app/recordings/...",
  "actions": [
    { "text": "Ação 1", "assigned_to": "João", "due_date": "2025-05-05", "completed": false }
  ]
}
```

Verificar saúde do servidor:
```
GET /health
```

Para rodar o servidor Flask separadamente:
```bash
WEBHOOK_API_KEY=sua-chave python api.py
```

---

## Deploy no Streamlit Cloud

1. Faça push do repositório para o GitHub
2. Acesse [share.streamlit.io](https://share.streamlit.io)
3. Selecione o repositório e `app.py` como entry point
4. Em **Advanced settings → Secrets**, cole o conteúdo do `secrets.toml`
5. Deploy

---

## Estrutura

```
GestorHub/
├── app.py                      # Aplicação principal (Streamlit)
├── api.py                      # Servidor webhook Flask
├── tldv_email_sync.py          # Sync via Gmail API (opcional)
├── requirements.txt            # Dependências core
├── requirements-tldv.txt       # Dependências integração Gmail
├── logo.png                    # Logo do app
├── .gitignore
└── .streamlit/
    └── secrets.toml.example    # Template de configuração
```
