import socket
import json
import threading
import time
import uuid
import random
import string

class MatchmakingService:
    """Serviço de matchmaking para conectar jogadores"""
    
    def __init__(self, server_host="localhost", server_port=5000):
        self.server_host = server_host
        self.server_port = server_port
        self.cached_rooms = []
        self.last_update = 0
        self.local_discovery_port = 5001  # Porta para descoberta na rede local
        self.rooms = {}  # Armazena as informações das salas disponíveis
        self.local_rooms = {}  # Armazena as informações das salas na rede local
        
        # Iniciar thread para descoberta na rede local
        self.local_discovery_running = False
        self.local_discovery_thread = None
        
        self.room_cache = []
        self.last_refresh = 0

    @staticmethod
    def generate_room_id():
        return ''.join(random.choices(string.digits, k=4))

    def _send_request(self, command, data=None):
        """Envia uma requisição para o servidor de matchmaking"""
        if data is None:
            data = {}
            
        # Adiciona o comando ao payload
        data["command"] = command
        
        try:
            # Cria um socket TCP
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(5)  # timeout de 5 segundos
            
            # Tenta conectar ao servidor
            client_socket.connect((self.server_host, self.server_port))
            
            # Envia a requisição
            request = json.dumps(data).encode('utf-8')
            client_socket.send(request)
            
            # Recebe a resposta
            response_data = client_socket.recv(4096)
            response = json.loads(response_data.decode('utf-8'))
            
            client_socket.close()
            
            # Verifica se a resposta foi bem-sucedida
            if response.get("status") == "success":
                return True, response
            else:
                return False, response.get("message", "Erro desconhecido")
                
        except socket.timeout:
            return False, "Tempo limite excedido ao conectar ao servidor"
        except ConnectionRefusedError:
            return False, "Servidor não está disponível"
        except json.JSONDecodeError:
            return False, "Resposta inválida do servidor"
        except Exception as e:
            return False, str(e)
            
    def create_room(self, host_name, room_name=None, password=None, host_port=5555):
        """Cria uma nova sala no servidor de matchmaking"""
        data = {
            "host_name": host_name,
            "room_name": room_name or f"Sala de {host_name}",
            "password": password,
            "host_port": host_port
        }
        
        return self._send_request("CREATE_ROOM", data)
        
    def join_room(self, room_id, player_name, password=None):
        """Conecta-se a uma sala existente"""
        data = {
            "room_id": room_id,
            "player_name": player_name,
            "password": password
        }
        
        return self._send_request("JOIN_ROOM", data)
        
    def list_games(self):
        """Lista todas as salas disponíveis no servidor"""
        # Cache de 5 segundos para evitar sobrecarga no servidor
        current_time = time.time()
        if current_time - self.last_refresh < 5 and self.room_cache:
            return True, {"rooms": self.room_cache}
            
        result = self._send_request("LIST_ROOMS")
        
        if result[0]:
            self.room_cache = result[1].get("rooms", [])
            self.last_refresh = current_time
            
        return result
        
    def leave_room(self, room_id, player_name):
        """Remove um jogador de uma sala"""
        data = {
            "room_id": room_id,
            "player_name": player_name
        }
        
        return self._send_request("LEAVE_ROOM", data)
        
    def update_room(self, room_id, players):
        """Atualiza informações de uma sala"""
        data = {
            "room_id": room_id,
            "players": players
        }
        
        return self._send_request("UPDATE_ROOM", data)

    def create_local_game(self, host_name, room_name=None, password=None):
        """Criar uma nova sala de jogo na rede local"""
        try:
            # Gerar ID único para a sala
            game_id = str(uuid.uuid4().int)[:4]  # Pegar os primeiros 4 dígitos
            
            # Usar endereço local
            host_address = f"{socket.gethostbyname(socket.gethostname())}:5678"
            
            room_data = {
                "game_id": game_id,
                "host_name": host_name,
                "host_address": host_address,
                "players": [host_name],
                "room_name": room_name or f"Sala de {host_name}",
                "has_password": password is not None,
                "password": password,
                "created_at": time.time()
            }
            
            # Armazenar informações da sala localmente
            self.local_rooms[game_id] = room_data
            
            # Iniciar broadcast na rede local se ainda não estiver rodando
            if not self.local_discovery_running:
                self.start_local_discovery()
            
            return True, game_id, room_data
        
        except Exception as e:
            return False, None, str(e)
    
    def join_local_game(self, game_id, password=None):
        """Entrar em uma sala de jogo na rede local"""
        try:
            if game_id not in self.local_rooms:
                return False, "Sala não encontrada na rede local"
            
            room = self.local_rooms[game_id]
            
            # Verificar senha se necessário
            if room.get("has_password", False) and room.get("password") != password:
                return False, "Senha incorreta"
            
            return True, room
        
        except Exception as e:
            return False, str(e)
    
    def list_local_games(self):
        """Listar todas as salas de jogo disponíveis na rede local"""
        try:
            # Filtrar salas antigas (mais de 30 minutos)
            current_time = time.time()
            active_rooms = [room for room in self.local_rooms.values() 
                            if current_time - room["created_at"] < 1800]
            
            # Remover senhas antes de enviar para o cliente
            for room in active_rooms:
                room.pop("password", None)
            
            return True, active_rooms
        
        except Exception as e:
            return False, str(e)
    
    def start_local_discovery(self):
        """Iniciar serviço de descoberta na rede local"""
        self.local_discovery_running = True
        self.local_discovery_thread = threading.Thread(target=self._local_discovery_service)
        self.local_discovery_thread.daemon = True
        self.local_discovery_thread.start()
    
    def _local_discovery_service(self):
        """Serviço para anunciar e descobrir jogos na rede local usando UDP broadcast"""
        try:
            # Criação do socket UDP para broadcast
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', self.local_discovery_port))
            
            while self.local_discovery_running:
                # Enviar broadcast de salas disponíveis a cada 5 segundos
                if self.local_rooms:
                    data = json.dumps({
                        "type": "room_broadcast",
                        "rooms": list(self.local_rooms.values())
                    }).encode('utf-8')
                    
                    sock.sendto(data, ('<broadcast>', self.local_discovery_port))
                
                # Esperar 5 segundos
                time.sleep(5)
        
        except Exception as e:
            print(f"Erro no serviço de descoberta local: {e}")
        finally:
            self.local_discovery_running = False
            sock.close()
    
    def stop_local_discovery(self):
        """Parar o serviço de descoberta na rede local"""
        self.local_discovery_running = False
        if self.local_discovery_thread:
            self.local_discovery_thread.join(timeout=1)
            self.local_discovery_thread = None

    def get_local_room_info(self, room_id):
        """Obter informações sobre uma sala na rede local pelo ID"""
        try:
            if room_id not in self.local_rooms:
                # Tentar redescobrir salas locais
                success, _ = self.list_local_games()
                
                # Verificar novamente se a sala foi encontrada
                if room_id not in self.local_rooms:
                    return False, "Sala não encontrada na rede local"
            
            return True, self.local_rooms[room_id]
        except Exception as e:
            return False, f"Erro ao obter informações da sala: {str(e)}"