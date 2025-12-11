#!/usr/bin/env python3
"""
🔐 FOTUS Manual Login - Captura automática de token
===================================================

Este script abre o navegador para você fazer login MANUALMENTE.
Após o login, ele captura automaticamente o token JWT e salva em cache.

✅ 100% confiável - Você faz login real
✅ Sem 2Captcha - Sem custos
✅ Token salvo automaticamente
✅ Renovação automática quando expirar

Uso:
    python3 fotus_manual_login.py

Você verá:
1. Navegador abre na página de login
2. Você preenche email/senha MANUALMENTE
3. Você resolve o Cloudflare MANUALMENTE
4. Você clica "Entrar" MANUALMENTE
5. Script detecta redirecionamento para /home
6. Script captura token automaticamente
7. Token salvo em .fotus_token_cache.json
8. Navegador fecha

Próximas vezes:
- Use fotus_get_token.py para obter token do cache
- Renove manualmente quando expirar (script avisa)
"""

import json
import time
import logging
import sys
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    print("❌ Playwright não instalado!")
    print("   Instale com: pip install playwright")
    print("   Depois: playwright install chromium")
    sys.exit(1)

LOGIN_URL = "https://app.fotus.com.br/login"
TOKEN_CACHE_FILE = ".fotus_token_cache.json"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def decode_jwt_expiry(token: str) -> Optional[datetime]:
    """Decodifica data de expiração do JWT"""
    try:
        payload = token.split('.')[1]
        payload += '=' * (4 - len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
        return datetime.fromtimestamp(data['exp'])
    except:
        return None


def extract_token(page) -> Optional[str]:
    """Extrai token JWT do localStorage"""
    try:
        logger.info("🔍 Procurando token no localStorage...")
        
        storage = page.evaluate('''() => {
            let result = {};
            for (let i = 0; i < localStorage.length; i++) {
                let key = localStorage.key(i);
                result[key] = localStorage.getItem(key);
            }
            return result;
        }''')
        
        # Procura em chaves conhecidas
        known_keys = ['token', 'authToken', 'jwt', 'access_token', 'accessToken', 'auth']
        for key in known_keys:
            if key in storage and storage[key]:
                val = storage[key]
                if isinstance(val, str) and val.startswith('eyJ'):
                    logger.info(f"   📍 Encontrado em '{key}'")
                    return val
        
        # Procura em qualquer chave que contenha JWT
        for key, val in storage.items():
            if not val:
                continue
            if isinstance(val, str) and val.startswith('eyJ') and val.count('.') >= 2:
                logger.info(f"   📍 Encontrado em '{key}'")
                return val
            
            # Tenta parsear como JSON
            try:
                data = json.loads(val)
                if isinstance(data, dict):
                    for k, v in data.items():
                        if isinstance(v, str) and v.startswith('eyJ') and v.count('.') >= 2:
                            logger.info(f"   📍 Encontrado em '{key}.{k}'")
                            return v
            except:
                pass
        
        logger.error("❌ Token não encontrado no localStorage")
        return None
        
    except Exception as e:
        logger.error(f"❌ Erro ao extrair token: {e}")
        return None


def save_cache(token: str, expiry: datetime):
    """Salva token em cache"""
    try:
        Path(TOKEN_CACHE_FILE).write_text(json.dumps({
            'token': token,
            'expiry': expiry.isoformat(),
            'updated': datetime.now().isoformat()
        }, indent=2))
        logger.info(f"💾 Token salvo em {TOKEN_CACHE_FILE}")
        logger.info(f"   Expira em: {expiry.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"   Válido por: {(expiry - datetime.now()).seconds // 3600}h {((expiry - datetime.now()).seconds % 3600) // 60}min")
    except Exception as e:
        logger.error(f"❌ Erro ao salvar cache: {e}")


def manual_login():
    """Abre navegador para login manual e captura token"""
    
    print("\n" + "="*60)
    print("🔐 FOTUS MANUAL LOGIN")
    print("="*60)
    print()
    print("📋 INSTRUÇÕES:")
    print("   1. O navegador vai abrir na página de login")
    print("   2. Preencha seu email e senha MANUALMENTE")
    print("   3. Resolva o Cloudflare Turnstile MANUALMENTE")
    print("   4. Clique em 'Entrar' MANUALMENTE")
    print("   5. Aguarde redirecionamento para /home")
    print("   6. O script captura o token AUTOMATICAMENTE")
    print("   7. Navegador fecha automaticamente")
    print()
    print("⏰ Tempo máximo: 5 minutos")
    print("="*60)
    print()
    
    input("Pressione ENTER para abrir o navegador...")
    
    logger.info("🌐 Abrindo navegador...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # SEMPRE visível para login manual
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
            ]
        )
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='pt-BR',
        )
        
        page = context.new_page()
        
        logger.info(f"📄 Acessando {LOGIN_URL}...")
        page.goto(LOGIN_URL, wait_until='domcontentloaded', timeout=60000)
        
        logger.info("⏳ Aguardando você fazer login...")
        logger.info("   👉 Preencha email, senha e resolva Cloudflare")
        logger.info("   👉 Clique em 'Entrar'")
        
        # Aguarda redirecionamento para /home (máximo 5 minutos)
        try:
            logger.info("⏰ Aguardando redirecionamento para /home (máx 5 min)...")
            page.wait_for_url('**/home**', timeout=300000)  # 5 minutos
            logger.info("✅ Redirecionado para /home!")
            
        except Exception as e:
            logger.error(f"❌ Timeout ou erro: {e}")
            logger.error("   Você não foi redirecionado para /home")
            logger.error("   Verifique se o login foi bem-sucedido")
            browser.close()
            return False
        
        # Aguarda um pouco para garantir que token foi salvo
        time.sleep(3)
        
        # Extrai token
        token = extract_token(page)
        
        browser.close()
        
        if not token:
            logger.error("❌ Não foi possível capturar o token")
            logger.error("   O token pode não estar no localStorage")
            return False
        
        # Decodifica expiração
        expiry = decode_jwt_expiry(token)
        if not expiry:
            logger.warning("⚠️ Não foi possível decodificar expiração")
            logger.warning("   Usando 5 horas como padrão")
            expiry = datetime.now() + timedelta(hours=5)
        
        # Salva cache
        save_cache(token, expiry)
        
        print()
        print("="*60)
        print("✅ SUCESSO!")
        print("="*60)
        print(f"Token: {token[:50]}...")
        print(f"Expira: {expiry.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        print()
        print("💡 Próximos passos:")
        print("   - Use: python3 fotus_get_token.py")
        print("   - Para obter token do cache")
        print("   - Renove quando expirar (script avisa)")
        print()
        
        return True


def main():
    try:
        success = manual_login()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Cancelado pelo usuário")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
