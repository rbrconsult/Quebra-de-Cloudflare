"""
Módulo para bypass de proteções Cloudflare
"""

import requests
from typing import Optional, Dict


class CloudflareBypass:
    """
    Classe para gerenciar bypass de proteções Cloudflare
    """
    
    def __init__(self, user_agent: Optional[str] = None):
        """
        Inicializa o bypass
        
        Args:
            user_agent: User agent customizado (opcional)
        """
        self.session = requests.Session()
        self.user_agent = user_agent or self._get_default_user_agent()
        self.session.headers.update({
            'User-Agent': self.user_agent
        })
    
    def _get_default_user_agent(self) -> str:
        """Retorna um user agent padrão"""
        return 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """
        Realiza requisição GET com bypass
        
        Args:
            url: URL alvo
            **kwargs: Argumentos adicionais para requests
            
        Returns:
            Response object
        """
        return self.session.get(url, **kwargs)
    
    def post(self, url: str, data: Optional[Dict] = None, **kwargs) -> requests.Response:
        """
        Realiza requisição POST com bypass
        
        Args:
            url: URL alvo
            data: Dados do POST
            **kwargs: Argumentos adicionais para requests
            
        Returns:
            Response object
        """
        return self.session.post(url, data=data, **kwargs)


if __name__ == "__main__":
    # Exemplo de uso
    bypass = CloudflareBypass()
    print("CloudflareBypass inicializado com sucesso!")
