#!/usr/bin/env python3
"""
🔑 CAPTURA MANUAL DE TOKEN - FOTUS
===================================

Script para capturar token JWT do FOTUS através de login manual.
Você faz login UMA VEZ e o token é salvo para uso futuro.

COMO USAR:
----------
1. Execute este script:
   python3 captura_token_manual.py

2. Uma janela do navegador vai abrir
3. Faça login normalmente no FOTUS
4. Aguarde ser redirecionado para a home
5. O script captura o token automaticamente
6. Token é salvo em 'fotus_token.json'

REQUISITOS:
-----------
pip install playwright
playwright install chromium
"""

import json
import time
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("❌ Playwright não instalado!")
    print("   Instale com:")
    print("   pip install playwright")
    print("   playwright install chromium")
    exit(1)


# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================

LOGIN_URL = "https://app.fotus.com.br/login"
TOKEN_FILE = "fotus_token.json"


# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================

def decode_jwt_expiry(token: str) -> Optional[datetime]:
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
        print(f"⚠️ Erro ao decodificar JWT: {e}")
    return None


def save_token(token: str, expiry: Optional[datetime] = None):
    """Salva token em arquivo JSON"""
    if not expiry:
        expiry = datetime.now() + timedelta(hours=5)
    
    data = {
        'token': token,
        'expiry': expiry.isoformat(),
        'captured_at': datetime.now().isoformat(),
        'token_preview': token[:50] + '...'
    }
    
    with open(TOKEN_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n✅ Token salvo em: {TOKEN_FILE}")
    print(f"📅 Expira em: {expiry.strftime('%d/%m/%Y %H:%M:%S')}")


def extract_token_from_page(page) -> Optional[str]:
    """Extrai token JWT do localStorage da página"""
    
    # Lista de possíveis chaves onde o token pode estar
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
    
    # Tenta chaves conhecidas primeiro
    for key in token_keys:
        value = page.evaluate(f'localStorage.getItem("{key}")')
        if value and isinstance(value, str) and value.startswith('eyJ'):
            print(f"   🎫 Token encontrado em localStorage['{key}']")
            return value
    
    # Se não encontrou, busca em todo localStorage
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
    
    print(f"   📦 Chaves no localStorage: {list(all_storage.keys())}")
    
    # Procura qualquer valor que pareça JWT
    for key, value in all_storage.items():
        if value and isinstance(value, str) and value.startswith('eyJ'):
            print(f"   🎫 Token JWT encontrado em: {key}")
            return value
        
        # Tenta parsear JSON aninhado
        if value and isinstance(value, str):
            try:
                data = json.loads(value)
                if isinstance(data, dict):
                    for k, v in data.items():
                        if isinstance(v, str) and v.startswith('eyJ'):
                            print(f"   🎫 Token em {key}.{k}")
                            return v
            except:
                pass
    
    return None


# ==============================================================================
# CAPTURA MANUAL
# ==============================================================================

def capturar_token_manual():
    """
    Abre navegador para login manual e captura token
    """
    print("="*70)
    print("🔑 CAPTURA MANUAL DE TOKEN - FOTUS")
    print("="*70)
    print("\n📋 INSTRUÇÕES:")
    print("   1. Uma janela do navegador vai abrir")
    print("   2. Faça login normalmente com seu email e senha")
    print("   3. Aguarde ser redirecionado para a home/dashboard")
    print("   4. O token será capturado automaticamente")
    print("\n⏳ Abrindo navegador em 3 segundos...")
    time.sleep(3)
    
    with sync_playwright() as p:
        print("\n🌐 Iniciando navegador...")
        
        # Lança navegador VISÍVEL para login manual
        browser = p.chromium.launch(
            headless=False,  # VISÍVEL!
            args=[
                '--start-maximized',
            ]
        )
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='pt-BR',
            timezone_id='America/Sao_Paulo',
        )
        
        page = context.new_page()
        
        print(f"📄 Acessando: {LOGIN_URL}")
        page.goto(LOGIN_URL)
        
        print("\n" + "="*70)
        print("👤 FAÇA LOGIN MANUALMENTE NO NAVEGADOR")
        print("="*70)
        print("   ⏳ Aguardando você fazer login...")
        print("   💡 Dica: Após o login, aguarde carregar a página inicial")
        print()
        
        # Aguarda redirecionamento para home/dashboard
        logged_in = False
        for i in range(300):  # Aguarda até 5 minutos
            time.sleep(1)
            current_url = page.url
            
            # Verifica se foi redirecionado (login bem-sucedido)
            if '/home' in current_url or '/dashboard' in current_url or '/painel' in current_url:
                print(f"\n✅ Login detectado! URL: {current_url}")
                logged_in = True
                break
            
            # Feedback a cada 10 segundos
            if i > 0 and i % 10 == 0:
                print(f"   ⏳ Aguardando login... ({i}s)")
        
        if not logged_in:
            print("\n❌ Timeout! Login não foi completado em 5 minutos.")
            browser.close()
            return False
        
        # Aguarda um pouco para garantir que o token foi salvo
        print("\n⏳ Aguardando aplicação carregar completamente...")
        time.sleep(3)
        
        # Extrai token
        print("\n🔍 Procurando token no localStorage...")
        token = extract_token_from_page(page)
        
        browser.close()
        
        if not token:
            print("\n❌ Token não encontrado!")
            print("   💡 Possíveis causas:")
            print("      - Login não foi completado")
            print("      - Token está em cookie (não localStorage)")
            print("      - Site usa outro método de autenticação")
            return False
        
        # Decodifica expiração
        expiry = decode_jwt_expiry(token)
        
        # Salva token
        save_token(token, expiry)
        
        print("\n" + "="*70)
        print("🎉 TOKEN CAPTURADO COM SUCESSO!")
        print("="*70)
        print(f"\n📄 Arquivo: {TOKEN_FILE}")
        print(f"🔑 Token: {token[:50]}...")
        
        if expiry:
            tempo_valido = expiry - datetime.now()
            horas = tempo_valido.total_seconds() / 3600
            print(f"⏰ Válido por: {horas:.1f} horas")
        
        print("\n💡 Use este token com o script de renovação automática!")
        
        return True


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    try:
        sucesso = capturar_token_manual()
        exit(0 if sucesso else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Cancelado pelo usuário")
        exit(1)
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
