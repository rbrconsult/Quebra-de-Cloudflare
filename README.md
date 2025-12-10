# 🔐 FOTUS Auth - Bypass Cloudflare com 2Captcha

Sistema completo de autenticação automática para FOTUS com bypass do **Cloudflare Turnstile** usando **2Captcha**.

## 🎯 Características

✅ **Bypass automático do Cloudflare Turnstile**  
✅ **Integração com 2Captcha** para resolver desafios  
✅ **Cache inteligente de tokens** (evita logins desnecessários)  
✅ **Renovação automática** quando token expira  
✅ **Modo headless** para automação completa  
✅ **Modo visível** para debug  
✅ **Extração automática de JWT** do localStorage  
✅ **Logging detalhado** de todo o processo  

---

## 📋 Requisitos

### Software
- Python 3.7+
- Playwright
- Requests

### Serviços
- Conta no [2Captcha](https://2captcha.com) com saldo

---

## 🚀 Instalação

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

### 3. Configure suas credenciais

Edite o arquivo `fotus_auth_2captcha.py` e atualize:

```python
# Credenciais FOTUS
CREDENTIALS = {
    "email": "seu@email.com",
    "password": "sua_senha"
}

# API Key 2Captcha
CAPTCHA_API_KEY = "sua_api_key_aqui"
```

---

## 💻 Uso

### Uso Standalone

```bash
# Login automático (headless)
python fotus_auth_2captcha.py

# Mostra navegador (debug)
python fotus_auth_2captcha.py --visible

# Força novo login (ignora cache)
python fotus_auth_2captcha.py --force
```

### Uso como Módulo Python

```python
from fotus_auth_2captcha import FotusAuth2Captcha

# Inicializa
auth = FotusAuth2Captcha(
    email="seu@email.com",
    password="sua_senha",
    captcha_api_key="sua_key_2captcha",
    headless=True
)

# Obtém token (usa cache se válido, senão faz login)
token = auth.get_token()

# Usa token em requisições
import requests
headers = {'Authorization': f'Bearer {token}'}
response = requests.get('https://app.fotus.com.br/api/endpoint', headers=headers)
```

### Exemplos Completos

Veja o arquivo `exemplo_uso.py` para exemplos detalhados:

```bash
python exemplo_uso.py
```

---

## 🔄 Fluxo de Funcionamento

```
1. 🌐 Playwright abre a página de login
2. 🔍 Detecta o Cloudflare Turnstile
3. 📤 Envia desafio para 2Captcha resolver
4. ⏳ Aguarda resolução (30-120 segundos)
5. 💉 Injeta resposta do captcha na página
6. 📝 Preenche email e senha
7. 🔘 Clica no botão de login
8. ✅ Aguarda redirecionamento
9. 🎫 Extrai token JWT do localStorage
10. 💾 Salva token em cache
```

---

## 📁 Estrutura de Arquivos

```
Quebra-de-Cloudflare/
├── fotus_auth_2captcha.py      # ⭐ Script principal com 2Captcha
├── fotus_auth.py               # Script original (sem 2Captcha)
├── captura_token_manual.py     # Captura manual via navegador
├── fotus_auth_renovacao.py     # Sistema de renovação automática
├── exemplo_uso.py              # Exemplos de uso
├── README.md                   # Esta documentação
├── requirements.txt            # Dependências Python
└── .fotus_token_cache.json     # Cache de token (gerado automaticamente)
```

---

## 🔧 Configuração Avançada

### Timeout do Captcha

Por padrão, aguarda até 120 segundos para resolver o captcha. Para alterar:

```python
captcha_response = self.captcha_solver.solve_turnstile(
    sitekey, 
    LOGIN_URL,
    timeout=180  # 3 minutos
)
```

### Margem de Renovação

Token é renovado 30 minutos antes de expirar. Para alterar:

```python
# Em fotus_auth_renovacao.py
RENEWAL_MARGIN_MINUTES = 60  # Renova 1 hora antes
```

### Endpoints da API

Ajuste as URLs conforme necessário:

```python
LOGIN_URL = "https://app.fotus.com.br/login"
API_BASE_URL = "https://app.fotus.com.br/api"
```

---

## 💰 Custos 2Captcha

- **Cloudflare Turnstile**: ~$2.00 por 1000 resoluções
- **Tempo médio**: 30-120 segundos por resolução
- **Recarregue em**: https://2captcha.com

### Verificar Saldo

```python
from fotus_auth_2captcha import TwoCaptchaSolver

solver = TwoCaptchaSolver("sua_api_key")
balance = solver.get_balance()
print(f"Saldo: ${balance:.2f}")
```

---

## 🐛 Troubleshooting

### ❌ "Token não encontrado"

**Causa**: Token não está no localStorage  
**Solução**: 
1. Execute com `--visible` para ver o que acontece
2. Verifique se login foi bem-sucedido
3. Verifique se está sendo redirecionado para /home ou /dashboard

### ❌ "Sitekey não encontrado"

**Causa**: Não conseguiu extrair sitekey do Turnstile  
**Solução**:
1. Screenshot é salvo automaticamente em `debug_turnstile.png`
2. Verifique se o Cloudflare está ativo
3. Tente executar com `--visible` para debug

### ❌ "Timeout esperando Cloudflare"

**Causa**: 2Captcha demorou muito ou falhou  
**Solução**:
1. Verifique saldo do 2Captcha
2. Aumente o timeout
3. Tente novamente (pode ser instabilidade temporária)

### ❌ "Campo de email não encontrado"

**Causa**: Seletores CSS mudaram  
**Solução**:
1. Execute com `--visible` para ver a página
2. Inspecione os campos e atualize os seletores no código
3. Veja screenshot em `debug_login.png`

---

## 📊 Cache de Token

O token é salvo em `.fotus_token_cache.json`:

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expiry": "2024-12-10T20:30:00",
  "refresh_token": "...",
  "updated_at": "2024-12-10T15:30:00"
}
```

### Limpar Cache

```bash
rm .fotus_token_cache.json
```

---

## 🔒 Segurança

⚠️ **IMPORTANTE**:

- **Nunca commite** credenciais no Git
- Use variáveis de ambiente para dados sensíveis
- Adicione `.fotus_token_cache.json` ao `.gitignore`
- Proteja sua API Key do 2Captcha

### Usando Variáveis de Ambiente

```python
import os

auth = FotusAuth2Captcha(
    email=os.getenv('FOTUS_EMAIL'),
    password=os.getenv('FOTUS_PASSWORD'),
    captcha_api_key=os.getenv('CAPTCHA_API_KEY')
)
```

```bash
export FOTUS_EMAIL="seu@email.com"
export FOTUS_PASSWORD="sua_senha"
export CAPTCHA_API_KEY="sua_key"
```

---

## 📈 Performance

- **Primeiro login**: 60-180 segundos (inclui resolução do captcha)
- **Logins subsequentes**: < 1 segundo (usa cache)
- **Renovação automática**: Transparente para o usuário

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

### v1.0.0 (2024-12-10)
- ✅ Integração com 2Captcha
- ✅ Bypass automático do Cloudflare Turnstile
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
