# 🍎 Instalação no Mac - FOTUS Auth V3

## 📋 Pré-requisitos

- Python 3.7+ instalado
- Git instalado
- Conexão com internet

---

## 🚀 Instalação Rápida

### 1. Clone o Repositório

```bash
cd ~/Desktop  # ou qualquer diretório de sua preferência
git clone https://github.com/rbrconsult/Quebra-de-Cloudflare.git
cd Quebra-de-Cloudflare
```

### 2. Instale as Dependências

```bash
pip3 install playwright requests
playwright install chromium
```

**Nota**: Se `pip3` não funcionar, tente `pip` ou `python3 -m pip`.

---

## ✅ Teste Rápido

### Verificar Saldo 2Captcha

```bash
python3 fotus_auth_v3.py --balance
```

**Saída esperada:**
```
💰 Saldo 2Captcha: $X.XXX
   (~XXX resoluções restantes)
```

### Primeiro Login (Modo Visível para Debug)

```bash
python3 fotus_auth_v3.py --visible
```

Isso vai:
1. ✅ Abrir navegador Chrome visível
2. ✅ Resolver Cloudflare automaticamente
3. ✅ Fazer login
4. ✅ Capturar token
5. ✅ Salvar em `.fotus_token_cache.json`

### Login Headless (Automação)

```bash
python3 fotus_auth_v3.py
```

Modo invisível, perfeito para automação!

---

## 📁 Arquivos Gerados

Após primeiro login bem-sucedido:

```
Quebra-de-Cloudflare/
├── .fotus_token_cache.json    ← TOKEN SALVO AQUI!
└── fotus_auth_v3.py
```

### Estrutura do Token Cache

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expiry": "2024-12-10T23:30:00",
  "updated": "2024-12-10T18:30:00"
}
```

---

## 🔧 Comandos Úteis

### Ver Saldo
```bash
python3 fotus_auth_v3.py --balance
```

### Limpar Cache (Forçar Novo Login)
```bash
python3 fotus_auth_v3.py --clear
```

### Forçar Novo Login (Ignorar Cache)
```bash
python3 fotus_auth_v3.py --force
```

### Debug com Navegador Visível
```bash
python3 fotus_auth_v3.py --visible
```

---

## 💻 Usar como Módulo Python

### Exemplo Básico

```python
from fotus_auth_v3 import FotusAuth

# Inicializa
auth = FotusAuth()

# Obtém token (automático: cache ou login)
token = auth.get_token()

print(f"Token: {token[:50]}...")
```

### Exemplo com Requests

```python
from fotus_auth_v3 import FotusAuth
import requests

# Obtém token
auth = FotusAuth()
token = auth.get_token()

# Usa em requisições
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

response = requests.get(
    'https://app.fotus.com.br/api/endpoint',
    headers=headers
)

print(response.json())
```

### Exemplo com Renovação Automática

```python
from fotus_auth_v3 import FotusAuth

auth = FotusAuth()

# Loop infinito - token sempre válido!
while True:
    token = auth.get_token()  # Renova automaticamente se expirado
    
    # Seu código aqui...
    fazer_scraping(token)
    
    time.sleep(3600)  # Aguarda 1 hora
```

---

## 🐛 Troubleshooting

### ❌ "Playwright não instalado"

```bash
pip3 install playwright
playwright install chromium
```

### ❌ "Saldo insuficiente"

Recarregue em: https://2captcha.com

### ❌ "Token não encontrado"

Execute com `--visible` para ver o que acontece:

```bash
python3 fotus_auth_v3.py --visible
```

Verifique os screenshots de debug:
- `debug_01_inicial.png`
- `debug_02_pos_captcha.png`
- `debug_03_formulario.png`
- `debug_04_pos_login.png`

### ❌ "Login falhou"

Verifique:
1. Credenciais corretas no código
2. Saldo 2Captcha suficiente
3. Conexão com internet estável

---

## 🔐 Segurança

### Proteger Credenciais

**Nunca commite credenciais!** Use variáveis de ambiente:

```bash
# No terminal
export FOTUS_EMAIL="seu@email.com"
export FOTUS_PASSWORD="sua_senha"
export CAPTCHA_API_KEY="sua_key"
```

Modifique o código:

```python
import os

CREDENTIALS = {
    "email": os.getenv('FOTUS_EMAIL', 'gabriel@evolveenergia.com.br'),
    "password": os.getenv('FOTUS_PASSWORD', 'container1')
}

CAPTCHA_API_KEY = os.getenv('CAPTCHA_API_KEY', '801e53e81ceea1b0b287a1a128231d00')
```

---

## 📊 Performance

| Operação | Tempo |
|----------|-------|
| **Primeiro login** | 60-180s (inclui 2Captcha) |
| **Login com cache** | < 1s |
| **Renovação automática** | Transparente |

---

## ✅ Checklist de Instalação

- [ ] Python 3.7+ instalado
- [ ] Git instalado
- [ ] Repositório clonado
- [ ] Dependências instaladas (`playwright`, `requests`)
- [ ] Chromium instalado (`playwright install chromium`)
- [ ] Saldo 2Captcha verificado
- [ ] Primeiro login testado com `--visible`
- [ ] Token salvo em `.fotus_token_cache.json`
- [ ] Teste de renovação automática OK

---

## 🎯 Próximos Passos

Após instalação bem-sucedida:

1. ✅ Integrar no seu scraper
2. ✅ Configurar renovação automática
3. ✅ Testar em produção
4. ✅ Monitorar logs

---

## 💬 Suporte

Problemas? Abra uma [issue](https://github.com/rbrconsult/Quebra-de-Cloudflare/issues)!

---

**Boa sorte! 🚀**
