# 🚀 Guia Rápido - FOTUS Auth com 2Captcha

## ⚡ Início Rápido em 5 Minutos

### 1️⃣ Instale as Dependências

```bash
pip install playwright requests
playwright install chromium
```

### 2️⃣ Configure suas Credenciais

Abra `fotus_auth_2captcha.py` e edite:

```python
# Linha 49-52
CREDENTIALS = {
    "email": "seu@email.com",        # ← SEU EMAIL
    "password": "sua_senha"           # ← SUA SENHA
}

# Linha 55
CAPTCHA_API_KEY = "sua_api_key"      # ← SUA KEY DO 2CAPTCHA
```

### 3️⃣ Execute!

```bash
python fotus_auth_2captcha.py
```

**Pronto!** O token será exibido no terminal.

---

## 📖 Exemplo de Uso em Código

```python
from fotus_auth_2captcha import FotusAuth2Captcha
import requests

# 1. Inicializa
auth = FotusAuth2Captcha()

# 2. Obtém token
token = auth.get_token()

# 3. Usa em requisições
headers = {'Authorization': f'Bearer {token}'}
response = requests.get('https://app.fotus.com.br/api/endpoint', headers=headers)

print(response.json())
```

---

## 🔑 Onde Conseguir API Key do 2Captcha?

1. Acesse: https://2captcha.com
2. Crie uma conta
3. Adicione créditos (mínimo $3)
4. Copie sua API Key em: https://2captcha.com/enterpage

---

## 💰 Quanto Custa?

- **Cloudflare Turnstile**: $2.00 por 1000 resoluções
- **Exemplo**: 100 logins = $0.20

---

## ⚙️ Opções de Linha de Comando

```bash
# Modo headless (padrão)
python fotus_auth_2captcha.py

# Mostra navegador (debug)
python fotus_auth_2captcha.py --visible

# Força novo login (ignora cache)
python fotus_auth_2captcha.py --force
```

---

## 🐛 Problemas Comuns

### ❌ "Playwright não instalado"
```bash
pip install playwright
playwright install chromium
```

### ❌ "Saldo insuficiente"
- Recarregue em: https://2captcha.com

### ❌ "Token não encontrado"
- Execute com `--visible` para ver o que acontece
- Verifique se credenciais estão corretas

---

## 📚 Documentação Completa

Veja [README.md](README.md) para documentação detalhada.

---

## 💡 Dicas

✅ **Cache automático**: Após primeiro login, token é reutilizado por horas  
✅ **Renovação automática**: Token é renovado antes de expirar  
✅ **Modo headless**: Perfeito para automação em servidores  

---

## 🎯 Próximos Passos

1. ✅ Configure suas credenciais
2. ✅ Teste o login
3. ✅ Integre em seus scripts
4. ✅ Automatize suas tarefas!

---

**Dúvidas?** Abra uma [issue](https://github.com/rbrconsult/Quebra-de-Cloudflare/issues)!
