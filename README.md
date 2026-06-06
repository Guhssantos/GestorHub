# GestorHub

Centro de Comando Executivo — agenda Microsoft 365, resumos de reuniões via tl;dv e chamados via Power BI em um único painel.

## Pré-requisitos

- Python 3.11+
- Conta Microsoft 365 com permissões `User.Read` e `Calendars.ReadWrite`
- App registrado no Azure AD (para obter `AZURE_CLIENT_ID` e `AZURE_CLIENT_SECRET`)

## Instalação

```bash
pip install -r requirements.txt
```

## Configuração

Crie o arquivo `.streamlit/secrets.toml` (nunca commitar):

```toml
AZURE_CLIENT_ID     = "seu-client-id"
AZURE_CLIENT_SECRET = "seu-client-secret"
REDIRECT_URI        = "https://seu-app.streamlit.app"
POWER_BI_URL        = "https://app.powerbi.com/reportEmbed?..."
```

## Executar

**Painel principal (Streamlit):**

```bash
streamlit run app.py
```

**Servidor de webhook tl;dv (Flask):**

```bash
python api.py
```

O webhook fica disponível em `POST http://localhost:5000/webhook/tldv`.

### Payload esperado pelo webhook

```json
{
  "title":   "Nome da reunião",
  "date":    "2025-05-01T10:30:00",
  "summary": "Resumo gerado pelo tl;dv",
  "url":     "https://tldv.io/...",
  "actions": ["Ação 1", "Ação 2"]
}
```

`title`, `date` e `summary` são obrigatórios. Campos ausentes retornam HTTP 400.
