# 🔐 FOTUS Login Manual - Método 100% Confiável

## 📋 Visão Geral

Este método é **100% confiável** porque você faz login **manualmente** e o script apenas captura o token automaticamente.

✅ **Sem 2Captcha** - Sem custos  
✅ **Sem bloqueios** - Login real  
✅ **Token salvo** - Reutilizável  
✅ **Renovação simples** - 1 comando  

---

## 🚀 Uso Rápido

### **1. Login Manual (primeira vez ou quando expirar)**

```bash
python3 fotus_manual_login.py
```

**O que acontece:**
1. Navegador abre na página de login
2. Você preenche email/senha **manualmente**
3. Você resolve Cloudflare **manualmente**
4. Você clica "Entrar" **manualmente**
5. Script detecta redirecionamento
6. Script captura token **automaticamente**
7. Token salvo em `.fotus_token_cache.json`

**Tempo:** ~30 segundos (depende de você)

---

### **2. Obter Token do Cache**

```bash
python3 fotus_get_token.py
```

**Saída:**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

### **3. Verificar Validade**

```bash
python3 fotus_get_token.py --check
```

**Saída:**
```
✅ Token válido
   Expira em: 2024-12-11 18:30:00
   Restam: 4h 23min
```

---

### **4. Obter JSON Completo**

```bash
python3 fotus_get_token.py --json
```

**Saída:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expiry": "2024-12-11T18:30:00",
  "updated": "2024-12-11T14:07:00",
  "valid": true,
  "remaining_seconds": 15780
}
```

---

## 💻 Integração em Código Python

### **Exemplo 1: Simples**

```python
import subprocess

# Obtém token
result = subprocess.run(
    ['python3', 'fotus_get_token.py'],
    capture_output=True,
    text=True
)

if result.returncode == 0:
    token = result.stdout.strip()
    print(f"Token: {token}")
else:
    print("Token expirado, renove com: python3 fotus_manual_login.py")
```

### **Exemplo 2: Com requests**

```python
import subprocess
import requests

def get_fotus_token():
    result = subprocess.run(
        ['python3', 'fotus_get_token.py'],
        capture_output=True,
        text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None

# Usar em requisições
token = get_fotus_token()
if token:
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get("https://api.fotus.com.br/endpoint", headers=headers)
    print(response.json())
else:
    print("❌ Token inválido, renove!")
```

### **Exemplo 3: Importando diretamente**

```python
from fotus_get_token import get_token, get_cache_info

# Obter apenas token
token = get_token()
if token:
    print(f"Token: {token}")

# Obter informações completas
info = get_cache_info()
if info and info['valid']:
    print(f"Token válido por mais {info['remaining_hours']}h")
    token = info['token']
else:
    print("Token expirado!")
```

---

## 🔄 Renovação Automática

### **Script de Verificação e Renovação**

Crie `check_and_renew.sh`:

```bash
#!/bin/bash

# Verifica se token é válido
python3 fotus_get_token.py --check > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "❌ Token expirado, renovando..."
    python3 fotus_manual_login.py
else
    echo "✅ Token válido"
fi
```

Torne executável:
```bash
chmod +x check_and_renew.sh
```

Execute:
```bash
./check_and_renew.sh
```

---

## 📊 Estrutura de Arquivos

```
Quebra-de-Cloudflare/
├── fotus_manual_login.py       # Login manual + captura
├── fotus_get_token.py           # Obtém token do cache
├── .fotus_token_cache.json      # Cache do token (gerado)
└── README_MANUAL.md             # Esta documentação
```

---

## ⏰ Validade do Token

- **Duração típica:** 4-8 horas
- **Renovação:** Execute `fotus_manual_login.py` novamente
- **Frequência:** 1-2x por dia (depende do FOTUS)

---

## 🎯 Vantagens vs Automação 2Captcha

| Aspecto | Manual | 2Captcha |
|---------|--------|----------|
| **Confiabilidade** | ✅ 100% | ⚠️ 60-80% |
| **Custo** | ✅ Grátis | ❌ $0.003/login |
| **Velocidade** | ⚠️ 30s (você) | ✅ 60-120s (auto) |
| **Bloqueios** | ✅ Zero | ❌ Frequentes |
| **Manutenção** | ✅ Simples | ❌ Complexa |

---

## 🐛 Troubleshooting

### **Token não encontrado**

```bash
❌ Token não encontrado no localStorage
```

**Solução:**
- Verifique se você realmente fez login
- Aguarde redirecionamento para `/home`
- O FOTUS pode estar salvando token em outro lugar

### **Timeout**

```bash
❌ Timeout ou erro
```

**Solução:**
- Você tem 5 minutos para fazer login
- Se demorar mais, execute novamente

### **Cache corrompido**

```bash
❌ Erro ao ler cache
```

**Solução:**
```bash
rm .fotus_token_cache.json
python3 fotus_manual_login.py
```

---

## 📞 Suporte

Se tiver problemas:
1. Verifique se Playwright está instalado
2. Verifique se Chromium foi baixado
3. Execute com `--help` para ver opções

---

## 🎉 Pronto!

Agora você tem um sistema **100% confiável** para obter tokens do FOTUS!

**Próximos passos:**
1. Execute `python3 fotus_manual_login.py`
2. Faça login manualmente
3. Use `python3 fotus_get_token.py` em seus scripts
4. Renove quando expirar

**Simples, confiável, sem bloqueios! 🚀**
