#!/usr/bin/env python3
"""
🔐 FOTUS AUTH - Login Automático com 2Captcha
==============================================

Sistema completo de autenticação no FOTUS com bypass do Cloudflare Turnstile
usando serviço 2Captcha para resolver o desafio automaticamente.

FLUXO:
------
1. Playwright abre a página de login
2. Detecta o Cloudflare Turnstile
3. Envia para 2Captcha resolver
4. Injeta a resposta do captcha
5. Login completa automaticamente
6. Captura o token JWT

USO STANDALONE:
---------------
python fotus_auth_2captcha.py                    # Login automático
python fotus_auth_2captcha.py --visible          # Mostra navegador
python fotus_auth_2captcha.py --force            # Força novo login

USO COMO MÓDULO:
----------------
from fotus_auth_2captcha import FotusAuth2Captcha

auth = FotusAuth2Captcha(
    email="seu@email.com",
    password="sua_senha",
    captcha_api_key="sua_key_2captcha"
)
token = auth.login()
print(token)

REQUISITOS:
-----------
pip install playwright requests
playwright install chromium
"""

import json
import time
import logging
import argparse
import base64
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("❌ Playwright não instalado!")
    print("   pip install playwright")
    print("   playwright install chromium")

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================

# Credenciais FOTUS
CREDENTIALS = {
    "email": "gabriel@evolveenergia.com.br",
    "password": "container1"
}

# API Key 2Captcha
CAPTCHA_API_KEY = "801e53e81ceea1b0b287a1a128231d00"

# URLs
LOGIN_URL = "https://app.fotus.com.br/login"
HOME_URL = "https://app.fotus.com.br/home"
TOKEN_CACHE_FILE = ".fotus_token_cache.json"

# 2Captcha API
CAPTCHA_API_URL = "https://2captcha.com"
CAPTCHA_SUBMIT_URL = f"{CAPTCHA_API_URL}/in.php"
CAPTCHA_RESULT_URL = f"{CAPTCHA_API_URL}/res.php"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# ==============================================================================
# CLASSE 2CAPTCHA
# ==============================================================================

class TwoCaptchaSolver:
    """Cliente para resolver Cloudflare Turnstile via 2Captcha"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def solve_turnstile(self, sitekey: str, page_url: str, timeout: int = 120) -> Optional[str]:
        """
        Resolve Cloudflare Turnstile
        
        Args:
            sitekey: Site key do Turnstile
            page_url: URL da página
            timeout: Timeout em segundos
            
        Returns:
            Token de resposta do captcha ou None
        """
        logger.info("🔐 Enviando Turnstile para 2Captcha...")
        logger.info(f"   Site Key: {sitekey[:30]}...")
        logger.info(f"   URL: {page_url}")
        
        # 1. Submete captcha
        try:
            submit_data = {
                'key': self.api_key,
                'method': 'turnstile',
                'sitekey': sitekey,
                'pageurl': page_url,
                'json': 1
            }
            
            response = requests.post(CAPTCHA_SUBMIT_URL, data=submit_data, timeout=30)
            result = response.json()
            
            if result.get('status') != 1:
                error = result.get('request', 'Erro desconhecido')
                logger.error(f"   ❌ Erro ao submeter: {error}")
                return None
            
            captcha_id = result.get('request')
            logger.info(f"   ✅ Captcha submetido! ID: {captcha_id}")
            
        except Exception as e:
            logger.error(f"   ❌ Erro na submissão: {e}")
            return None
        
        # 2. Aguarda resolução
        logger.info("   ⏳ Aguardando resolução (pode levar até 2 minutos)...")
        
        start_time = time.time()
        check_interval = 5  # Verifica a cada 5 segundos
        
        while time.time() - start_time < timeout:
            time.sleep(check_interval)
            
            try:
                result_data = {
                    'key': self.api_key,
                    'action': 'get',
                    'id': captcha_id,
                    'json': 1
                }
                
                response = requests.get(CAPTCHA_RESULT_URL, params=result_data, timeout=30)
                result = response.json()
                
                if result.get('status') == 1:
                    # Resolvido!
                    token = result.get('request')
                    elapsed = int(time.time() - start_time)
                    logger.info(f"   ✅ Captcha resolvido em {elapsed}s!")
                    return token
                
                elif result.get('request') == 'CAPCHA_NOT_READY':
                    # Ainda processando
                    elapsed = int(time.time() - start_time)
                    logger.info(f"   ⏳ Processando... ({elapsed}s)")
                    continue
                
                else:
                    # Erro
                    error = result.get('request', 'Erro desconhecido')
                    logger.error(f"   ❌ Erro: {error}")
                    return None
                    
            except Exception as e:
                logger.warning(f"   ⚠️ Erro ao verificar status: {e}")
                continue
        
        logger.error("   ❌ Timeout aguardando resolução do captcha")
        return None
    
    def get_balance(self) -> Optional[float]:
        """Retorna saldo da conta 2Captcha"""
        try:
            response = requests.get(
                CAPTCHA_RESULT_URL,
                params={'key': self.api_key, 'action': 'getbalance', 'json': 1},
                timeout=10
            )
            result = response.json()
            
            if result.get('status') == 1:
                return float(result.get('request', 0))
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao obter saldo: {e}")
        
        return None


# ==============================================================================
# CLASSE DE AUTENTICAÇÃO
# ==============================================================================

class FotusAuth2Captcha:
    """Gerencia autenticação FOTUS com bypass de Cloudflare via 2Captcha"""
    
    def __init__(
        self,
        email: str = None,
        password: str = None,
        captcha_api_key: str = None,
        headless: bool = True
    ):
        self.email = email or CREDENTIALS['email']
        self.password = password or CREDENTIALS['password']
        self.captcha_api_key = captcha_api_key or CAPTCHA_API_KEY
        self.headless = headless
        
        self.token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        
        self.captcha_solver = TwoCaptchaSolver(self.captcha_api_key)
        
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
        Faz login no FOTUS com bypass de Cloudflare
        
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
        logger.info("🌐 INICIANDO LOGIN AUTOMÁTICO COM 2CAPTCHA")
        logger.info("="*60)
        logger.info(f"   Modo: {'Headless' if self.headless else 'Visível'}")
        logger.info(f"   Email: {self.email}")
        
        # Verifica saldo 2Captcha
        balance = self.captcha_solver.get_balance()
        if balance is not None:
            logger.info(f"   💰 Saldo 2Captcha: ${balance:.2f}")
            if balance < 0.01:
                logger.warning("   ⚠️ Saldo baixo! Recarregue em: https://2captcha.com")
        
        try:
            with sync_playwright() as p:
                # ============================================
                # 1. LANÇA NAVEGADOR
                # ============================================
                logger.info("\n1️⃣ Iniciando navegador...")
                
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--window-size=1920,1080',
                    ]
                )
                
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    locale='pt-BR',
                    timezone_id='America/Sao_Paulo',
                )
                
                # Anti-detecção
                context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    window.chrome = { runtime: {} };
                """)
                
                page = context.new_page()
                
                # ============================================
                # 2. ACESSA PÁGINA
                # ============================================
                logger.info("\n2️⃣ Acessando página de login...")
                page.goto(LOGIN_URL, wait_until='domcontentloaded')
                time.sleep(3)
                
                # ============================================
                # 3. DETECTA E RESOLVE TURNSTILE
                # ============================================
                logger.info("\n3️⃣ Detectando Cloudflare Turnstile...")
                
                # Procura iframe do Turnstile
                turnstile_iframe = page.query_selector('iframe[src*="challenges.cloudflare.com"]')
                
                if turnstile_iframe:
                    logger.info("   ✅ Turnstile detectado!")
                    
                    # Extrai sitekey do HTML
                    html = page.content()
                    sitekey = None
                    
                    # Tenta diferentes métodos para extrair sitekey
                    # Método 1: Procura no HTML
                    if 'data-sitekey' in html:
                        import re
                        match = re.search(r'data-sitekey=["\']([^"\']+)["\']', html)
                        if match:
                            sitekey = match.group(1)
                    
                    # Método 2: Procura no script
                    if not sitekey:
                        match = re.search(r'sitekey["\']?\s*[:=]\s*["\']([^"\']+)["\']', html)
                        if match:
                            sitekey = match.group(1)
                    
                    # Método 3: Extrai do iframe
                    if not sitekey:
                        iframe_src = turnstile_iframe.get_attribute('src')
                        if iframe_src and 'sitekey=' in iframe_src:
                            match = re.search(r'sitekey=([^&]+)', iframe_src)
                            if match:
                                sitekey = match.group(1)
                    
                    if not sitekey:
                        logger.error("   ❌ Não foi possível extrair sitekey!")
                        page.screenshot(path='debug_turnstile.png')
                        logger.info("   📸 Screenshot salvo: debug_turnstile.png")
                        browser.close()
                        return None
                    
                    logger.info(f"   🔑 Sitekey: {sitekey[:30]}...")
                    
                    # Resolve via 2Captcha
                    captcha_response = self.captcha_solver.solve_turnstile(sitekey, LOGIN_URL)
                    
                    if not captcha_response:
                        logger.error("   ❌ Falha ao resolver Turnstile")
                        browser.close()
                        return None
                    
                    # Injeta resposta do captcha
                    logger.info("   💉 Injetando resposta do captcha...")
                    
                    page.evaluate(f"""
                        (response) => {{
                            // Procura callback do Turnstile
                            if (window.turnstile) {{
                                window.turnstile.reset();
                            }}
                            
                            // Injeta resposta
                            const input = document.querySelector('input[name="cf-turnstile-response"]');
                            if (input) {{
                                input.value = response;
                            }}
                            
                            // Dispara evento
                            const event = new Event('change', {{ bubbles: true }});
                            if (input) input.dispatchEvent(event);
                        }}
                    """, captcha_response)
                    
                    time.sleep(2)
                    logger.info("   ✅ Captcha injetado!")
                    
                else:
                    logger.info("   ℹ️ Turnstile não detectado (pode já ter passado)")
                
                # ============================================
                # 4. FAZ LOGIN
                # ============================================
                logger.info("\n4️⃣ Fazendo login...")
                
                time.sleep(2)
                
                # Preenche email
                email_selectors = [
                    'input[type="email"]',
                    'input[formcontrolname="email"]',
                    'input[name="email"]',
                    '#email',
                ]
                
                email_input = None
                for selector in email_selectors:
                    email_input = page.query_selector(selector)
                    if email_input:
                        logger.info(f"   📧 Campo email: {selector}")
                        break
                
                if not email_input:
                    page.screenshot(path='debug_login.png')
                    logger.error("   ❌ Campo de email não encontrado")
                    browser.close()
                    return None
                
                email_input.click()
                email_input.fill(self.email)
                time.sleep(0.5)
                
                # Preenche senha
                password_selectors = [
                    'input[type="password"]',
                    'input[formcontrolname="password"]',
                    'input[name="password"]',
                    '#password',
                ]
                
                password_input = None
                for selector in password_selectors:
                    password_input = page.query_selector(selector)
                    if password_input:
                        logger.info(f"   🔑 Campo senha: {selector}")
                        break
                
                if not password_input:
                    page.screenshot(path='debug_login.png')
                    logger.error("   ❌ Campo de senha não encontrado")
                    browser.close()
                    return None
                
                password_input.click()
                password_input.fill(self.password)
                time.sleep(0.5)
                
                # Clica botão login
                button_selectors = [
                    'button[type="submit"]',
                    'button:has-text("Entrar")',
                    'button:has-text("Login")',
                ]
                
                login_button = None
                for selector in button_selectors:
                    try:
                        login_button = page.query_selector(selector)
                        if login_button and login_button.is_visible():
                            logger.info(f"   🔘 Botão: {selector}")
                            break
                    except:
                        continue
                
                if login_button:
                    login_button.click()
                else:
                    logger.info("   ⌨️ Usando Enter")
                    password_input.press('Enter')
                
                # ============================================
                # 5. AGUARDA REDIRECIONAMENTO
                # ============================================
                logger.info("\n5️⃣ Aguardando login...")
                
                for i in range(20):
                    time.sleep(1)
                    current_url = page.url
                    
                    if '/home' in current_url or '/dashboard' in current_url:
                        logger.info(f"   ✅ Login OK! URL: {current_url}")
                        break
                    
                    if i % 3 == 0:
                        logger.info(f"   ⏳ Aguardando... ({current_url})")
                else:
                    page.screenshot(path='debug_after_login.png')
                    logger.error("   ❌ Login não completou")
                    browser.close()
                    return None
                
                # ============================================
                # 6. EXTRAI TOKEN
                # ============================================
                logger.info("\n6️⃣ Extraindo token JWT...")
                
                time.sleep(2)
                
                token_keys = [
                    'token', 'accessToken', 'access_token',
                    'authToken', 'auth_token', 'jwt',
                ]
                
                token = None
                for key in token_keys:
                    value = page.evaluate(f'localStorage.getItem("{key}")')
                    if value and value.startswith('eyJ'):
                        token = value
                        logger.info(f"   🎫 Token em: {key}")
                        break
                
                if not token:
                    # Busca em todo localStorage
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
                    
                    for key, value in all_storage.items():
                        if value and isinstance(value, str) and value.startswith('eyJ'):
                            token = value
                            logger.info(f"   🎫 Token em: {key}")
                            break
                
                browser.close()
                
                if not token:
                    logger.error("   ❌ Token não encontrado")
                    return None
                
                # Salva token
                self.token = token
                self.token_expiry = self._decode_jwt_expiry(token)
                
                if self.token_expiry:
                    logger.info(f"   📅 Expira: {self.token_expiry.strftime('%d/%m/%Y %H:%M')}")
                else:
                    self.token_expiry = datetime.now() + timedelta(hours=5)
                
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


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description='FOTUS Auth com 2Captcha')
    parser.add_argument('--visible', action='store_true', help='Mostra navegador')
    parser.add_argument('--force', action='store_true', help='Força novo login')
    args = parser.parse_args()
    
    auth = FotusAuth2Captcha(headless=not args.visible)
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
