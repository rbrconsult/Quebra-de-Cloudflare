#!/usr/bin/env python3
"""
🔄 RENOVAÇÃO AUTOMÁTICA DE TOKEN - FOTUS
=========================================

Sistema que gerencia token JWT do FOTUS com renovação automática.
Usa o token capturado manualmente e renova quando necessário.

COMO USAR:
----------

1. Primeiro, capture o token manualmente:
   python3 captura_token_manual.py

2. Depois, use esta classe em seus scripts:
   
   from fotus_auth_renovacao import FotusAuth
   
   auth = FotusAuth()
   token = auth.get_token()  # Retorna token válido (renova se necessário)
   
   # Use o token em suas requisições
   headers = {'Authorization': f'Bearer {token}'}

3. Ou execute standalone para verificar status:
   python3 fotus_auth_renovacao.py

MÉTODOS DE RENOVAÇÃO:
---------------------
1. Refresh Token (se disponível na API)
2. Re-login manual (abre navegador quando necessário)
"""

import json
import time
import base64
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================

TOKEN_FILE = "fotus_token.json"
LOGIN_URL = "https://app.fotus.com.br/login"
API_BASE_URL = "https://app.fotus.com.br/api"  # Ajuste conforme necessário

# Margem de segurança: renova token X minutos antes de expirar
RENEWAL_MARGIN_MINUTES = 30


# ==============================================================================
# CLASSE DE AUTENTICAÇÃO
# ==============================================================================

class FotusAuth:
    """
    Gerencia autenticação FOTUS com renovação automática de token
    """
    
    def __init__(self, token_file: str = TOKEN_FILE):
        """
        Inicializa gerenciador de autenticação
        
        Args:
            token_file: Caminho para arquivo JSON com token
        """
        self.token_file = token_file
        self.token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        self.refresh_token: Optional[str] = None
        
        self._load_token()
    
    def _load_token(self) -> bool:
        """Carrega token do arquivo"""
        if not Path(self.token_file).exists():
            print(f"⚠️ Arquivo de token não encontrado: {self.token_file}")
            print(f"   Execute primeiro: python3 captura_token_manual.py")
            return False
        
        try:
            with open(self.token_file, 'r') as f:
                data = json.load(f)
            
            self.token = data.get('token')
            self.refresh_token = data.get('refresh_token')
            
            expiry_str = data.get('expiry')
            if expiry_str:
                self.token_expiry = datetime.fromisoformat(expiry_str)
            
            if self.token:
                print(f"✅ Token carregado de: {self.token_file}")
                if self.token_expiry:
                    print(f"   Expira em: {self.token_expiry.strftime('%d/%m/%Y %H:%M:%S')}")
                return True
            
        except Exception as e:
            print(f"❌ Erro ao carregar token: {e}")
        
        return False
    
    def _save_token(self):
        """Salva token no arquivo"""
        try:
            data = {
                'token': self.token,
                'expiry': self.token_expiry.isoformat() if self.token_expiry else None,
                'refresh_token': self.refresh_token,
                'updated_at': datetime.now().isoformat(),
                'token_preview': self.token[:50] + '...' if self.token else None
            }
            
            with open(self.token_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"💾 Token atualizado em: {self.token_file}")
            
        except Exception as e:
            print(f"⚠️ Erro ao salvar token: {e}")
    
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
            print(f"⚠️ Erro ao decodificar JWT: {e}")
        return None
    
    def is_token_valid(self) -> bool:
        """
        Verifica se token atual é válido
        
        Returns:
            True se token está válido (com margem de segurança)
        """
        if not self.token:
            return False
        
        if not self.token_expiry:
            # Se não sabe expiração, assume válido por segurança
            # mas tenta decodificar
            self.token_expiry = self._decode_jwt_expiry(self.token)
            if not self.token_expiry:
                return True  # Assume válido se não consegue decodificar
        
        # Verifica com margem de segurança
        now = datetime.now()
        margin = timedelta(minutes=RENEWAL_MARGIN_MINUTES)
        
        return self.token_expiry > (now + margin)
    
    def get_token_status(self) -> Dict:
        """
        Retorna status detalhado do token
        
        Returns:
            Dict com informações do token
        """
        if not self.token:
            return {
                'valid': False,
                'message': 'Token não encontrado',
                'action': 'Capture token manualmente'
            }
        
        if not self.token_expiry:
            return {
                'valid': True,
                'message': 'Token presente (expiração desconhecida)',
                'token_preview': self.token[:50] + '...'
            }
        
        now = datetime.now()
        time_left = self.token_expiry - now
        
        if time_left.total_seconds() <= 0:
            return {
                'valid': False,
                'message': 'Token expirado',
                'expired_at': self.token_expiry.isoformat(),
                'action': 'Renovação necessária'
            }
        
        hours_left = time_left.total_seconds() / 3600
        
        if hours_left < (RENEWAL_MARGIN_MINUTES / 60):
            return {
                'valid': False,
                'message': f'Token expira em breve ({hours_left:.1f}h)',
                'expires_at': self.token_expiry.isoformat(),
                'action': 'Renovação recomendada'
            }
        
        return {
            'valid': True,
            'message': f'Token válido ({hours_left:.1f}h restantes)',
            'expires_at': self.token_expiry.isoformat(),
            'token_preview': self.token[:50] + '...'
        }
    
    def renew_with_refresh_token(self) -> bool:
        """
        Tenta renovar token usando refresh token (se API suportar)
        
        Returns:
            True se renovação foi bem-sucedida
        """
        if not self.refresh_token:
            print("⚠️ Refresh token não disponível")
            return False
        
        print("🔄 Tentando renovar com refresh token...")
        
        try:
            # Ajuste esta URL conforme a API do FOTUS
            response = requests.post(
                f"{API_BASE_URL}/auth/refresh",
                json={'refresh_token': self.refresh_token},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                new_token = data.get('token') or data.get('access_token')
                
                if new_token:
                    self.token = new_token
                    self.token_expiry = self._decode_jwt_expiry(new_token)
                    self.refresh_token = data.get('refresh_token', self.refresh_token)
                    self._save_token()
                    
                    print("✅ Token renovado com sucesso!")
                    return True
            
            print(f"❌ Falha na renovação: HTTP {response.status_code}")
            
        except Exception as e:
            print(f"❌ Erro ao renovar token: {e}")
        
        return False
    
    def renew_with_manual_login(self) -> bool:
        """
        Renova token abrindo navegador para login manual
        
        Returns:
            True se renovação foi bem-sucedida
        """
        if not PLAYWRIGHT_AVAILABLE:
            print("❌ Playwright não disponível!")
            print("   Instale com: pip install playwright")
            print("   E execute: playwright install chromium")
            return False
        
        print("\n" + "="*70)
        print("🔄 RENOVAÇÃO MANUAL DE TOKEN")
        print("="*70)
        print("   O navegador vai abrir para você fazer login novamente")
        print("   ⏳ Abrindo em 3 segundos...")
        time.sleep(3)
        
        # Importa e executa captura manual
        try:
            from captura_token_manual import capturar_token_manual
            sucesso = capturar_token_manual()
            
            if sucesso:
                # Recarrega token
                self._load_token()
                return True
            
        except ImportError:
            print("⚠️ Script de captura manual não encontrado")
            print("   Execute: python3 captura_token_manual.py")
        
        return False
    
    def get_token(self, auto_renew: bool = True) -> Optional[str]:
        """
        Retorna token válido, renovando automaticamente se necessário
        
        Args:
            auto_renew: Se True, tenta renovar automaticamente
        
        Returns:
            Token JWT válido ou None
        """
        # Verifica se token está válido
        if self.is_token_valid():
            return self.token
        
        if not auto_renew:
            print("⚠️ Token inválido e auto_renew=False")
            return None
        
        print("\n⚠️ Token precisa ser renovado")
        
        # Tenta renovar com refresh token primeiro
        if self.renew_with_refresh_token():
            return self.token
        
        # Se falhou, tenta login manual
        print("\n💡 Refresh token falhou, será necessário login manual")
        
        if self.renew_with_manual_login():
            return self.token
        
        print("\n❌ Não foi possível renovar token")
        return None
    
    def validate_token_with_api(self) -> bool:
        """
        Valida token fazendo requisição de teste na API
        
        Returns:
            True se token está funcionando
        """
        if not self.token:
            return False
        
        try:
            # Ajuste esta URL para um endpoint de teste da API
            response = requests.get(
                f"{API_BASE_URL}/user/me",  # ou qualquer endpoint que valide auth
                headers={'Authorization': f'Bearer {self.token}'},
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"⚠️ Erro ao validar token: {e}")
            return False


# ==============================================================================
# MAIN - TESTE E STATUS
# ==============================================================================

def main():
    """Execução standalone para verificar status do token"""
    print("="*70)
    print("🔐 FOTUS AUTH - STATUS DO TOKEN")
    print("="*70)
    
    auth = FotusAuth()
    
    if not auth.token:
        print("\n❌ Nenhum token encontrado!")
        print("\n💡 Para começar:")
        print("   1. Execute: python3 captura_token_manual.py")
        print("   2. Faça login no navegador que abrir")
        print("   3. O token será salvo automaticamente")
        return
    
    # Mostra status
    status = auth.get_token_status()
    print(f"\n📊 Status: {status['message']}")
    
    if status.get('expires_at'):
        print(f"⏰ Expira em: {status['expires_at']}")
    
    if status.get('token_preview'):
        print(f"🔑 Token: {status['token_preview']}")
    
    # Testa obter token (com renovação automática)
    print("\n🔍 Testando get_token()...")
    token = auth.get_token()
    
    if token:
        print("✅ Token válido obtido!")
        print(f"   {token[:50]}...")
    else:
        print("❌ Falha ao obter token válido")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
