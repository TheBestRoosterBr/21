import socket
import time

def check_server_connection(host="localhost", port=5000, timeout=1.0):
    """
    Verifica se um servidor está disponível na porta especificada.
    
    Args:
        host: O nome do host ou endereço IP do servidor
        port: A porta do servidor
        timeout: Tempo máximo de espera em segundos
        
    Returns:
        bool: True se o servidor estiver disponível, False caso contrário
    """
    try:
        # Criar socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        # Tentar conectar
        start_time = time.time()
        result = sock.connect_ex((host, port))
        elapsed = time.time() - start_time
        
        # Fechar socket
        sock.close()
        
        # Verificar resultado
        if result == 0:
            print(f"Servidor disponível em {host}:{port} ({elapsed:.2f}s)")
            return True
        else:
            print(f"Servidor indisponível em {host}:{port} ({elapsed:.2f}s)")
            return False
            
    except socket.error as e:
        print(f"Erro ao verificar servidor: {e}")
        return False 