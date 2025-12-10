#!/usr/bin/env python3
"""
🔐 FOTUS AUTH - Login Automático com Bypass Cloudflare
======================================================

Módulo separado para autenticação no FOTUS.
Usa Playwright para passar pelo Cloudflare JS Challenge.

Uso standalone:
    python fotus_auth.py                    # Login headless
    python fotus_auth.py --visible          # Mostra navegador
    python fotus_auth.py --force            # Força novo login

Uso como módulo:
    from fotus_auth import FotusAuth
    
    auth = FotusAuth(headless=True)
    token = auth.login()
    print(token)

Requisitos:
    pip install playwright
    playwright install chromium
"""

import json
import time
import logging
import argparse
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("❌ Playwright não instalado!")
    print("   Instale com:")
    print("   pip install playwright")
    print("   playwright install chromium")

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================

CREDENTIALS = {
    "email": "gabriel@evolveenergia.com.br",
    "password": "container1"
}

LOGIN_URL = "https://app.fotus.com.br/login"
HOME_URL = "https://app.fotus.com.br/home"
TOKEN_CACHE_FILE = ".fotus_token_cache.json"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# ==============================================================================
# CLASSE DE AUTENTICAÇÃO
# ==============================================================================

class FotusAuth:
    """Gerencia autenticação via Playwright com bypass do Cloudflare"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        self._load_cached_token()
    
    def _load_cached_token(self):
        """Carrega token do cache se ainda válido"""
        if Path(TOKEN_CACHE_FILE).exists():
            try:
                with open(TOKEN_CACHE_FILE, 'r') as f:
                    cache = json.load(f)
                expiry = datetime.fromisoformat(cache['expiry'])
                if expiry > datetime.now():
                    self.token = cache['token']
                    self.token_expiry = expiry
                    minutos = (expiry - datetime.now()).seconds // 60
                    logger.info(f"🔑 Token em cache válido (expira em {minutos} min)")
                else:
                    logger.info("⏰ Token em cache expirado")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao carregar cache: {e}")
    
    def _save_token_cache(self):
        """Salva token no cache"""
        if self.token and self.token_expiry:
            try:
                with open(TOKEN_CACHE_FILE, 'w') as f:
                    json.dump({
                        'token': self.token,
                        'expiry': self.token_expiry.isoformat()
                    }, f)
                logger.info(f"💾 Token salvo em cache")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao salvar cache: {e}")
    
    def _decode_jwt_expiry(self, token: str) -> Optional[datetime]:
        """Extrai data de expiração do JWT"""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None
            payload = parts[1]
            # Padding para base64
            payload += '=' * (4 - len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload)
            data = json.loads(decoded)
            exp = data.get('exp')
            if exp:
                return datetime.fromtimestamp(exp)
        except Exception as e:
            logger.warning(f"⚠️ Erro ao decodificar JWT: {e}")
        return None
    
    def is_token_valid(self) -> bool:
        """Verifica se token atual é válido (com margem de 10 min)"""
        if not self.token or not self.token_expiry:
            return False
        return self.token_expiry > datetime.now() + timedelta(minutes=10)
    
    def get_token(self) -> Optional[str]:
        """Retorna token válido (do cache ou faz login)"""
        if self.is_token_valid():
            return self.token
        return self.login(force=True)
    
    def login(self, force: bool = False) -> Optional[str]:
        """
        Faz login no FOTUS e retorna token JWT.
        
        Args:
            force: Se True, ignora cache e faz novo login
            
        Returns:
            Token JWT ou None se falhar
        """
        # Verifica cache
        if not force and self.is_token_valid():
            logger.info("✅ Usando token em cache")
            return self.token
        
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("❌ Playwright não disponível!")
            return None
        
        logger.info("="*60)
        logger.info("🌐 INICIANDO LOGIN AUTOMÁTICO")
        logger.info("="*60)
        logger.info(f"   Modo: {'Headless' if self.headless else 'Visível'}")
        logger.info(f"   Email: {CREDENTIALS['email']}")
        
        try:
            with sync_playwright() as p:
                # ============================================
                # 1. LANÇA NAVEGADOR COM STEALTH
                # ============================================
                logger.info("\n1️⃣ Iniciando navegador...")
                
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-infobars',
                        '--window-size=1920,1080',
                    ]
                )
                
                # Contexto com fingerprint realista
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    locale='pt-BR',
                    timezone_id='America/Sao_Paulo',
                )
                
                # Script para ocultar automação
                context.add_init_script("""
                    // Remove flag webdriver
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    
                    // Simula Chrome real
                    window.chrome = { runtime: {} };
                    
                    // Plugins falsos
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                    
                    // Languages
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['pt-BR', 'pt', 'en-US', 'en']
                    });
                """)
                
                page = context.new_page()
                
                # ============================================
                # 2. ACESSA PÁGINA E PASSA PELO CLOUDFLARE
                # ============================================
                logger.info("\n2️⃣ Acessando página de login...")
                page.goto(LOGIN_URL, wait_until='domcontentloaded')
                
                # Espera Cloudflare resolver (máx 30s)
                logger.info("   ⏳ Aguardando Cloudflare...")
                
                cloudflare_passed = False
                for i in range(30):
                    time.sleep(1)
                    
                    # Verifica se ainda está no Cloudflare
                    html = page.content().lower()
                    if 'checking your browser' in html or 'cloudflare' in html:
                        if i % 5 == 0:
                            logger.info(f"   ⏳ Cloudflare... ({i}s)")
                        continue
                    
                    # Verifica se chegou na página de login
                    if page.query_selector('input[type="email"]') or \
                       page.query_selector('input[formcontrolname="email"]') or \
                       page.query_selector('input[name="email"]'):
                        cloudflare_passed = True
                        break
                    
                    # Verifica se já está logado
                    if '/home' in page.url or '/dashboard' in page.url:
                        cloudflare_passed = True
                        logger.info("   ✅ Já estava logado!")
                        break
                
                if not cloudflare_passed:
                    logger.error("   ❌ Timeout esperando Cloudflare")
                    browser.close()
                    return None
                
                logger.info("   ✅ Cloudflare passou!")
                
                # ============================================
                # 3. FAZ LOGIN
                # ============================================
                logger.info("\n3️⃣ Fazendo login...")
                
                # Aguarda campos carregarem
                time.sleep(2)
                
                # Tenta diferentes seletores para email
                email_selectors = [
                    'input[type="email"]',
                    'input[formcontrolname="email"]',
                    'input[name="email"]',
                    'input[placeholder*="email" i]',
                    'input[placeholder*="e-mail" i]',
                    '#email',
                ]
                
                email_input = None
                for selector in email_selectors:
                    email_input = page.query_selector(selector)
                    if email_input:
                        logger.info(f"   📧 Campo email: {selector}")
                        break
                
                if not email_input:
                    # Debug: salva screenshot
                    page.screenshot(path='debug_login_page.png')
                    logger.error("   ❌ Campo de email não encontrado")
                    logger.error("   📸 Screenshot salvo: debug_login_page.png")
                    browser.close()
                    return None
                
                # Preenche email
                email_input.click()
                email_input.fill(CREDENTIALS['email'])
                time.sleep(0.5)
                
                # Tenta diferentes seletores para senha
                password_selectors = [
                    'input[type="password"]',
                    'input[formcontrolname="password"]',
                    'input[formcontrolname="senha"]',
                    'input[name="password"]',
                    'input[name="senha"]',
                    '#password',
                    '#senha',
                ]
                
                password_input = None
                for selector in password_selectors:
                    password_input = page.query_selector(selector)
                    if password_input:
                        logger.info(f"   🔑 Campo senha: {selector}")
                        break
                
                if not password_input:
                    page.screenshot(path='debug_login_page.png')
                    logger.error("   ❌ Campo de senha não encontrado")
                    browser.close()
                    return None
                
                # Preenche senha
                password_input.click()
                password_input.fill(CREDENTIALS['password'])
                time.sleep(0.5)
                
                # Clica no botão de login
                button_selectors = [
                    'button[type="submit"]',
                    'button:has-text("Entrar")',
                    'button:has-text("Login")',
                    'button:has-text("Acessar")',
                    'input[type="submit"]',
                    '.btn-login',
                    '#btn-login',
                ]
                
                login_button = None
                for selector in button_selectors:
                    try:
                        login_button = page.query_selector(selector)
                        if login_button and login_button.is_visible():
                            logger.info(f"   🔘 Botão login: {selector}")
                            break
                    except:
                        continue
                
                if login_button:
                    login_button.click()
                else:
                    # Tenta Enter como fallback
                    logger.info("   ⌨️ Usando Enter para submeter")
                    password_input.press('Enter')
                
                # ============================================
                # 4. AGUARDA REDIRECIONAMENTO E CAPTURA TOKEN
                # ============================================
                logger.info("\n4️⃣ Aguardando login...")
                
                # Espera redirecionamento (máx 15s)
                for i in range(15):
                    time.sleep(1)
                    current_url = page.url
                    
                    if '/home' in current_url or '/dashboard' in current_url or '/painel' in current_url:
                        logger.info(f"   ✅ Login OK! Redirecionado para: {current_url}")
                        break
                    
                    if i % 3 == 0:
                        logger.info(f"   ⏳ Aguardando... ({current_url})")
                else:
                    # Verifica se teve erro de login
                    html = page.content().lower()
                    if 'senha' in html and 'inválid' in html:
                        logger.error("   ❌ Senha inválida!")
                    elif 'email' in html and 'inválid' in html:
                        logger.error("   ❌ Email inválido!")
                    else:
                        page.screenshot(path='debug_after_login.png')
                        logger.error("   ❌ Login não completou")
                        logger.error("   📸 Screenshot salvo: debug_after_login.png")
                    browser.close()
                    return None
                
                # ============================================
                # 5. EXTRAI TOKEN DO LOCALSTORAGE
                # ============================================
                logger.info("\n5️⃣ Extraindo token JWT...")
                
                time.sleep(2)  # Aguarda SPA carregar
                
                # Tenta diferentes chaves de localStorage
                token_keys = [
                    'token',
                    'accessToken',
                    'access_token',
                    'authToken',
                    'auth_token',
                    'jwt',
                    'jwtToken',
                    'user_token',
                    'fotus_token',
                ]
                
                token = None
                for key in token_keys:
                    value = page.evaluate(f'localStorage.getItem("{key}")')
                    if value and value.startswith('eyJ'):
                        token = value
                        logger.info(f"   🎫 Token encontrado em: {key}")
                        break
                
                # Se não achou, tenta pegar todo localStorage
                if not token:
                    all_storage = page.evaluate('''
                        () => {
                            let items = {};
                            for (let i = 0; i < localStorage.length; i++) {
                                let key = localStorage.key(i);
                                items[key] = localStorage.getItem(key);
                            }
                            return items;
                        }
                    ''')
                    
                    logger.info(f"   📦 Chaves no localStorage: {list(all_storage.keys())}")
                    
                    # Procura qualquer valor que pareça JWT
                    for key, value in all_storage.items():
                        if value and isinstance(value, str) and value.startswith('eyJ'):
                            token = value
                            logger.info(f"   🎫 Token JWT encontrado em: {key}")
                            break
                        # Tenta parsear JSON
                        if value and isinstance(value, str):
                            try:
                                data = json.loads(value)
                                if isinstance(data, dict):
                                    for k, v in data.items():
                                        if isinstance(v, str) and v.startswith('eyJ'):
                                            token = v
                                            logger.info(f"   🎫 Token em {key}.{k}")
                                            break
                            except:
                                pass
                        if token:
                            break
                
                browser.close()
                
                if not token:
                    logger.error("   ❌ Token não encontrado no localStorage")
                    return None
                
                # ============================================
                # 6. SALVA TOKEN
                # ============================================
                self.token = token
                self.token_expiry = self._decode_jwt_expiry(token)
                
                if self.token_expiry:
                    logger.info(f"   📅 Expira em: {self.token_expiry.strftime('%d/%m/%Y %H:%M')}")
                else:
                    # Assume 5 horas se não conseguir decodificar
                    self.token_expiry = datetime.now() + timedelta(hours=5)
                    logger.info("   📅 Expiração assumida: 5 horas")
                
                self._save_token_cache()
                
                logger.info("\n" + "="*60)
                logger.info("🎉 LOGIN CONCLUÍDO COM SUCESSO!")
                logger.info("="*60)
                logger.info(f"   Token: {token[:50]}...")
                
                return token
                
        except Exception as e:
            logger.error(f"❌ Erro no login: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def clear_cache(self):
        """Remove token do cache"""
        self.token = None
        self.token_expiry = None
        if Path(TOKEN_CACHE_FILE).exists():
            Path(TOKEN_CACHE_FILE).unlink()
            logger.info("🗑️ Cache removido")


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description='FOTUS Auth - Login Automático')
    parser.add_argument('--visible', action='store_true', help='Mostra navegador (não headless)')
    parser.add_argument('--force', action='store_true', help='Força novo login (ignora cache)')
    parser.add_argument('--clear', action='store_true', help='Limpa cache do token')
    args = parser.parse_args()
    
    auth = FotusAuth(headless=not args.visible)
    
    if args.clear:
        auth.clear_cache()
        return
    
    token = auth.login(force=args.force)
    
    if token:
        print("\n" + "="*60)
        print("TOKEN JWT:")
        print("="*60)
        print(token)
        print("="*60)
    else:
        print("\n❌ Falha ao obter token")
        exit(1)


if __name__ == "__main__":
    main()
