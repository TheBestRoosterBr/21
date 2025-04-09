#!/usr/bin/env python
"""
Script para iniciar o servidor de lobby de Blackjack 21 P2P.
Este servidor gerencia as salas de jogo online e facilita a comunicação entre os clientes.
"""

import sys
import os
import argparse

# Adicionar o diretório raiz ao path para importar os módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.lobby_server import LobbyServer

def main():
    """Função principal para iniciar o servidor de lobby"""
    parser = argparse.ArgumentParser(description="Servidor de Lobby para Blackjack P2P")
    
    parser.add_argument("--host", default="0.0.0.0", 
                      help="Endereço IP para o servidor (padrão: 0.0.0.0, aceita conexões de qualquer IP)")
    
    parser.add_argument("--port", type=int, default=5000, 
                      help="Porta para o servidor escutar (padrão: 5000)")
    
    parser.add_argument("--debug", action="store_true", 
                      help="Ativar mensagens de debug detalhadas")
    
    args = parser.parse_args()
    
    print("=== Servidor de Lobby Blackjack 21 P2P ===")
    print(f"Iniciando servidor em {args.host}:{args.port}")
    
    if args.debug:
        print("Modo de debug ativado")
    
    # Iniciar o servidor
    server = LobbyServer(host=args.host, port=args.port)
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nServidor interrompido pelo usuário")
    except Exception as e:
        print(f"Erro fatal: {e}")
    finally:
        server.stop()
        print("Servidor encerrado")

if __name__ == "__main__":
    main() 