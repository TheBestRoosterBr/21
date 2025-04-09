import socket
import json
import threading
import time
import random
import string
import argparse

class LobbyServer:
    def __init__(self, host="0.0.0.0", port=5000):
        self.host = host
        self.port = port
        self.rooms = {}  # Armazena salas ativas
        self.server_socket = None
        self.running = False
        self.lock = threading.Lock()  # Para acesso seguro ao dicionário de salas
        
    def generate_room_id(self):
        """Gera um ID de sala aleatório de 4 dígitos"""
        return ''.join(random.choices(string.digits, k=4))
        
    def start(self):
        """Inicia o servidor de lobby"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.running = True
            print(f"Servidor de lobby iniciado em {self.host}:{self.port}")
            
            # Thread para limpar salas antigas
            cleanup_thread = threading.Thread(target=self._cleanup_old_rooms)
            cleanup_thread.daemon = True
            cleanup_thread.start()
            
            # Loop principal para aceitar conexões
            while self.running:
                client_socket, client_address = self.server_socket.accept()
                print(f"Nova conexão de {client_address}")
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, client_address)
                )
                client_thread.daemon = True
                client_thread.start()
                
        except KeyboardInterrupt:
            print("Servidor interrompido pelo usuário")
        except Exception as e:
            print(f"Erro no servidor: {e}")
        finally:
            self.stop()
            
    def stop(self):
        """Para o servidor de lobby"""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None
        print("Servidor de lobby encerrado")
        
    def _handle_client(self, client_socket, client_address):
        """Manipula a conexão do cliente"""
        try:
            # Recebe a mensagem do cliente
            data = client_socket.recv(4096)
            if not data:
                return
                
            # Analisa a mensagem
            request = json.loads(data.decode('utf-8'))
            command = request.get("command")
            
            print(f"Comando recebido: {command} de {client_address}")
            
            # Processa o comando
            response = self._process_command(command, request, client_address)
            
            # Envia a resposta
            client_socket.send(json.dumps(response).encode('utf-8'))
        except json.JSONDecodeError:
            print(f"Erro ao decodificar JSON de {client_address}")
            response = {"status": "error", "message": "Formato JSON inválido"}
            client_socket.send(json.dumps(response).encode('utf-8'))
        except Exception as e:
            print(f"Erro ao manipular cliente {client_address}: {e}")
        finally:
            client_socket.close()
            
    def _process_command(self, command, request, client_address):
        """Processa comandos dos clientes"""
        if command == "CREATE_ROOM":
            return self._create_room(request, client_address)
        elif command == "JOIN_ROOM":
            return self._join_room(request)
        elif command == "LIST_ROOMS":
            return self._list_rooms()
        elif command == "LEAVE_ROOM":
            return self._leave_room(request)
        elif command == "UPDATE_ROOM":
            return self._update_room(request)
        else:
            return {"status": "error", "message": f"Comando inválido: {command}"}
            
    def _create_room(self, request, client_address):
        """Cria uma nova sala"""
        host_name = request.get("host_name")
        room_name = request.get("room_name")
        password = request.get("password")
        host_port = request.get("host_port", 5555)
        
        if not host_name:
            return {"status": "error", "message": "Nome do host é obrigatório"}
            
        # Gera um ID único para a sala
        with self.lock:
            room_id = self.generate_room_id()
            while room_id in self.rooms:
                room_id = self.generate_room_id()
            
            # Usa o endereço IP do cliente como endereço de host
            client_ip = client_address[0]
            host_address = f"{client_ip}:{host_port}"
            
            # Cria a sala
            room = {
                "room_id": room_id,
                "host_name": host_name,
                "host_address": host_address,
                "players": [host_name],
                "room_name": room_name or f"Sala de {host_name}",
                "has_password": password is not None and password != "",
                "password": password,
                "created_at": time.time()
            }
            
            self.rooms[room_id] = room
            
        print(f"Sala criada: {room_id} por {host_name} em {host_address}")
            
        # Retorna uma cópia da sala sem a senha
        room_copy = room.copy()
        if "password" in room_copy:
            del room_copy["password"]
            
        return {
            "status": "success",
            "room_id": room_id,
            "room": room_copy
        }
        
    def _join_room(self, request):
        """Permite que um jogador entre em uma sala"""
        room_id = request.get("room_id")
        player_name = request.get("player_name")
        password = request.get("password")
        
        if not room_id or not player_name:
            return {"status": "error", "message": "ID da sala e nome do jogador são obrigatórios"}
        
        with self.lock:
            if room_id not in self.rooms:
                return {"status": "error", "message": "Sala não encontrada"}
                
            room = self.rooms[room_id]
            
            # Verifica a senha se necessário
            if room.get("has_password", False) and room.get("password") != password:
                return {"status": "error", "message": "Senha incorreta"}
                
            # Adiciona o jogador à sala se ainda não estiver
            if player_name not in room["players"]:
                room["players"].append(player_name)
                print(f"Jogador {player_name} entrou na sala {room_id}")
                
            # Retorna uma cópia da sala sem a senha
            room_copy = room.copy()
            if "password" in room_copy:
                del room_copy["password"]
                
        return {
            "status": "success",
            "room": room_copy
        }
        
    def _list_rooms(self):
        """Lista todas as salas disponíveis"""
        # Filtra salas antigas (mais de 30 minutos)
        current_time = time.time()
        active_rooms = []
        
        with self.lock:
            for room_id, room in self.rooms.items():
                if current_time - room["created_at"] < 1800:  # 30 minutos
                    # Cria uma cópia da sala sem a senha
                    room_copy = room.copy()
                    if "password" in room_copy:
                        del room_copy["password"]
                    active_rooms.append(room_copy)
                
        return {
            "status": "success",
            "rooms": active_rooms
        }
        
    def _leave_room(self, request):
        """Remove um jogador de uma sala"""
        room_id = request.get("room_id")
        player_name = request.get("player_name")
        
        if not room_id or not player_name:
            return {"status": "error", "message": "ID da sala e nome do jogador são obrigatórios"}
        
        with self.lock:
            if room_id not in self.rooms:
                return {"status": "error", "message": "Sala não encontrada"}
                
            room = self.rooms[room_id]
            
            # Remove o jogador da sala
            if player_name in room["players"]:
                room["players"].remove(player_name)
                print(f"Jogador {player_name} saiu da sala {room_id}")
                
            # Se não houver mais jogadores, remove a sala
            if not room["players"]:
                del self.rooms[room_id]
                print(f"Sala {room_id} removida (sem jogadores)")
                return {"status": "success", "message": "Sala removida"}
                
            # Se o host saiu, define o próximo jogador como host
            if player_name == room["host_name"] and room["players"]:
                room["host_name"] = room["players"][0]
                print(f"Novo host da sala {room_id}: {room['host_name']}")
                
        return {"status": "success", "message": "Jogador removido da sala"}
        
    def _update_room(self, request):
        """Atualiza informações de uma sala"""
        room_id = request.get("room_id")
        players = request.get("players")
        
        if not room_id:
            return {"status": "error", "message": "ID da sala é obrigatório"}
        
        with self.lock:
            if room_id not in self.rooms:
                return {"status": "error", "message": "Sala não encontrada"}
                
            room = self.rooms[room_id]
            
            # Atualiza a lista de jogadores
            if players is not None:
                room["players"] = players
                print(f"Lista de jogadores atualizada para sala {room_id}")
                
            # Retorna uma cópia da sala sem a senha
            room_copy = room.copy()
            if "password" in room_copy:
                del room_copy["password"]
                
        return {
            "status": "success",
            "room": room_copy
        }
        
    def _cleanup_old_rooms(self):
        """Remove salas antigas periodicamente"""
        while self.running:
            time.sleep(60)  # Verifica a cada minuto
            
            current_time = time.time()
            room_ids_to_remove = []
            
            with self.lock:
                for room_id, room in self.rooms.items():
                    if current_time - room["created_at"] > 1800:  # 30 minutos
                        room_ids_to_remove.append(room_id)
                        
                for room_id in room_ids_to_remove:
                    del self.rooms[room_id]
                    
            if room_ids_to_remove:
                print(f"Removidas {len(room_ids_to_remove)} salas antigas")

def main():
    """Função principal para iniciar o servidor como um programa independente"""
    parser = argparse.ArgumentParser(description="Servidor de Lobby para Blackjack P2P")
    parser.add_argument("--host", default="0.0.0.0", help="Endereço IP do servidor (padrão: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5000, help="Porta do servidor (padrão: 5000)")
    
    args = parser.parse_args()
    
    server = LobbyServer(host=args.host, port=args.port)
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nServidor interrompido manualmente")
    finally:
        server.stop()

if __name__ == "__main__":
    main()
