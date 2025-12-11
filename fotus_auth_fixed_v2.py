#!/usr/bin/env python3
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

CREDENTIALS = {
    "email": "gabriel@evolveenergia.com.br",
    "password": "container1"
}

CAPTCHA_API_KEY = "801e53e81ceea1b0b287a1a128231d00"
LOGIN_URL = "https://app.fotus.com.br/login"
TOKEN_CACHE_FILE = ".fotus_token_cache.json"
FOTUS_TURNSTILE_SITEKEY = "0x4AAAAAACCs0CK5Bg2jZ-lT"  # Fallback hardcoded

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)


class TurnstileSolver:
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def solve(self, site_key: str, page_url: str, timeout: int = 120) -> Optional[str]:
        logger.info(f"🔄 2Captcha: enviando...")
        
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
                logger.error(f"❌ {result.get('request')}")
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
        logger.info("🔍 Método 1: Procurando data-sitekey...")
        el = page.query_selector('[data-sitekey]')
        if el:
            sk = el.get_attribute('data-sitekey')
            logger.info(f"   ✅ Encontrado: {sk[:30]}...")
            return sk
        
        logger.info("🔍 Método 2: Procurando em iframes...")
        for frame in page.frames:
            logger.info(f"   Frame: {frame.url[:80]}...")
            if 'challenges.cloudflare.com' in frame.url or 'turnstile' in frame.url.lower():
                match = re.search(r'sitekey=([^&]+)', frame.url)
                if match:
                    sk = match.group(1)
                    logger.info(f"   ✅ Encontrado no iframe: {sk[:30]}...")
                    return sk
        
        logger.info("🔍 Método 3: Regex no HTML...")
        html = page.content()
        patterns = [
            r'data-sitekey=["\']([0-9a-zA-Z_-]+)["\']',
            r'sitekey["\s:]+["\']([0-9a-zA-Z_-]+)["\']',
            r'"siteKey":"([^"]+)"',
            r"'siteKey':'([^']+)'",
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                sk = match.group(1)
                logger.info(f"   ✅ Encontrado via regex: {sk[:30]}...")
                return sk
        
        logger.info("🔍 Método 4: JavaScript evaluation...")
        try:
            sk = page.evaluate('''() => {
                // Procura em todos os elementos
                let el = document.querySelector('[data-sitekey]');
                if (el) return el.getAttribute('data-sitekey');
                
                // Procura em scripts
                let scripts = document.querySelectorAll('script');
                for (let script of scripts) {
                    let match = script.textContent.match(/sitekey["\s:]+["']([0-9a-zA-Z_-]+)["']/i);
                    if (match) return match[1];
                }
                
                // Procura no window
                if (window.turnstile) return window.turnstile.sitekey;
                
                return null;
            }''')
            if sk:
                logger.info(f"   ✅ Encontrado via JS: {sk[:30]}...")
                return sk
        except:
            pass
        
        logger.warning("⚠️ Sitekey não encontrada dinamicamente!")
        logger.info(f"🔑 Usando sitekey hardcoded: {FOTUS_TURNSTILE_SITEKEY[:30]}...")
        return FOTUS_TURNSTILE_SITEKEY
    
    def _inject_response(self, page, token: str):
        """Injeta resposta do Turnstile com múltiplas tentativas de callback"""
        page.evaluate(f'''() => {{
            // 1. Preenche inputs existentes
            document.querySelectorAll('input[name="cf-turnstile-response"]')
                .forEach(i => i.value = "{token}");
            
            // 2. Cria input se não existir
            if (!document.querySelector('input[name="cf-turnstile-response"]')) {{
                let input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'cf-turnstile-response';
                input.value = "{token}";
                document.querySelector('form')?.appendChild(input);
            }}
            
            // 3. Tenta encontrar e chamar callback do Turnstile (múltiplos métodos)
            
            // Método 1: window.turnstile.callback
            if (window.turnstile?.callback) {{
                try {{
                    console.log('[INJECT] Chamando window.turnstile.callback');
                    window.turnstile.callback("{token}");
                }} catch(e) {{ console.error('[INJECT] Erro callback:', e); }}
            }}
            
            // Método 2: Procura callback em widgets
            try {{
                const widgets = document.querySelectorAll('.cf-turnstile, [data-sitekey]');
                widgets.forEach(widget => {{
                    if (widget._callback) {{
                        console.log('[INJECT] Chamando widget._callback');
                        widget._callback("{token}");
                    }}
                }});
            }} catch(e) {{ console.error('[INJECT] Erro widget callback:', e); }}
            
            // Método 3: Dispara eventos customizados
            try {{
                const event = new CustomEvent('cf-turnstile-response', {{
                    detail: {{ token: "{token}" }},
                    bubbles: true,
                    cancelable: true
                }});
                document.dispatchEvent(event);
                console.log('[INJECT] Evento cf-turnstile-response disparado');
            }} catch(e) {{ console.error('[INJECT] Erro evento:', e); }}
            
            // Método 4: Dispara eventos change nos inputs
            document.querySelectorAll('input[name="cf-turnstile-response"]')
                .forEach(i => {{
                    i.dispatchEvent(new Event('input', {{bubbles: true}}));
                    i.dispatchEvent(new Event('change', {{bubbles: true}}));
                }});
            
            // Método 5: Tenta marcar checkbox visualmente (se existir)
            try {{
                const checkbox = document.querySelector('.cf-turnstile input[type="checkbox"]');
                if (checkbox) {{
                    checkbox.checked = true;
                    checkbox.dispatchEvent(new Event('change', {{bubbles: true}}));
                    console.log('[INJECT] Checkbox marcado');
                }}
            }} catch(e) {{ console.error('[INJECT] Erro checkbox:', e); }}
            
            console.log('[INJECT] Injeção completa');
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
                
                if isinstance(val, str) and val.count('.') == 2 and len(val) > 50 and val.startswith('eyJ'):
                    logger.info(f"   📍 {key}")
                    return val.strip('"')
                
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
        logger.info(f"💰 Saldo: ${balance:.3f}")
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
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    locale='pt-BR',
                )
                
                context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    window.chrome = { runtime: {} };
                """)
                
                page = context.new_page()
                
                logger.info("📄 Acessando...")
                page.goto(LOGIN_URL, wait_until='domcontentloaded', timeout=60000)
                time.sleep(3)
                page.screenshot(path='debug_01_inicial.png')
                
                logger.info("📝 Preenchendo...")
                page.wait_for_selector('input', timeout=10000)
                
                page.query_selector('input[type="email"]').fill(CREDENTIALS['email'])
                time.sleep(0.3)
                page.query_selector('input[type="password"]').fill(CREDENTIALS['password'])
                time.sleep(0.5)
                page.screenshot(path='debug_02_preenchido.png')
                
                logger.info("🔘 Clicando Entrar...")
                btn = page.query_selector('button[type="submit"]')
                if btn:
                    btn.click()
                else:
                    page.keyboard.press('Enter')
                
                logger.info("⏳ Aguardando Turnstile (10s)...")
                time.sleep(10)
                page.screenshot(path='debug_03_pos_submit.png')
                
                site_key = self._find_sitekey(page)
                
                if not site_key:
                    if 'home' in page.url.lower():
                        logger.info("   ✅ Login direto!")
                    else:
                        logger.error("❌ Sitekey não encontrada!")
                        page.screenshot(path='debug_04_no_sitekey.png')
                        
                        # Salva HTML para debug
                        Path('debug_page.html').write_text(page.content())
                        logger.info("💾 HTML salvo em debug_page.html")
                        
                        browser.close()
                        return None
                else:
                    captcha_token = self.solver.solve(site_key, LOGIN_URL)
                    if not captcha_token:
                        browser.close()
                        return None
                    
                    logger.info("💉 Injetando...")
                    self._inject_response(page, captcha_token)
                    time.sleep(2)  # Aguarda JavaScript processar
                    page.screenshot(path='debug_05_injetado.png')
                    
                    logger.info("⏳ Aguardando Cloudflare validar (15s)...")
                    time.sleep(15)
                    page.screenshot(path='debug_05b_apos_espera.png')
                    
                    # Verifica se já redirecionou para /home
                    if 'home' in page.url.lower():
                        logger.info("✅ Já redirecionou para /home automaticamente!")
                    else:
                        logger.info("🔍 Ainda na página de login, verificando Turnstile...")
                        
                        # Verifica se Turnstile foi aceito
                        try:
                            turnstile_success = page.evaluate('''() => {
                                const input = document.querySelector('input[name="cf-turnstile-response"]');
                                return input && input.value && input.value.length > 0;
                            }''')
                            if turnstile_success:
                                logger.info("   ✅ Turnstile aceito!")
                            else:
                                logger.warning("   ⚠️ Turnstile pode não ter sido aceito")
                        except:
                            pass
                        
                        logger.info("🔘 Clicando Entrar novamente...")
                        btn = page.query_selector('button[type="submit"]')
                        if btn:
                            btn.click()
                        else:
                            page.keyboard.press('Enter')
                
                logger.info("⏳ Aguardando /home...")
                try:
                    page.wait_for_url('**/home**', timeout=30000)
                    logger.info("   ✅ Redirecionado!")
                except:
                    time.sleep(5)
                    if 'home' not in page.url.lower():
                        page.screenshot(path='debug_06_fail.png')
                        logger.error("❌ Login falhou!")
                        browser.close()
                        return None
                
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
                logger.info("="*60)
                
                return self.token
                
        except Exception as e:
            logger.error(f"❌ {e}")
            import traceback
            traceback.print_exc()
            return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--visible', action='store_true')
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--balance', action='store_true')
    args = parser.parse_args()
    
    if args.balance:
        print(f"💰 Saldo: ${TurnstileSolver(CAPTCHA_API_KEY).get_balance():.3f}")
        return
    
    auth = FotusAuth(headless=not args.visible)
    token = auth.login(force=args.force)
    
    if token:
        print("\n" + "="*60)
        print("✅ TOKEN:")
        print(token[:80] + "...")
        print("="*60)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
