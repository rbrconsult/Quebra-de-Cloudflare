# 🔐 FOTUS Auth - Bypass Cloudflare com 2Captcha

Sistema completo de autenticação automática para FOTUS com bypass do **Cloudflare Turnstile** usando **2Captcha**.

---

## ⭐ **VERSÃO RECOMENDADA: V3 HÍBRIDA**

**Use `fotus_auth_v3.py`** - Combina o melhor de todas as versões anteriores!

✅ **HTTPS** nas APIs (segurança)  
✅ **Anti-detecção completo** (plugins, languages, webdriver)  
✅ **wait_for_url()** nativo do Playwright  
✅ **Cria input** se não existir (mais robusto)  
✅ **CLI completo** (--balance, --clear, --visible, --force)  
✅ **Renovação automática** de token  
✅ **Cache persistente**  
✅ **Screenshots de debug** em múltiplos pontos  

---

## 🚀 Instalação Rápida

### 1. Clone o repositório
```bash
git clone https://github.com/rbrconsult/Quebra-de-Cloudflare.git
cd Quebra-de-Cloudflare
```

### 2. Instale as dependências
```bash
pip install playwright requests
playwright install chromium
```

### 3. Execute
```bash
python fotus_auth_v3.py
```

**📖 Instruções completas para Mac**: [INSTALACAO_MAC.md](INSTALACAO_MAC.md)

---

## 💻 Uso

### Standalone

```bash
# Login automático (headless)
python fotus_auth_v3.py

# Mostra navegador (debug)
python fotus_auth_v3.py --visible

# Ver saldo 2Captcha
python fotus_auth_v3.py --balance

# Limpar cache
python fotus_auth_v3.py --clear

# Forçar novo login
python fotus_auth_v3.py --force
```

### Como Módulo Python

```python
from fotus_auth_v3 import FotusAuth

# Inicializa
auth = FotusAuth()

# Obtém token (automático: cache ou login)
token = auth.get_token()

# Usa em requisições
import requests
headers = {'Authorization': f'Bearer {token}'}
response = requests.get('https://app.fotus.com.br/api/endpoint', headers=headers)
```

---

## 🔄 Fluxo de Funcionamento

```
1. 🌐 Playwright abre a página
2. 🔍 Detecta o Cloudflare Turnstile
3. 📤 Envia para 2Captcha resolver
4. ⏳ Aguarda resolução (30-120s)
5. 💉 Injeta a resposta do captcha
6. 📝 Preenche email e senha
7. 🔘 Clica no botão de login
8. ✅ Aguarda redirecionamento
9. 🎫 Extrai token JWT do localStorage
10. 💾 Salva token em cache (.fotus_token_cache.json)
```

**Renovação automática**: Token é renovado automaticamente antes de expirar!

---

## 📁 Estrutura de Arquivos

```
Quebra-de-Cloudflare/
├── fotus_auth_v3.py            # ⭐ VERSÃO RECOMENDADA (híbrida)
├── fotus_auth_2captcha.py      # Versão original Manus
├── fotus_auth.py               # Versão sem 2Captcha (referência)
├── captura_token_manual.py     # Captura manual via navegador
├── fotus_auth_renovacao.py     # Sistema de renovação
├── exemplo_uso.py              # Exemplos de uso
├── README.md                   # Esta documentação
├── INSTALACAO_MAC.md           # Instruções para Mac
├── QUICKSTART.md               # Guia rápido de 5 minutos
├── requirements.txt            # Dependências Python
└── .fotus_token_cache.json     # Cache de token (gerado automaticamente)
```

---

## 🎯 Características da V3

### **Segurança**
- ✅ HTTPS em todas as APIs
- ✅ Anti-detecção completo (webdriver, plugins, languages)
- ✅ Fingerprint realista

### **Robustez**
- ✅ Múltiplos métodos de detecção de Turnstile
- ✅ Cria input cf-turnstile-response se não existir
- ✅ Fallbacks em todos os pontos críticos
- ✅ Screenshots de debug automáticos

### **Automação**
- ✅ Renovação automática de token
- ✅ Cache persistente
- ✅ Zero interação manual necessária
- ✅ Margem de 10 minutos antes de expirar

### **Debug**
- ✅ Screenshots em pontos-chave
- ✅ Logging detalhado
- ✅ Modo visível para troubleshooting
- ✅ Limpeza automática após sucesso

---

## 💰 Custos 2Captcha

- **Cloudflare Turnstile**: ~$2.00 por 1000 resoluções
- **100 logins**: ~$0.20
- **Tempo médio**: 30-120 segundos por resolução

### Verificar Saldo

```bash
python fotus_auth_v3.py --balance
```

---

## 🐛 Troubleshooting

### ❌ "Token não encontrado"

**Solução**: Execute com `--visible` para ver o que acontece
```bash
python fotus_auth_v3.py --visible
```

### ❌ "Saldo insuficiente"

**Solução**: Recarregue em https://2captcha.com

### ❌ "Login falhou"

**Solução**: Verifique os screenshots de debug:
- `debug_01_inicial.png`
- `debug_02_pos_captcha.png`
- `debug_03_formulario.png`
- `debug_04_pos_login.png`
- `debug_erro_login.png`

---

## 📊 Cache de Token

O token é salvo em `.fotus_token_cache.json`:

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expiry": "2024-12-10T23:30:00",
  "updated": "2024-12-10T18:30:00"
}
```

### Limpar Cache

```bash
python fotus_auth_v3.py --clear
```

Ou manualmente:
```bash
rm .fotus_token_cache.json
```

---

## 🔒 Segurança

⚠️ **IMPORTANTE**:

- **Nunca commite** credenciais no Git
- Use variáveis de ambiente para dados sensíveis
- `.fotus_token_cache.json` já está no `.gitignore`
- Proteja sua API Key do 2Captcha

### Usando Variáveis de Ambiente

```python
import os

CREDENTIALS = {
    "email": os.getenv('FOTUS_EMAIL'),
    "password": os.getenv('FOTUS_PASSWORD')
}
CAPTCHA_API_KEY = os.getenv('CAPTCHA_API_KEY')
```

```bash
export FOTUS_EMAIL="seu@email.com"
export FOTUS_PASSWORD="sua_senha"
export CAPTCHA_API_KEY="sua_key"
```

---

## 📈 Performance

| Operação | Tempo |
|----------|-------|
| **Primeiro login** | 60-180 segundos (inclui 2Captcha) |
| **Logins subsequentes** | < 1 segundo (usa cache) |
| **Renovação automática** | Transparente |

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

---

## 📝 Changelog

### v3.0.0 (2024-12-10) - **HÍBRIDA OTIMIZADA**
- ✅ HTTPS nas APIs (segurança)
- ✅ Anti-detecção completo
- ✅ wait_for_url() nativo
- ✅ Cria input se não existir
- ✅ CLI completo (--balance, --clear)
- ✅ Screenshots em múltiplos pontos
- ✅ Limpeza automática de debug

### v2.0.0 (2024-12-10)
- ✅ Integração com 2Captcha
- ✅ Bypass automático do Cloudflare Turnstile

### v1.0.0 (2024-12-10)
- ✅ Cache de tokens
- ✅ Renovação automática
- ✅ Modo headless e visível
- ✅ Logging detalhado

---

## 📄 Licença

MIT License - Veja arquivo LICENSE para detalhes.

---

## 🔗 Links Úteis

- [2Captcha](https://2captcha.com) - Serviço de resolução de captchas
- [Playwright](https://playwright.dev) - Framework de automação
- [FOTUS](https://app.fotus.com.br) - Plataforma alvo

---

## ⚠️ Disclaimer

Este projeto é apenas para fins educacionais e de automação legítima. Use com responsabilidade e respeite os Termos de Serviço do FOTUS.

---

## 👤 Autor

**rbrconsult**

- GitHub: [@rbrconsult](https://github.com/rbrconsult)
- Repositório: [Quebra-de-Cloudflare](https://github.com/rbrconsult/Quebra-de-Cloudflare)

---

## 💬 Suporte

Encontrou um bug ou tem uma sugestão? Abra uma [issue](https://github.com/rbrconsult/Quebra-de-Cloudflare/issues)!

---

**⭐ Se este projeto foi útil, considere dar uma estrela no GitHub!**
