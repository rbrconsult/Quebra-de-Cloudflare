#!/usr/bin/env python3
"""
📝 EXEMPLO DE USO - FOTUS AUTH COM 2CAPTCHA
============================================

Demonstra como usar o sistema de autenticação em seus scripts.
"""

from fotus_auth_2captcha import FotusAuth2Captcha
import requests


def exemplo_basico():
    """Exemplo básico: obter token e fazer requisição"""
    print("="*60)
    print("EXEMPLO 1: Uso Básico")
    print("="*60)
    
    # Inicializa autenticação
    auth = FotusAuth2Captcha(
        email="gabriel@evolveenergia.com.br",
        password="container1",
        captcha_api_key="801e53e81ceea1b0b287a1a128231d00",
        headless=True  # Modo headless para automação
    )
    
    # Obtém token (usa cache se válido, senão faz login)
    token = auth.get_token()
    
    if not token:
        print("❌ Falha ao obter token")
        return
    
    print(f"\n✅ Token obtido: {token[:50]}...")
    
    # Usa token em requisição
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Exemplo de requisição (ajuste a URL conforme sua necessidade)
    try:
        response = requests.get(
            'https://app.fotus.com.br/api/user/me',  # Exemplo
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            print("\n✅ Requisição bem-sucedida!")
            print(f"Resposta: {response.json()}")
        else:
            print(f"\n⚠️ Status: {response.status_code}")
            
    except Exception as e:
        print(f"\n⚠️ Erro na requisição: {e}")


def exemplo_com_renovacao():
    """Exemplo: verificar e renovar token automaticamente"""
    print("\n" + "="*60)
    print("EXEMPLO 2: Renovação Automática")
    print("="*60)
    
    auth = FotusAuth2Captcha()
    
    # Verifica se token está válido
    if auth.is_token_valid():
        print("✅ Token em cache ainda válido")
        print(f"   Expira em: {auth.token_expiry}")
    else:
        print("⚠️ Token inválido ou expirado")
        print("   Fazendo novo login...")
        token = auth.login(force=True)
        
        if token:
            print("✅ Novo token obtido!")
        else:
            print("❌ Falha no login")


def exemplo_loop_requisicoes():
    """Exemplo: fazer múltiplas requisições com renovação automática"""
    print("\n" + "="*60)
    print("EXEMPLO 3: Loop com Renovação Automática")
    print("="*60)
    
    auth = FotusAuth2Captcha()
    
    # Simula múltiplas requisições
    for i in range(5):
        print(f"\n📡 Requisição {i+1}/5...")
        
        # get_token() renova automaticamente se necessário
        token = auth.get_token()
        
        if not token:
            print("❌ Não foi possível obter token válido")
            break
        
        # Faz sua requisição aqui
        headers = {'Authorization': f'Bearer {token}'}
        
        # ... sua lógica de requisição ...
        
        print(f"✅ Requisição {i+1} completada")


def exemplo_tratamento_erro():
    """Exemplo: tratamento de erros"""
    print("\n" + "="*60)
    print("EXEMPLO 4: Tratamento de Erros")
    print("="*60)
    
    try:
        auth = FotusAuth2Captcha()
        token = auth.get_token()
        
        if not token:
            raise Exception("Não foi possível obter token")
        
        # Suas requisições aqui...
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        print("\n💡 Possíveis soluções:")
        print("   1. Verifique suas credenciais")
        print("   2. Verifique saldo do 2Captcha")
        print("   3. Verifique conexão com internet")
        print("   4. Tente executar com --visible para debug")


def verificar_saldo_2captcha():
    """Verifica saldo da conta 2Captcha"""
    print("\n" + "="*60)
    print("VERIFICAR SALDO 2CAPTCHA")
    print("="*60)
    
    from fotus_auth_2captcha import TwoCaptchaSolver
    
    solver = TwoCaptchaSolver("801e53e81ceea1b0b287a1a128231d00")
    balance = solver.get_balance()
    
    if balance is not None:
        print(f"\n💰 Saldo atual: ${balance:.2f}")
        
        if balance < 1.0:
            print("\n⚠️ Saldo baixo!")
            print("   Recarregue em: https://2captcha.com")
        else:
            print("✅ Saldo suficiente")
    else:
        print("❌ Não foi possível verificar saldo")


if __name__ == "__main__":
    print("\n🚀 EXEMPLOS DE USO - FOTUS AUTH\n")
    
    # Descomente o exemplo que deseja executar:
    
    exemplo_basico()
    # exemplo_com_renovacao()
    # exemplo_loop_requisicoes()
    # exemplo_tratamento_erro()
    # verificar_saldo_2captcha()
    
    print("\n✅ Exemplos concluídos!")
