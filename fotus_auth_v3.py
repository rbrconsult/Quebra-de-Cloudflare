#!/usr/bin/env python3
"""
🔐 FOTUS AUTH V3 - HÍBRIDO OTIMIZADO
====================================

Combina o melhor do Manus (robustez) + Claude (eficiência).

✅ HTTPS nas APIs (segurança)
✅ Anti-detecção completo (plugins, languages, webdriver)
✅ wait_for_url() nativo do Playwright
✅ Cria input cf-turnstile-response se não existir
✅ CLI completo (--balance, --clear, --visible, --force)
✅ Renovação automática de token
✅ Cache persistente

Uso:
    python fotus_auth_v3.py                # Login automático
    python fotus_auth_v3.py --visible      # Debug com navegador visível
    python fotus_auth_v3.py --balance      # Ver saldo 2Captcha
    python fotus_auth_v3.py --clear        # Limpar cache
    python fotus_auth_v3.py --force        # Forçar novo login

Como módulo:
    from fotus_auth_v3 import FotusAuth
    
    auth = FotusAuth()
    token = auth.get_token()  # Automático: cache ou login
    
Requisitos:
    pip install playwright requests
    playwright install chromium
"""

import json
import time
import logging
import argparse
import sys
import base64
import re
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️ Instale: pip install playwright && playwright install chromium")

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================

CREDENTIALS = {
    "email": "gabriel@evolveenergia.com.br",
    "password": "container1"
}

CAPTCHA_API_KEY = "801e53e81ceea1b0b287a1a128231d00"

LOGIN_URL = "https://app.fotus.com.br/login"
TOKEN_CACHE_FILE = ".fotus_token_cache.json"

# URLs 2Captcha com HTTPS (segurança)
CAPTCHA_IN_URL = "https://2captcha.com/in.php"
CAPTCHA_RES_URL = "https://2captcha.com/res.php"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# ==============================================================================
# 2CAPTCHA SOLVER
# ==============================================================================

class TurnstileSolver:
    """Resolve Cloudflare Turnstile via 2Captcha (HTTPS)"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def solve(self, site_key: str, page_url: str, timeout: int = 120) -> Optional[str]:
        """
        Resolve Turnstile e retorna token.
        
        Args:
            site_key: Sitekey do Turnstile
            page_url: URL da página
            timeout: Timeout em segundos
            
        Returns:
            Token de resposta ou None
        """
        logger.info("🔄 Enviando Turnstile para 2Captcha...")
        logger.info(f"   SiteKey: {site_key[:30]}...")
        
        # 1. Envia captcha
        try:
            resp = requests.post(CAPTCHA_IN_URL, data={
                "key": self.api_key,
                "method": "turnstile",
                "sitekey": site_key,
                "pageurl": page_url,
                "json": 1
            }, timeout=30)
            
            result = resp.json()
            if result.get("status") != 1:
                error = result.get('request', 'Erro desconhecido')
                logger.error(f"❌ 2Captcha erro: {error}")
                return None
            
            task_id = result["request"]
            logger.info(f"   ✅ Task ID: {task_id}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao enviar: {e}")
            return None
        
        # 2. Aguarda resolução (polling)
        logger.info("⏳ Resolvendo (30-60s)...")
        start = time.time()
        
        while time.time() - start < timeout:
            time.sleep(5)
            
            try:
                resp = requests.get(CAPTCHA_RES_URL, params={
                    "key": self.api_key,
                    "action": "get",
                    "id": task_id,
                    "json": 1
                }, timeout=30)
                
                result = resp.json()
                
                if result.get("status") == 1:
                    token = result["request"]
                    logger.info("   ✅ Captcha resolvido!")
                    return token
                
                status = result.get("request", "")
                if status != "CAPCHA_NOT_READY":
                    logger.error(f"❌ Erro: {status}")
                    return None
                
                elapsed = int(time.time() - start)
                logger.info(f"   ⏳ Aguardando... {elapsed}s")
                
            except Exception as e:
                logger.warning(f"⚠️ Erro polling: {e}")
        
        logger.error("❌ Timeout 2Captcha")
        return None
    
    def get_balance(self) -> float:
        """Retorna saldo da conta 2Captcha"""
        try:
            resp = requests.get(CAPTCHA_RES_URL, params={
                "key": self.api_key,
                "action": "getbalance",
                "json": 1
            }, timeout=10)
            result = resp.json()
            if result.get("status") == 1:
                return float(result["request"])
        except Exception as e:
            logger.warning(f"⚠️ Erro ao obter saldo: {e}")
        return 0.0


# ==============================================================================
# AUTENTICAÇÃO FOTUS
# ==============================================================================

class FotusAuth:
    """
    Autenticação automática no FOTUS com 2Captcha.
    
    Funcionalidades:
    - Bypass Cloudflare Turnstile via 2Captcha
    - Cache persistente de token
    - Renovação automática quando expira
    - Anti-detecção completo
    """
    
    def __init__(self, headless: bool = True):
        """
        Args:
            headless: True para navegador invisível, False para debug
        """
        self.headless = headless
        self.token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        self.solver = TurnstileSolver(CAPTCHA_API_KEY)
        self._load_cache()
    
    # ==========================================================================
    # CACHE
    # ==========================================================================
    
    def _load_cache(self):
        """Carrega token do cache se válido"""
        if not Path(TOKEN_CACHE_FILE).exists():
            return
            
        try:
            cache = json.loads(Path(TOKEN_CACHE_FILE).read_text())
            expiry = datetime.fromisoformat(cache['expiry'])
            
            # Válido se expira em mais de 10 minutos
            if expiry > datetime.now() + timedelta(minutes=10):
                self.token = cache['token']
                self.token_expiry = expiry
                mins = (expiry - datetime.now()).seconds // 60
                logger.info(f"🔑 Token do cache válido ({mins} min restantes)")
            else:
                logger.info("⏰ Token do cache expirado")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao carregar cache: {e}")
    
    def _save_cache(self):
        """Salva token no cache"""
        if not self.token or not self.token_expiry:
            return
            
        try:
            Path(TOKEN_CACHE_FILE).write_text(json.dumps({
                'token': self.token,
                'expiry': self.token_expiry.isoformat(),
                'updated': datetime.now().isoformat()
            }, indent=2))
            logger.info("💾 Token salvo em cache")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao salvar cache: {e}")
    
    def clear_cache(self):
        """Limpa cache do token"""
        self.token = None
        self.token_expiry = None
        Path(TOKEN_CACHE_FILE).unlink(missing_ok=True)
        logger.info("🗑️ Cache limpo")
    
    # ==========================================================================
    # JWT
    # ==========================================================================
    
    def _decode_jwt_expiry(self, token: str) -> Optional[datetime]:
        """Extrai data de expiração do JWT"""
        try:
            payload = token.split('.')[1]
            payload += '=' * (4 - len(payload) % 4)
            data = json.loads(base64.urlsafe_b64decode(payload))
            return datetime.fromtimestamp(data['exp'])
        except Exception:
            return None
    
    def is_token_valid(self) -> bool:
        """Verifica se token é válido (com margem de 10 min)"""
        if not self.token or not self.token_expiry:
            return False
        return self.token_expiry > datetime.now() + timedelta(minutes=10)
    
    # ==========================================================================
    # API PÚBLICA
    # ==========================================================================
    
    def get_token(self) -> Optional[str]:
        """
        Retorna token válido (automático).
        
        - Se cache válido: retorna do cache
        - Se expirado: faz login automático
        
        Returns:
            Token JWT ou None
        """
        if self.is_token_valid():
            return self.token
        return self.login()
    
    def login(self, force: bool = False) -> Optional[str]:
        """
        Faz login no FOTUS com resolução automática do Turnstile.
        
        Args:
            force: Se True, ignora cache
            
        Returns:
            Token JWT ou None
        """
        # Usa cache se válido
        if not force and self.is_token_valid():
            logger.info("✅ Usando token do cache")
            return self.token
        
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("❌ Playwright não instalado!")
            return None
        
        # Verifica saldo
        balance = self.solver.get_balance()
        logger.info(f"💰 Saldo 2Captcha: ${balance:.3f}")
        if balance < 0.003:  # ~1 resolução custa $0.002-0.003
            logger.error("❌ Saldo 2Captcha insuficiente!")
            return None
        
        logger.info("="*60)
        logger.info("🌐 INICIANDO LOGIN AUTOMÁTICO")
        logger.info("="*60)
        logger.info(f"   Email: {CREDENTIALS['email']}")
        logger.info(f"   Modo: {'Headless' if self.headless else 'Visível'}")
        
        try:
            with sync_playwright() as p:
                # 1. Lança navegador com anti-detecção
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
                
                # 2. Contexto com fingerprint realista
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    locale='pt-BR',
                    timezone_id='America/Sao_Paulo',
                )
                
                # 3. Anti-detecção completo (Manus)
                context.add_init_script("""
                    // Remove webdriver flag
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    
                    // Simula Chrome real
                    window.chrome = { runtime: {} };
                    
                    // Plugins falsos
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                    
                    // Languages brasileiras
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['pt-BR', 'pt', 'en-US', 'en']
                    });
                    
                    // Permissions
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );
                """)
                
                page = context.new_page()
                
                # 4. Acessa página de login
                logger.info("📄 Acessando página de login...")
                page.goto(LOGIN_URL, wait_until='networkidle', timeout=60000)
                time.sleep(2)
                
                # 5. Screenshot inicial (debug)
                page.screenshot(path='debug_01_inicial.png')
                
                # 6. Detecta e resolve Turnstile
                logger.info("🔍 Procurando Turnstile...")
                site_key = self._find_turnstile_sitekey(page)
                
                if site_key:
                    logger.info(f"   ✅ Turnstile encontrado: {site_key[:30]}...")
                    
                    # Resolve via 2Captcha
                    captcha_token = self.solver.solve(site_key, LOGIN_URL)
                    
                    if captcha_token:
                        logger.info("💉 Injetando resposta do captcha...")
                        self._inject_turnstile_response(page, captcha_token)
                        time.sleep(2)
                        page.screenshot(path='debug_02_pos_captcha.png')
                    else:
                        logger.warning("⚠️ Falha ao resolver captcha, tentando continuar...")
                else:
                    logger.info("   ℹ️ Turnstile não detectado, continuando...")
                
                # 7. Preenche formulário
                logger.info("📝 Preenchendo formulário...")
                
                # Espera campos carregarem
                page.wait_for_selector('input', timeout=10000)
                time.sleep(1)
                
                # Email
                email_filled = False
                for selector in ['input[type="email"]', 'input[name="email"]', 'input[placeholder*="mail" i]', '#email']:
                    el = page.query_selector(selector)
                    if el:
                        el.click()
                        time.sleep(0.2)
                        el.fill(CREDENTIALS['email'])
                        email_filled = True
                        logger.info(f"   ✅ Email preenchido ({selector})")
                        break
                
                if not email_filled:
                    page.screenshot(path='debug_erro_email.png')
                    logger.error("❌ Campo de email não encontrado!")
                    browser.close()
                    return None
                
                time.sleep(0.3)
                
                # Senha
                password_filled = False
                for selector in ['input[type="password"]', 'input[name="password"]', 'input[name="senha"]']:
                    el = page.query_selector(selector)
                    if el:
                        el.click()
                        time.sleep(0.2)
                        el.fill(CREDENTIALS['password'])
                        password_filled = True
                        logger.info(f"   ✅ Senha preenchida ({selector})")
                        break
                
                if not password_filled:
                    logger.error("❌ Campo de senha não encontrado!")
                    browser.close()
                    return None
                
                time.sleep(0.5)
                page.screenshot(path='debug_03_formulario.png')
                
                # 8. Submit
                logger.info("🔘 Clicando em Entrar...")
                button_clicked = False
                for selector in ['button[type="submit"]', 'button:has-text("Entrar")', 'button:has-text("Login")', 'button:has-text("Acessar")']:
                    btn = page.query_selector(selector)
                    if btn:
                        btn.click()
                        button_clicked = True
                        break
                
                if not button_clicked:
                    # Fallback: Enter
                    page.keyboard.press('Enter')
                
                # 9. Aguarda redirecionamento (Playwright nativo)
                logger.info("⏳ Aguardando login completar...")
                try:
                    page.wait_for_url('**/home**', timeout=30000)
                    logger.info("   ✅ Redirecionado para /home!")
                except:
                    time.sleep(5)
                    current_url = page.url.lower()
                    if 'login' in current_url:
                        page.screenshot(path='debug_erro_login.png')
                        logger.error("❌ Login falhou! Ver: debug_erro_login.png")
                        browser.close()
                        return None
                    elif 'home' in current_url or 'dashboard' in current_url:
                        logger.info("   ✅ Login OK!")
                    else:
                        logger.warning(f"   ⚠️ URL inesperada: {page.url}")
                
                page.screenshot(path='debug_04_pos_login.png')
                
                # 10. Extrai token do localStorage
                logger.info("🔍 Extraindo token JWT...")
                token = self._extract_jwt_token(page)
                
                browser.close()
                
                if not token:
                    logger.error("❌ Token JWT não encontrado no localStorage!")
                    return None
                
                # 11. Salva
                self.token = token
                self.token_expiry = self._decode_jwt_expiry(token)
                if not self.token_expiry:
                    self.token_expiry = datetime.now() + timedelta(hours=5)
                    logger.info("   ⚠️ Expiração não detectada, assumindo 5h")
                
                self._save_cache()
                
                # Limpa screenshots de debug em caso de sucesso
                for f in Path('.').glob('debug_*.png'):
                    f.unlink(missing_ok=True)
                
                logger.info("="*60)
                logger.info(f"✅ LOGIN COMPLETO!")
                logger.info(f"   Token: {self.token[:50]}...")
                logger.info(f"   Expira: {self.token_expiry}")
                logger.info("="*60)
                
                return self.token
                
        except Exception as e:
            logger.error(f"❌ Erro no login: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    # ==========================================================================
    # HELPERS PRIVADOS
    # ==========================================================================
    
    def _find_turnstile_sitekey(self, page) -> Optional[str]:
        """Encontra sitekey do Cloudflare Turnstile"""
        
        # Método 1: Atributo data-sitekey direto
        el = page.query_selector('[data-sitekey]')
        if el:
            key = el.get_attribute('data-sitekey')
            if key:
                return key
        
        # Método 2: iframe do Cloudflare
        for frame in page.frames:
            if 'challenges.cloudflare.com' in frame.url:
                match = re.search(r'sitekey=([^&]+)', frame.url)
                if match:
                    return match.group(1)
        
        # Método 3: Regex no HTML
        html = page.content()
        patterns = [
            r'data-sitekey=["\']([0-9a-zA-Z_-]+)["\']',
            r'sitekey["\s:]+["\']([0-9a-zA-Z_-]+)["\']',
            r'turnstile.*?sitekey["\s:]+["\']([0-9a-zA-Z_-]+)["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _inject_turnstile_response(self, page, token: str):
        """Injeta resposta do Turnstile na página"""
        page.evaluate(f'''() => {{
            // Preenche inputs existentes
            document.querySelectorAll('input[name="cf-turnstile-response"], input[name="g-recaptcha-response"]')
                .forEach(input => {{ input.value = "{token}"; }});
            
            // Cria input se não existir (Claude)
            let existing = document.querySelector('input[name="cf-turnstile-response"]');
            if (!existing) {{
                let input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'cf-turnstile-response';
                input.value = "{token}";
                let form = document.querySelector('form');
                if (form) form.appendChild(input);
            }}
            
            // Tenta callback do Turnstile
            if (window.turnstile) {{
                try {{
                    if (typeof window.turnstile.callback === 'function') {{
                        window.turnstile.callback("{token}");
                    }}
                }} catch(e) {{}}
            }}
            
            // Dispara eventos
            document.querySelectorAll('input[name="cf-turnstile-response"]').forEach(input => {{
                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }});
        }}''')
    
    def _extract_jwt_token(self, page) -> Optional[str]:
        """Extrai token JWT do localStorage"""
        
        # Busca todo localStorage
        try:
            storage = page.evaluate('''() => {
                let items = {};
                for (let i = 0; i < localStorage.length; i++) {
                    let key = localStorage.key(i);
                    items[key] = localStorage.getItem(key);
                }
                return items;
            }''')
            
            # Procura JWT (formato: xxx.yyy.zzz)
            for key, val in storage.items():
                if not val or not isinstance(val, str):
                    continue
                
                # JWT direto
                if val.count('.') == 2 and len(val) > 50:
                    # Verifica se começa com eyJ (base64 de {")
                    if val.startswith('eyJ') or val.strip('"').startswith('eyJ'):
                        logger.info(f"   ✅ Token encontrado em: {key}")
                        return val.strip('"')
                
                # JWT dentro de JSON
                if '{' in val:
                    try:
                        data = json.loads(val)
                        if isinstance(data, dict):
                            for k, v in data.items():
                                if isinstance(v, str) and v.count('.') == 2 and len(v) > 50:
                                    if v.startswith('eyJ') or v.strip('"').startswith('eyJ'):
                                        logger.info(f"   ✅ Token encontrado em: {key}.{k}")
                                        return v.strip('"')
                    except:
                        pass
            
        except Exception as e:
            logger.error(f"Erro ao extrair token: {e}")
        
        return None


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description='FOTUS Auth V3 - Login Automático')
    parser.add_argument('--visible', action='store_true', help='Mostra navegador (debug)')
    parser.add_argument('--force', action='store_true', help='Força novo login')
    parser.add_argument('--clear', action='store_true', help='Limpa cache')
    parser.add_argument('--balance', action='store_true', help='Mostra saldo 2Captcha')
    args = parser.parse_args()
    
    # Comando: saldo
    if args.balance:
        solver = TurnstileSolver(CAPTCHA_API_KEY)
        balance = solver.get_balance()
        print(f"💰 Saldo 2Captcha: ${balance:.3f}")
        print(f"   (~{int(balance / 0.003)} resoluções restantes)")
        return
    
    auth = FotusAuth(headless=not args.visible)
    
    # Comando: limpar cache
    if args.clear:
        auth.clear_cache()
        return
    
    # Comando: login
    token = auth.login(force=args.force)
    
    if token:
        print("\n" + "="*60)
        print("✅ TOKEN JWT OBTIDO:")
        print("="*60)
        print(token[:80] + "...")
        print("="*60)
        print(f"Expira em: {auth.token_expiry}")
        print(f"Cache: {TOKEN_CACHE_FILE}")
        print("\nUso no scraper:")
        print("  from fotus_auth_v3 import FotusAuth")
        print("  token = FotusAuth().get_token()")
    else:
        print("\n❌ Falha no login")
        print("   Verifique os arquivos debug_*.png")
        sys.exit(1)


if __name__ == "__main__":
    main()