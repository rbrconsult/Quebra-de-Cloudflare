#!/usr/bin/env python3
"""
🎫 FOTUS Get Token - Obtém token do cache
=========================================

Obtém token JWT do cache salvo pelo fotus_manual_login.py

Uso:
    python3 fotus_get_token.py              # Mostra token
    python3 fotus_get_token.py --check      # Verifica validade
    python3 fotus_get_token.py --json       # Saída JSON

Integração em código:
    from fotus_get_token import get_token
    
    token = get_token()
    if token:
        headers = {"Authorization": f"Bearer {token}"}
        # Usar em requests...
"""

import json
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

TOKEN_CACHE_FILE = ".fotus_token_cache.json"


def get_token() -> Optional[str]:
    """Obtém token do cache"""
    if not Path(TOKEN_CACHE_FILE).exists():
        return None
    
    try:
        cache = json.loads(Path(TOKEN_CACHE_FILE).read_text())
        return cache.get('token')
    except:
        return None


def get_cache_info() -> Optional[Dict]:
    """Obtém informações completas do cache"""
    if not Path(TOKEN_CACHE_FILE).exists():
        return None
    
    try:
        cache = json.loads(Path(TOKEN_CACHE_FILE).read_text())
        expiry = datetime.fromisoformat(cache['expiry'])
        updated = datetime.fromisoformat(cache['updated'])
        now = datetime.now()
        
        return {
            'token': cache['token'],
            'expiry': expiry,
            'updated': updated,
            'valid': expiry > now,
            'remaining_seconds': (expiry - now).total_seconds() if expiry > now else 0,
            'remaining_minutes': int((expiry - now).total_seconds() / 60) if expiry > now else 0,
            'remaining_hours': int((expiry - now).total_seconds() / 3600) if expiry > now else 0,
        }
    except Exception as e:
        return None


def main():
    parser = argparse.ArgumentParser(description='Obtém token JWT do cache')
    parser.add_argument('--check', action='store_true', help='Verifica validade do token')
    parser.add_argument('--json', action='store_true', help='Saída em formato JSON')
    args = parser.parse_args()
    
    if not Path(TOKEN_CACHE_FILE).exists():
        print(f"❌ Cache não encontrado: {TOKEN_CACHE_FILE}")
        print("   Execute primeiro: python3 fotus_manual_login.py")
        sys.exit(1)
    
    info = get_cache_info()
    
    if not info:
        print("❌ Erro ao ler cache")
        sys.exit(1)
    
    if args.json:
        # Saída JSON
        output = {
            'token': info['token'],
            'expiry': info['expiry'].isoformat(),
            'updated': info['updated'].isoformat(),
            'valid': info['valid'],
            'remaining_seconds': info['remaining_seconds'],
        }
        print(json.dumps(output, indent=2))
        sys.exit(0 if info['valid'] else 1)
    
    if args.check:
        # Verifica validade
        if info['valid']:
            print(f"✅ Token válido")
            print(f"   Expira em: {info['expiry'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Restam: {info['remaining_hours']}h {info['remaining_minutes'] % 60}min")
            sys.exit(0)
        else:
            print(f"❌ Token expirado")
            print(f"   Expirou em: {info['expiry'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Execute: python3 fotus_manual_login.py")
            sys.exit(1)
    
    # Saída padrão: apenas token
    if info['valid']:
        print(info['token'])
        sys.exit(0)
    else:
        print(f"❌ Token expirado (expirou em {info['expiry'].strftime('%Y-%m-%d %H:%M:%S')})", file=sys.stderr)
        print(f"   Execute: python3 fotus_manual_login.py", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
