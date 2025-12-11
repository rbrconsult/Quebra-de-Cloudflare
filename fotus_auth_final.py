#!/usr/bin/env python3
"""
🔐 FOTUS AUTH FINAL - Turnstile pós-submit
==========================================

Fluxo correto:
1. Preenche formulário
2. Clica Entrar
3. Turnstile aparece
4. 2Captcha resolve
5. Injeta resposta
6. Submete novamente
7. Login completa

Uso:
    python fotus_auth_final.py              # Login automático
    python fotus_auth_final.py --visible    # Debug
    python fotus_auth_final.py --balance    # Saldo 2Captcha
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
    print("⚠️ pip install playwright && playwright install chromium")

# ==============================================================================
# CONFIG
# ==============================================================================

CREDENTIALS = {
    "email": "gabriel@evolveenergia.com.br",
    "password": "container1"
}

CAPTCHA_API_KEY = "801e53e81ceea1b0b287a1a128231d00"
LOGIN_URL = "https://app.fotus.com.br/login"
TOKEN_CACHE_FILE = ".fotus_token_cache.json"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# ==============================================================================
# 2CAPTCHA
# ==============================================================================

class TurnstileSolver:
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def solve(self, site_key: str, page_url: str, timeout: int = 120) -> Optional[str]:
        logger.info(f"🔄 2Captcha: enviando Turnstile...")
        
        try:
            resp = requests.post("https://2captcha.com/in.php", data={
                "key": self.api_key,
                "method": "turnstile",
                "sitekey": site_key,
                "pageurl": page_url,
                "json": 1
            }, timeout=30)
            
            result = resp.json()
            if result.get("status") != 1:
                logger.error(f"❌ Erro: {result.get('request')}")
                return None
            
            task_id = result["request"]
            logger.info(f"   Task: {task_id}")
        except Exception as e:
            logger.error(f"❌ {e}")
            return None
        
        logger.info("⏳ Resolvendo...")
        start = time.time()
        
        while time.time() - start < timeout:
            time.sleep(5)
            try:
                resp = requests.get("https://2captcha.com/res.php", params={
                    "key": self.api_key, "action": "get", "id": task_id, "json": 1
                }, timeout=30)
                result = resp.json()
                
                if result.get("status") == 1:
                    logger.info("   ✅ Resolvido!")
                    return result["request"]
                
                if result.get("request") != "CAPCHA_NOT_READY":
                    logger.error(f"❌ {result.get('request')}")
                    return None
                
                logger.info(f"   ⏳ {int(time.time()-start)}s...")
            except:
                pass
        
        return None
    
    def get_balance(self) -> float:
        try:
            resp = requests.get("https://2captcha.com/res.php", 
                params={"key": self.api_key, "action": "getbalance", "json": 1}, timeout=10)
            if resp.json().get("status") == 1:
                return float(resp.json()["request"])
        except:
            pass
        return 0.0


# ==============================================================================
# AUTH
# ==============================================================================

class FotusAuth:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.token = None
        self.token_expiry = None
        self.solver = TurnstileSolver(CAPTCHA_API_KEY)
        self._load_cache()
    
    def _load_cache(self):
        if Path(TOKEN_CACHE_FILE).exists():
            try:
                cache = json.loads(Path(TOKEN_CACHE_FILE).read_text())
                expiry = datetime.fromisoformat(cache['expiry'])
                if expiry > datetime.now() + timedelta(minutes=10):
                    self.token = cache['token']
                    self.token_expiry = expiry
                    logger.info(f"🔑 Cache válido ({(expiry - datetime.now()).seconds // 60} min)")
            except:
                pass
    
    def _save_cache(self):
        if self.token and self.token_expiry:
            Path(TOKEN_CACHE_FILE).write_text(json.dumps({
                'token': self.token,
                'expiry': self.token_expiry.isoformat()
            }, indent=2))
            logger.info("💾 Cache salvo")
    
    def _jwt_expiry(self, token: str) -> Optional[datetime]:
        try:
            payload = token.split('.')[1]
            payload += '=' * (4 - len(payload) % 4)
            data = json.loads(base64.urlsafe_b64decode(payload))
            return datetime.fromtimestamp(data['exp'])
        except:
            return None
    
    def is_valid(self) -> bool:
        return self.token and self.token_expiry and self.token_expiry > datetime.now() + timedelta(minutes=10)
    
    def get_token(self) -> Optional[str]:
        return self.token if self.is_valid() else self.login()
    
    def _find_sitekey(self, page) -> Optional[str]:
        # 1. Atributo direto
        el = page.query_selector('[data-sitekey]')
        if el:
            return el.get_attribute('data-sitekey')
        
        # 2. iframe Cloudflare
        for frame in page.frames:
            if 'challenges.cloudflare.com' in frame.url:
                match = re.search(r'sitekey=([^&]+)', frame.url)
                if match:
                    return match.group(1)
        
        # 3. Regex no HTML
        html = page.content()
        match = re.search(r'data-sitekey=["\']([0-9a-zA-Z_-]+)["\']', html)
        if match:
            return match.group(1)
        
        return None
    
    def _inject_response(self, page, token: str):
        page.evaluate(f'''() => {{
            // Preenche inputs existentes
            document.querySelectorAll('input[name="cf-turnstile-response"]')
                .forEach(i => i.value = "{token}");
            
            // Cria se não existir
            if (!document.querySelector('input[name="cf-turnstile-response"]')) {{
                let input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'cf-turnstile-response';
                input.value = "{token}";
                document.querySelector('form')?.appendChild(input);
            }}
            
            // Callback do Turnstile
            if (window.turnstile?.callback) {{
                try {{ window.turnstile.callback("{token}"); }} catch(e) {{}}
            }}
            
            // Eventos
            document.querySelectorAll('input[name="cf-turnstile-response"]')
                .forEach(i => i.dispatchEvent(new Event('change', {{bubbles: true}})));
        }}''')
    
    def _extract_token(self, page) -> Optional[str]:
        try:
            storage = page.evaluate('''() => {
                let r = {};
                for (let i = 0; i < localStorage.length; i++) {
                    let k = localStorage.key(i);
                    r[k] = localStorage.getItem(k);
                }
                return r;
            }''')
            
            for key, val in storage.items():
                if not val:
                    continue
                
                # JWT direto
                if isinstance(val, str) and val.count('.') == 2 and len(val) > 50 and val.startswith('eyJ'):
                    logger.info(f"   📍 {key}")
                    return val.strip('"')
                
                # Dentro de JSON
                if '{' in str(val):
                    try:
                        data = json.loads(val)
                        if isinstance(data, dict):
                            for k, v in data.items():
                                if isinstance(v, str) and v.count('.') == 2 and v.startswith('eyJ'):
                                    logger.info(f"   📍 {key}.{k}")
                                    return v
                    except:
                        pass
        except:
            pass
        return None
    
    def login(self, force: bool = False) -> Optional[str]:
        if not force and self.is_valid():
            return self.token
        
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("❌ Playwright não instalado!")
            return None
        
        balance = self.solver.get_balance()
        logger.info(f"💰 Saldo 2Captcha: ${balance:.3f}")
        if balance < 0.003:
            logger.error("❌ Saldo insuficiente!")
            return None
        
        logger.info("="*60)
        logger.info("🌐 LOGIN AUTOMÁTICO")
        logger.info("="*60)
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
                )
                
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    locale='pt-BR',
                )
                
                context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    window.chrome = { runtime: {} };
                    Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['pt-BR', 'pt', 'en']});
                """)
                
                page = context.new_page()
                
                # 1. Acessa
                logger.info("📄 Acessando...")
                page.goto(LOGIN_URL, wait_until='domcontentloaded', timeout=60000)
                time.sleep(2)
                
                # 2. Preenche
                logger.info("📝 Preenchendo...")
                page.wait_for_selector('input', timeout=10000)
                
                page.query_selector('input[type="email"]').fill(CREDENTIALS['email'])
                time.sleep(0.3)
                page.query_selector('input[type="password"]').fill(CREDENTIALS['password'])
                time.sleep(0.5)
                
                # 3. Submit
                logger.info("🔘 Clicando Entrar...")
                btn = page.query_selector('button[type="submit"]')
                if btn:
                    btn.click()
                else:
                    page.keyboard.press('Enter')
                
                # 4. Espera Turnstile
                logger.info("⏳ Aguardando Turnstile (5s)...")
                time.sleep(5)
                page.screenshot(path='debug_pos_submit.png')
                
                # 5. Detecta
                logger.info("🔍 Procurando sitekey...")
                site_key = self._find_sitekey(page)
                
                if not site_key:
                    # Talvez já tenha passado direto
                    if 'home' in page.url.lower():
                        logger.info("   ✅ Login direto (sem captcha)!")
                    else:
                        logger.error("❌ Sitekey não encontrada!")
                        page.screenshot(path='debug_no_sitekey.png')
                        browser.close()
                        return None
                else:
                    logger.info(f"   ✅ Sitekey: {site_key[:30]}...")
                    
                    # 6. Resolve
                    captcha_token = self.solver.solve(site_key, LOGIN_URL)
                    if not captcha_token:
                        logger.error("❌ 2Captcha falhou!")
                        browser.close()
                        return None
                    
                    # 7. Injeta
                    logger.info("💉 Injetando...")
                    self._inject_response(page, captcha_token)
                    time.sleep(2)
                    
                    # 8. Submete novamente
                    logger.info("🔘 Submetendo novamente...")
                    btn = page.query_selector('button[type="submit"]')
                    if btn:
                        btn.click()
                    else:
                        page.keyboard.press('Enter')
                
                # 9. Aguarda home
                logger.info("⏳ Aguardando /home...")
                try:
                    page.wait_for_url('**/home**', timeout=30000)
                    logger.info("   ✅ Redirecionado!")
                except:
                    time.sleep(5)
                    if 'home' not in page.url.lower():
                        page.screenshot(path='debug_login_fail.png')
                        logger.error("❌ Login falhou!")
                        browser.close()
                        return None
                
                # 10. Extrai token
                logger.info("🔍 Extraindo token...")
                token = self._extract_token(page)
                
                browser.close()
                
                if not token:
                    logger.error("❌ Token não encontrado!")
                    return None
                
                self.token = token
                self.token_expiry = self._jwt_expiry(token) or datetime.now() + timedelta(hours=5)
                self._save_cache()
                
                logger.info("="*60)
                logger.info(f"✅ SUCESSO!")
                logger.info(f"   Token: {token[:50]}...")
                logger.info(f"   Expira: {self.token_expiry}")
                logger.info("="*60)
                
                return self.token
                
        except Exception as e:
            logger.error(f"❌ {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def clear_cache(self):
        Path(TOKEN_CACHE_FILE).unlink(missing_ok=True)
        self.token = None
        self.token_expiry = None
        logger.info("🗑️ Cache limpo")


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--visible', action='store_true', help='Mostra navegador')
    parser.add_argument('--force', action='store_true', help='Ignora cache')
    parser.add_argument('--balance', action='store_true', help='Saldo 2Captcha')
    parser.add_argument('--clear', action='store_true', help='Limpa cache')
    args = parser.parse_args()
    
    if args.balance:
        print(f"💰 Saldo: ${TurnstileSolver(CAPTCHA_API_KEY).get_balance():.3f}")
        return
    
    auth = FotusAuth(headless=not args.visible)
    
    if args.clear:
        auth.clear_cache()
        return
    
    token = auth.login(force=args.force)
    
    if token:
        print("\n" + "="*60)
        print("✅ TOKEN:")
        print(token[:80] + "...")
        print("="*60)
        print(f"Expira: {auth.token_expiry}")
        print(f"\nUso: from fotus_auth_final import FotusAuth")
        print("     token = FotusAuth().get_token()")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()