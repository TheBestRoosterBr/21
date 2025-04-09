import uuid
import socket

import pygame

from client.player_data import get_player_balance
from server.matchmaking import MatchmakingService
from shared import config
from shared.models.game import Game
from shared.models.player import Player
from shared.network.message import Message, MessageType, ActionType
from shared.network.p2p_manager import P2PManager


def on_player_connected(player_id, player_data):
    """Callback para quando um novo jogador se conecta"""
    print(f"Jogador conectado: {player_id}")


class Room:
    def __init__(self, screen, player_name, player_balance, view_manager):
        """Inicializar a sala"""
        self.screen = screen
        self.player_name = player_name
        self.player_balance = player_balance
        self.view_manager = view_manager
        
        # Dados da sala
        self.room_id = None
        self.room_name = "Sala Nova"
        self.room_name_input = ""
        self.password_input = ""
        self.room_name_input_active = False
        self.password_input_active = False
        self.host_name = ""
        self.host_address = ""
        self.host_mode = False
        self.game = None
        self.game_state = None
        
        # Lista de salas
        self.room_list = []
        self.selected_room_index = -1
        self.joining_room_id = ""
        self.room_list_status = ""
        
        # Fontes
        self.title_font = pygame.font.SysFont("Arial", 48)
        self.large_font = pygame.font.SysFont("Arial", 32)
        self.medium_font = pygame.font.SysFont("Arial", 24)
        self.small_font = pygame.font.SysFont("Arial", 18)
        
        # Jogador
        self.player = None
        
        # Matchmaking e rede
        self.matchmaking_service = None
        self.p2p_manager = None

    def render_create_room(self):
        """Renderizar a tela de criação de sala"""
        # Background
        self.screen.fill(config.GREEN)
        
        # Título
        title = self.large_font.render("Criar Nova Sala", True, config.WHITE)
        title_rect = title.get_rect(center=(config.SCREEN_WIDTH // 2, 50))
        self.screen.blit(title, title_rect)
        
        # Área do formulário
        form_width = 500
        form_height = 350
        form_x = config.SCREEN_WIDTH // 2 - form_width // 2
        form_y = 100
        
        # Painel do formulário
        pygame.draw.rect(self.screen, (0, 60, 0), (form_x, form_y, form_width, form_height), border_radius=10)
        pygame.draw.rect(self.screen, config.WHITE, (form_x, form_y, form_width, form_height), 2, border_radius=10)
        
        # Campo de nome da sala
        field_y = form_y + 40
        field_label = self.medium_font.render("Nome da Sala:", True, config.WHITE)
        self.screen.blit(field_label, (form_x + 30, field_y))
        
        # Campo de texto para o nome da sala
        input_field_width = form_width - 60
        input_field_height = 50
        room_name_field = pygame.Rect(form_x + 30, field_y + 40, input_field_width, input_field_height)
        
        # Desenhar o campo de entrada com cor baseada no foco
        field_color = (0, 100, 150) if self.room_name_input_active else (0, 80, 100)
        pygame.draw.rect(self.screen, field_color, room_name_field, border_radius=5)
        pygame.draw.rect(self.screen, config.WHITE, room_name_field, 2, border_radius=5)
        
        # Texto do nome da sala
        if self.room_name_input:
            room_name_text = self.medium_font.render(self.room_name_input, True, config.WHITE)
            # Limitar o texto para não sair do campo
            if room_name_text.get_width() > input_field_width - 20:
                visible_chars = 0
                for i in range(len(self.room_name_input)):
                    test_text = self.medium_font.render(self.room_name_input[-i:], True, config.WHITE)
                    if test_text.get_width() <= input_field_width - 20:
                        visible_chars = i
                        break
                room_name_text = self.medium_font.render(self.room_name_input[-visible_chars:], True, config.WHITE)
            self.screen.blit(room_name_text, (room_name_field.x + 10, room_name_field.y + 10))
        else:
            placeholder = self.medium_font.render("Digite o nome da sala", True, (150, 150, 150))
            self.screen.blit(placeholder, (room_name_field.x + 10, room_name_field.y + 10))
        
        # Campo de senha (opcional)
        field_y += 120
        password_label = self.medium_font.render("Senha (opcional):", True, config.WHITE)
        self.screen.blit(password_label, (form_x + 30, field_y))
        
        # Campo de texto para a senha
        password_field = pygame.Rect(form_x + 30, field_y + 40, input_field_width, input_field_height)
        
        # Desenhar o campo de entrada com cor baseada no foco
        field_color = (0, 100, 150) if self.password_input_active else (0, 80, 100)
        pygame.draw.rect(self.screen, field_color, password_field, border_radius=5)
        pygame.draw.rect(self.screen, config.WHITE, password_field, 2, border_radius=5)
        
        # Texto da senha (exibir asteriscos)
        if self.password_input:
            password_display = "*" * len(self.password_input)
            password_text = self.medium_font.render(password_display, True, config.WHITE)
            self.screen.blit(password_text, (password_field.x + 10, password_field.y + 10))
        else:
            placeholder = self.medium_font.render("Digite a senha (opcional)", True, (150, 150, 150))
            self.screen.blit(placeholder, (password_field.x + 10, password_field.y + 10))
        
        # Botões
        button_width = 200
        button_height = 60
        button_y = form_y + form_height + 50
        
        # Botão Criar
        create_button = pygame.Rect(config.SCREEN_WIDTH // 2 - button_width - 10, button_y, button_width, button_height)
        create_color = (0, 150, 0)  # Verde forte
        pygame.draw.rect(self.screen, create_color, create_button, border_radius=10)
        pygame.draw.rect(self.screen, config.WHITE, create_button, 2, border_radius=10)
        create_text = self.medium_font.render("Criar Sala", True, config.WHITE)
        create_text_rect = create_text.get_rect(center=create_button.center)
        self.screen.blit(create_text, create_text_rect)
        
        # Botão Cancelar
        cancel_button = pygame.Rect(config.SCREEN_WIDTH // 2 + 10, button_y, button_width, button_height)
        cancel_color = (150, 30, 30)  # Vermelho
        pygame.draw.rect(self.screen, cancel_color, cancel_button, border_radius=10)
        pygame.draw.rect(self.screen, config.WHITE, cancel_button, 2, border_radius=10)
        cancel_text = self.medium_font.render("Cancelar", True, config.WHITE)
        cancel_text_rect = cancel_text.get_rect(center=cancel_button.center)
        self.screen.blit(cancel_text, cancel_text_rect)
        
        # Cursor piscante
        cursor_visible = ((pygame.time.get_ticks() % 1000) < 500)
        if cursor_visible:
            if self.room_name_input_active and self.room_name_input:
                cursor_x = room_name_field.x + 10 + self.medium_font.render(self.room_name_input, True, config.WHITE).get_width()
                pygame.draw.line(self.screen, config.WHITE, (cursor_x, room_name_field.y + 10), 
                                (cursor_x, room_name_field.y + 40), 2)
            elif self.password_input_active and self.password_input:
                cursor_x = password_field.x + 10 + self.medium_font.render("*" * len(self.password_input), True, config.WHITE).get_width()
                pygame.draw.line(self.screen, config.WHITE, (cursor_x, password_field.y + 10), 
                                (cursor_x, password_field.y + 40), 2)

    def create_room(self):
        """Criar uma nova sala"""
        try:
            # Verifica se o nome da sala é válido
            if not self.room_name_input or len(self.room_name_input.strip()) < 3:
                print("Nome da sala deve ter pelo menos 3 caracteres")
                return False
            
            # Obtém o IP local
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            
            # Criar o jogador
            from shared.models.player import Player
            self.player = Player(self.player_name, self.player_balance, str(uuid.uuid4()))
            
            # Criar uma nova sala no serviço de matchmaking
            response = self.matchmaking_service.create_room(
                host_name=self.player_name,
                room_name=self.room_name_input,
                password=self.password_input if self.password_input else None,
                host_port=5555
            )
            
            if not response[0]:
                print(f"Erro ao criar sala: {response[1]}")
                return False
                
            room_data = response[1]
            self.room_id = room_data.get("room_id")
            
            # Inicializar P2P como host
            from shared.network.p2p_manager import P2PManager
            self.p2p_manager = P2PManager(host=True, port=5555)
            
            # Registrar callbacks
            self.p2p_manager.register_message_callback(self.on_message_received)
            self.p2p_manager.register_disconnection_callback(self.on_player_disconnected)
            
            # Iniciar o servidor P2P
            self.p2p_manager.start()
            
            # Inicializar o jogo
            from shared.models.game import Game
            self.game = Game()
            self.game.initialize_game(self.player)
            
            # Configurar como host
            self.host_mode = True
            
            # Garantir que o game_client tenha a referência do game_id e game
            if hasattr(self, 'game_client'):
                self.game_client.game_id = self.room_id
                self.game_client.game = self.game
                self.game_client.host_mode = True
                self.game_client.player = self.player
                self.game_client.game_state = self.game.get_game_state()
                self.game_client.p2p_manager = self.p2p_manager
            
            print(f"Sala criada com sucesso: ID {self.room_id}")
            
            # Inicializar mensagens do jogo se necessário
            if not hasattr(self.game, 'messages'):
                self.game.messages = []
            self.game.messages.append(f"Sala '{self.room_name_input}' criada por {self.player_name}")
            
            # Atualizar o estado do jogo
            self.game_state = self.game.get_game_state()
            
            # Mudar para a tela de lobby
            self.view_manager.set_view("LOBBY")
            
            return True
        except Exception as e:
            print(f"Erro ao criar sala: {e}")
            import traceback
            traceback.print_exc()
            return False

    def handle_create_room_event(self, event):
        """Lidar com eventos na tela de criação de sala"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            
            # Coordenadas do formulário
            form_width = 500
            form_height = 350
            form_x = config.SCREEN_WIDTH // 2 - form_width // 2
            form_y = 100
            input_field_width = form_width - 60
            input_field_height = 50
            
            # Verificar clique no campo de nome da sala
            field_y = form_y + 40
            room_name_field = pygame.Rect(form_x + 30, field_y + 40, input_field_width, input_field_height)
            self.room_name_input_active = room_name_field.collidepoint(mouse_pos)
            
            # Verificar clique no campo de senha
            field_y += 120
            password_field = pygame.Rect(form_x + 30, field_y + 40, input_field_width, input_field_height)
            self.password_input_active = password_field.collidepoint(mouse_pos)
            
            # Botões
            button_width = 200
            button_height = 60
            button_y = form_y + form_height + 50
            
            # Botão Criar
            create_button = pygame.Rect(config.SCREEN_WIDTH // 2 - button_width - 10, button_y, button_width, button_height)
            if create_button.collidepoint(mouse_pos):
                # Verificar dados e criar sala
                if self.create_room():
                    # Sala criada com sucesso
                    pass
                return
            
            # Botão Cancelar
            cancel_button = pygame.Rect(config.SCREEN_WIDTH // 2 + 10, button_y, button_width, button_height)
            if cancel_button.collidepoint(mouse_pos):
                self.view_manager.go_back()
                return
                
        elif event.type == pygame.KEYDOWN:
            # Pressionar Tab alterna entre os campos
            if event.key == pygame.K_TAB:
                self.room_name_input_active = not self.room_name_input_active
                self.password_input_active = not self.password_input_active
                
            # Pressionar Return/Enter confirma a criação
            elif event.key == pygame.K_RETURN:
                if self.create_room():
                    # Sala criada com sucesso
                    pass
                    
            # Pressionar Escape volta à tela anterior
            elif event.key == pygame.K_ESCAPE:
                self.view_manager.go_back()
                
            # Edição do texto nos campos ativos
            elif self.room_name_input_active:
                if event.key == pygame.K_BACKSPACE:
                    self.room_name_input = self.room_name_input[:-1]
                else:
                    # Limitar o tamanho do nome da sala
                    if len(self.room_name_input) < 20:
                        self.room_name_input += event.unicode
                        
            elif self.password_input_active:
                if event.key == pygame.K_BACKSPACE:
                    self.password_input = self.password_input[:-1]
                else:
                    # Limitar o tamanho da senha
                    if len(self.password_input) < 16:
                        self.password_input += event.unicode

    def reset_room_data(self):
        """Reseta os dados da sala"""
        self.room_name_input = ""
        self.password_input = ""
        self.room_id = None
        self.room_name_input_active = False
        self.password_input_active = False
        self.error_message = ""
        self.success_message = ""
        self.show_error = False
        self.show_success = False
        self.timer_redirect = None

    def render_join_room(self):
        """Renderizar a tela para juntar-se a uma sala específica usando o ID"""
        # Background com gradiente
        self.screen.fill((0, 40, 0))  # Verde escuro base

        # Área do título
        title_bg = pygame.Rect(0, 0, config.SCREEN_WIDTH, 120)
        pygame.draw.rect(self.screen, (0, 30, 0), title_bg)

        # Título
        title = self.title_font.render("Juntar-se a uma Sala", True, (240, 240, 240))
        title_rect = title.get_rect(center=(config.SCREEN_WIDTH // 2, 60))
        self.screen.blit(title, title_rect)

        # Área central
        form_width = 500
        form_height = 300
        form_x = config.SCREEN_WIDTH // 2 - form_width // 2
        form_y = 150

        form_bg = pygame.Rect(form_x, form_y, form_width, form_height)
        pygame.draw.rect(self.screen, (0, 60, 0), form_bg, border_radius=10)
        pygame.draw.rect(self.screen, (0, 100, 0), form_bg, 2, border_radius=10)

        y_offset = form_y + 30

        # ID da Sala
        id_label = self.medium_font.render("ID da Sala:", True, config.WHITE)
        self.screen.blit(id_label, (form_x + 30, y_offset))

        # Campo de entrada para o ID da sala
        id_box = pygame.Rect(form_x + 30, y_offset + 40, 440, 40)

        # Cor da borda baseada no estado de foco
        if self.room_id_input_active:
            id_border_color = (100, 200, 255)  # Azul quando ativo
        else:
            id_border_color = (0, 100, 0)  # Verde escuro padrão

        pygame.draw.rect(self.screen, id_border_color, id_box, border_radius=5)
        pygame.draw.rect(self.screen, (240, 240, 240), pygame.Rect(id_box.x + 2, id_box.y + 2,
                                                                   id_box.width - 4, id_box.height - 4),
                         border_radius=5)

        # Texto do ID da sala
        cursor = "|" if self.room_id_input_active and pygame.time.get_ticks() % 1000 < 500 else ""
        id_text = self.medium_font.render(self.room_id_input + cursor, True, (0, 0, 0))
        self.screen.blit(id_text, (id_box.x + 10, id_box.y + 5))

        y_offset += 100

        # Senha
        password_label = self.medium_font.render("Senha da Sala:", True, config.WHITE)
        self.screen.blit(password_label, (form_x + 30, y_offset))

        # Campo de entrada para a senha
        password_box = pygame.Rect(form_x + 30, y_offset + 40, 440, 40)

        # Cor da borda baseada no estado de foco
        if self.password_input_active:
            password_border_color = (100, 200, 255)  # Azul quando ativo
        else:
            password_border_color = (0, 100, 0)  # Verde escuro padrão

        pygame.draw.rect(self.screen, password_border_color, password_box, border_radius=5)
        pygame.draw.rect(self.screen, (240, 240, 240), pygame.Rect(password_box.x + 2, password_box.y + 2,
                                                                   password_box.width - 4, password_box.height - 4),
                         border_radius=5)

        # Texto da senha (mostrado como asteriscos)
        password_display = "*" * len(self.password_input)
        cursor = "|" if self.password_input_active and pygame.time.get_ticks() % 1000 < 500 else ""
        password_text = self.medium_font.render(password_display + cursor, True, (0, 0, 0))
        self.screen.blit(password_text, (password_box.x + 10, password_box.y + 5))

        password_info = self.small_font.render("Deixe em branco para salas sem senha", True, (200, 200, 200))
        self.screen.blit(password_info, (form_x + 30, y_offset + 90))

        y_offset += 120

        # Seleção de modo de conexão
        mode_label = self.medium_font.render("Modo de Conexão:", True, config.WHITE)
        self.screen.blit(mode_label, (form_x + 30, y_offset))

        # Opções de modo
        online_rect = pygame.Rect(form_x + 30, y_offset + 40, 200, 40)
        local_rect = pygame.Rect(form_x + 270, y_offset + 40, 200, 40)

        # Destacar a opção selecionada
        if self.view_manager.connection_mode == "online":
            pygame.draw.rect(self.screen, (0, 120, 210), online_rect, border_radius=5)
            pygame.draw.rect(self.screen, (0, 80, 0), local_rect, border_radius=5)
        else:
            pygame.draw.rect(self.screen, (0, 80, 0), online_rect, border_radius=5)
            pygame.draw.rect(self.screen, (0, 120, 210), local_rect, border_radius=5)

        # Texto dos botões
        online_text = self.medium_font.render("Online", True, config.WHITE)
        local_text = self.medium_font.render("Rede Local", True, config.WHITE)

        online_text_rect = online_text.get_rect(center=online_rect.center)
        local_text_rect = local_text.get_rect(center=local_rect.center)

        self.screen.blit(online_text, online_text_rect)
        self.screen.blit(local_text, local_text_rect)

        # Botões de ação
        button_width = 200
        button_height = 50
        button_y = 500

        # Botão Buscar Salas
        browse_button = pygame.Rect(config.SCREEN_WIDTH // 2 - 310, button_y, button_width, button_height)
        mouse_pos = pygame.mouse.get_pos()
        browse_color = (0, 130, 180) if browse_button.collidepoint(mouse_pos) else (0, 100, 150)
        pygame.draw.rect(self.screen, browse_color, browse_button, border_radius=10)
        pygame.draw.rect(self.screen, config.WHITE, browse_button, 2, border_radius=10)
        browse_text = self.medium_font.render("Lista de Salas", True, config.WHITE)
        browse_text_rect = browse_text.get_rect(center=browse_button.center)
        self.screen.blit(browse_text, browse_text_rect)

        # Botão Entrar
        join_button = pygame.Rect(config.SCREEN_WIDTH // 2 - 100, button_y, button_width, button_height)
        join_color = (0, 150, 0) if join_button.collidepoint(mouse_pos) else (0, 120, 0)
        pygame.draw.rect(self.screen, join_color, join_button, border_radius=10)

    def render_room_browser(self):
        """Renderizar o navegador de salas"""
        # Background
        self.screen.fill(config.GREEN)
        
        # Título
        title = self.large_font.render("Salas Disponíveis", True, config.WHITE)
        self.screen.blit(title, (config.SCREEN_WIDTH // 2 - title.get_width() // 2, 20))
        
        # Tipo de conexão
        if self.view_manager.connection_mode == "online":
            connection_text = self.medium_font.render("Modo Online", True, config.WHITE)
        else:
            connection_text = self.medium_font.render("Modo Local", True, config.WHITE)
        self.screen.blit(connection_text, (config.SCREEN_WIDTH - connection_text.get_width() - 20, 20))
        
        # Status
        status_text = self.medium_font.render(self.room_list_status, True, config.WHITE)
        self.screen.blit(status_text, (20, 80))
        
        # Lista de salas
        list_x = 40
        list_y = 130
        list_width = config.SCREEN_WIDTH - 80
        list_height = config.SCREEN_HEIGHT - 250
        
        # Fundo da lista
        pygame.draw.rect(self.screen, (0, 50, 0), (list_x, list_y, list_width, list_height))
        pygame.draw.rect(self.screen, config.WHITE, (list_x, list_y, list_width, list_height), 2)
        
        # Cabeçalho da lista
        header_height = 40
        pygame.draw.rect(self.screen, (0, 70, 0), (list_x, list_y, list_width, header_height))
        
        # Textos do cabeçalho
        headers = ["ID", "Nome da Sala", "Host", "Jogadores", "Senha"]
        header_widths = [80, 240, 180, 100, 80]
        header_x = list_x + 10
        
        for i, header in enumerate(headers):
            header_text = self.small_font.render(header, True, config.WHITE)
            self.screen.blit(header_text, (header_x, list_y + 10))
            header_x += header_widths[i]
        
        # Linhas da lista
        if self.room_list:
            visible_items = min(8, len(self.room_list))
            item_height = 50
            
            for i in range(visible_items):
                room = self.room_list[i]
                row_y = list_y + header_height + (i * item_height)
                
                # Destaque para a sala selecionada
                if i == self.selected_room_index:
                    pygame.draw.rect(self.screen, (0, 100, 0), (list_x, row_y, list_width, item_height))
                
                # Linha divisória
                pygame.draw.line(self.screen, (0, 80, 0), (list_x, row_y), (list_x + list_width, row_y))
                
                # Desenhar os dados da sala
                room_id = room.get("room_id", "N/A")
                room_name = room.get("room_name", "Sem nome")
                host_name = room.get("host_name", "Desconhecido")
                players = len(room.get("players", []))
                has_password = "Sim" if room.get("has_password", False) else "Não"
                
                # Textos da sala
                item_x = list_x + 10
                item_y = row_y + 15
                
                # ID
                id_text = self.small_font.render(str(room_id), True, config.WHITE)
                self.screen.blit(id_text, (item_x, item_y))
                item_x += header_widths[0]
                
                # Nome
                name_text = self.small_font.render(room_name, True, config.WHITE)
                self.screen.blit(name_text, (item_x, item_y))
                item_x += header_widths[1]
                
                # Host
                host_text = self.small_font.render(host_name, True, config.WHITE)
                self.screen.blit(host_text, (item_x, item_y))
                item_x += header_widths[2]
                
                # Jogadores
                players_text = self.small_font.render(str(players), True, config.WHITE)
                self.screen.blit(players_text, (item_x, item_y))
                item_x += header_widths[3]
                
                # Senha
                password_text = self.small_font.render(has_password, True, config.WHITE)
                self.screen.blit(password_text, (item_x, item_y))
        else:
            # Mensagem de nenhuma sala encontrada
            no_rooms_text = self.medium_font.render("Nenhuma sala encontrada", True, config.WHITE)
            no_rooms_x = list_x + (list_width // 2) - (no_rooms_text.get_width() // 2)
            no_rooms_y = list_y + (list_height // 2) - (no_rooms_text.get_height() // 2)
            self.screen.blit(no_rooms_text, (no_rooms_x, no_rooms_y))
        
        # Botões - Layout simplificado em linha
        button_y = list_y + list_height + 20
        button_width = 200
        button_height = 50
        total_width = button_width * 4 + 30  # 4 botões com 10px entre eles
        start_x = (config.SCREEN_WIDTH - total_width) // 2
        
        # Botão Criar Sala
        create_button = pygame.Rect(start_x, button_y, button_width, button_height)
        pygame.draw.rect(self.screen, (0, 150, 0), create_button, border_radius=10)
        pygame.draw.rect(self.screen, config.WHITE, create_button, 2, border_radius=10)
        create_text = self.medium_font.render("Criar Sala", True, config.WHITE)
        create_text_rect = create_text.get_rect(center=create_button.center)
        self.screen.blit(create_text, create_text_rect)
        
        # Botão de Entrar
        join_button = pygame.Rect(start_x + button_width + 10, button_y, button_width, button_height)
        join_color = (0, 120, 180) if self.selected_room_index >= 0 else (100, 100, 100)
        pygame.draw.rect(self.screen, join_color, join_button, border_radius=10)
        pygame.draw.rect(self.screen, config.WHITE, join_button, 2, border_radius=10)
        join_text = self.medium_font.render("Entrar", True, config.WHITE)
        join_text_rect = join_text.get_rect(center=join_button.center)
        self.screen.blit(join_text, join_text_rect)
        
        # Botão de Atualizar
        refresh_button = pygame.Rect(start_x + (button_width + 10) * 2, button_y, button_width, button_height)
        pygame.draw.rect(self.screen, (150, 100, 0), refresh_button, border_radius=10)
        pygame.draw.rect(self.screen, config.WHITE, refresh_button, 2, border_radius=10)
        refresh_text = self.medium_font.render("Atualizar", True, config.WHITE)
        refresh_text_rect = refresh_text.get_rect(center=refresh_button.center)
        self.screen.blit(refresh_text, refresh_text_rect)
        
        # Botão de Voltar
        back_button = pygame.Rect(start_x + (button_width + 10) * 3, button_y, button_width, button_height)
        pygame.draw.rect(self.screen, (180, 0, 0), back_button, border_radius=10)
        pygame.draw.rect(self.screen, config.WHITE, back_button, 2, border_radius=10)
        back_text = self.medium_font.render("Voltar", True, config.WHITE)
        back_text_rect = back_text.get_rect(center=back_button.center)
        self.screen.blit(back_text, back_text_rect)

    def handle_room_browser_event(self, event):
        """Lidar com eventos no navegador de salas"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            
            # Lista de salas
            list_x = 40
            list_y = 130
            list_width = config.SCREEN_WIDTH - 80
            list_height = config.SCREEN_HEIGHT - 250
            header_height = 40
            
            # Verificar cliques na lista
            if (list_x <= mouse_pos[0] <= list_x + list_width and
                list_y + header_height <= mouse_pos[1] <= list_y + list_height):
                
                # Calcular o índice da sala clicada
                item_height = 50
                clicked_index = (mouse_pos[1] - (list_y + header_height)) // item_height
                
                if self.room_list and 0 <= clicked_index < len(self.room_list):
                    self.selected_room_index = clicked_index
                    print(f"Sala selecionada: {self.room_list[self.selected_room_index].get('room_name', 'Sem nome')}")
            
            # Botões - Layout em linha
            button_y = list_y + list_height + 20
            button_width = 200
            button_height = 50
            total_width = button_width * 4 + 30  # 4 botões com 10px entre eles
            start_x = (config.SCREEN_WIDTH - total_width) // 2
            
            # Botão Criar Sala
            create_button = pygame.Rect(start_x, button_y, button_width, button_height)
            if create_button.collidepoint(mouse_pos):
                self.view_manager.set_view("CREATE_ROOM")
                self.reset_room_data()
                return
            
            # Botão de Entrar
            join_button = pygame.Rect(start_x + button_width + 10, button_y, button_width, button_height)
            if join_button.collidepoint(mouse_pos) and self.selected_room_index >= 0:
                self.join_selected_room(self.selected_room_index)
                return
            
            # Botão de Atualizar
            refresh_button = pygame.Rect(start_x + (button_width + 10) * 2, button_y, button_width, button_height)
            if refresh_button.collidepoint(mouse_pos):
                self.load_room_list(mode=self.view_manager.connection_mode)
                return
            
            # Botão de Voltar
            back_button = pygame.Rect(start_x + (button_width + 10) * 3, button_y, button_width, button_height)
            if back_button.collidepoint(mouse_pos):
                self.view_manager.go_back()
                return

    def load_room_list(self, mode="online"):
        """Carregar lista de salas disponíveis"""
        # Save current selection index and room ID if any
        selected_room_id = None
        if self.room_list and self.selected_room_index >= 0 and self.selected_room_index < len(self.room_list):
            selected_room_id = self.room_list[self.selected_room_index].get("room_id", None)
            
        self.room_list = []
        self.room_list_status = "Carregando..."
        
        if mode == "online":
            try:
                # Obter lista de salas do serviço de matchmaking
                success, response = self.matchmaking_service.list_games()
                
                if not success:
                    self.room_list_status = f"Erro ao carregar salas: {response}"
                    return
                    
                # Verificar se há salas disponíveis
                if "rooms" in response and response["rooms"]:
                    # Processar cada sala
                    for room in response["rooms"]:
                        # Adiciona o id na room para compatibilidade
                        room["id"] = room["room_id"]
                        self.room_list.append(room)
                    
                    # Atualizar status
                    self.room_list_status = f"{len(self.room_list)} sala(s) encontrada(s)"
                else:
                    self.room_list_status = "Nenhuma sala disponível"
            except Exception as e:
                self.room_list_status = f"Erro: {str(e)}"
                import traceback
                traceback.print_exc()
        else:
            # Modo local para testes
            self.room_list_status = "Modo local - teste apenas"
            # Adicionar algumas salas de teste
            self.room_list = [
                {
                    "id": "1234",
                    "room_id": "1234",
                    "host_name": "Jogador Local",
                    "room_name": "Sala Local 1",
                    "players": ["Jogador Local"],
                    "has_password": False
                }
            ]
            
        # Try to restore previous selection if possible
        if selected_room_id:
            for i, room in enumerate(self.room_list):
                if room.get("room_id") == selected_room_id or room.get("id") == selected_room_id:
                    self.selected_room_index = i
                    break
            else:
                self.selected_room_index = -1
        else:
            self.selected_room_index = -1

    def join_selected_room(self, room_index):
        """Entrar na sala selecionada"""
        if self.room_list and 0 <= room_index < len(self.room_list):
            selected_room = self.room_list[room_index]
            room_id = selected_room.get("room_id", selected_room.get("id"))
            has_password = selected_room.get("has_password", False)
            
            # Se a sala tiver senha, exibir prompt de senha
            if has_password:
                self.joining_room_id = room_id
                self.view_manager.set_view("JOIN_ROOM")
                return
                
            # Se não tiver senha, conectar diretamente
            if self.view_manager.connection_mode == "online":
                success = self.connect_to_online_room(room_id)
                if success:
                    self.view_manager.set_view("LOBBY")
                else:
                    print("Falha ao conectar à sala online")
            else:
                success = self.connect_to_local_room(room_id)
                if success:
                    self.view_manager.set_view("LOBBY")
                else:
                    print("Falha ao conectar à sala local")

    def connect_to_online_room(self, room_id, password=""):
        """Conectar-se a uma sala online"""
        try:
            # Verificar se a sala existe
            join_response = self.matchmaking_service.join_room(
                room_id=room_id,
                player_name=self.player_name,
                password=password
            )
            
            if not join_response[0]:
                print(f"Erro ao entrar na sala: {join_response[1]}")
                return False
                
            room_data = join_response[1].get("room", {})
            self.room_id = room_id
            self.room_name = room_data.get("room_name", f"Sala {room_id}")
            self.host_name = room_data.get("host_name", "Desconhecido")
            self.host_address = room_data.get("host_address", "")
            
            # Se for o host, não precisa se conectar
            if self.host_name == self.player_name:
                print("Você é o host desta sala.")
                return True
                
            # Extrair IP e porta do endereço do host
            if ":" in self.host_address:
                host_ip, host_port_str = self.host_address.split(":")
                host_port = int(host_port_str)
            else:
                print("Formato de endereço de host inválido")
                return False
                
            # Criar jogador
            from shared.models.player import Player
            self.player = Player(self.player_name, self.player_balance, str(uuid.uuid4()))
            
            # Inicializar o gerenciador P2P como cliente
            from shared.network.p2p_manager import P2PManager
            self.p2p_manager = P2PManager(host=False, port=host_port)
            
            # Registrar callbacks
            self.p2p_manager.register_message_callback(self.on_message_received)
            self.p2p_manager.register_disconnection_callback(self.on_player_disconnected)
            
            # Conectar ao host
            success, message = self.p2p_manager.connect_to_host(host_ip)
            if not success:
                print(f"Falha ao conectar ao host: {message}")
                return False
            
            # Enviar mensagem de conexão
            from shared.network.message import Message, MessageType
            connection_message = Message(
                msg_type=MessageType.JOIN_REQUEST,
                sender_id=self.player.player_id,
                content={
                    "player_id": self.player.player_id,
                    "player_name": self.player_name,
                    "balance": self.player_balance
                }
            )
            
            self.p2p_manager.send_message(connection_message)
            
            print(f"Conectado à sala {room_id} em {host_ip}:{host_port}")
            
            # Entrar na sala (lobby)
            self.view_manager.set_view("LOBBY")
            
            # Garantir que o game_client tenha a referência do game_id
            if hasattr(self, 'game_client'):
                self.game_client.game_id = room_id
            
            return True
            
        except Exception as e:
            print(f"Erro ao conectar à sala online: {e}")
            import traceback
            traceback.print_exc()
            return False

    def connect_to_local_room(self, room_id, password=""):
        """Conectar a uma sala na rede local usando o ID da sala"""
        # Verificar se o ID da sala foi informado
        if not room_id:
            self.error_message = "ID da sala não informado"
            self.message_timer = pygame.time.get_ticks()
            return False

        # Obter informações da sala localmente via broadcast UDP
        success, room_info = self.matchmaking_service.get_local_room_info(room_id)
        if not success:
            self.error_message = "Sala não encontrada na rede local"
            self.message_timer = pygame.time.get_ticks()
            return False

        # Verificar senha se necessário
        if room_info.get("has_password", False) and room_info.get("password") != password:
            self.error_message = "Senha incorreta"
            self.message_timer = pygame.time.get_ticks()
            return False

        # Obter endereço do host
        host_address = room_info.get("host_address")
        if not host_address:
            self.error_message = "Endereço do host não disponível"
            self.message_timer = pygame.time.get_ticks()
            return False

        # Configurar conexão P2P como cliente
        self.p2p_manager = P2PManager(host=False, port=5555)
        self.p2p_manager.register_message_callback(self.on_message_received)
        self.p2p_manager.register_connection_callback(on_player_connected)
        self.p2p_manager.register_disconnection_callback(self.on_player_disconnected)
        self.p2p_manager.start()

        # Conectar ao host
        connect_success, connection_message = self.p2p_manager.connect_to_host(host_address)
        if not connect_success:
            self.error_message = f"Erro ao conectar ao host: {connection_message}"
            self.message_timer = pygame.time.get_ticks()
            return False

        # Enviar solicitação para entrar na sala
        join_message = Message.create_join_request(
            self.player.player_id,
            self.player.name
        )
        self.p2p_manager.send_message(join_message)

        # Registrar entrada no jogo local
        self.matchmaking_service.join_local_game(room_id, self.player_name)

        # Aguardar resposta do host (será tratada em on_message_received)
        self.room_id = room_id
        return True

    def handle_join_room_event(self, event):
        """Manipular eventos na tela de juntar-se a uma sala"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            form_x = config.SCREEN_WIDTH // 2 - 250
            form_y = 150

            # Ativar/desativar campos de entrada
            # Campo ID da Sala
            id_box = pygame.Rect(form_x + 30, form_y + 70, 440, 40)
            if id_box.collidepoint(mouse_pos):
                self.room_id_input_active = True
                self.password_input_active = False

            # Campo Senha
            password_box = pygame.Rect(form_x + 30, form_y + 170, 440, 40)
            if password_box.collidepoint(mouse_pos):
                self.password_input_active = True
                self.room_id_input_active = False

            # Botões de modo de conexão
            y_offset = form_y + 250
            online_rect = pygame.Rect(form_x + 30, y_offset + 40, 200, 40)
            local_rect = pygame.Rect(form_x + 270, y_offset + 40, 200, 40)

            if online_rect.collidepoint(mouse_pos):
                self.view_manager.connection_mode = "online"
            elif local_rect.collidepoint(mouse_pos):
                self.view_manager.connection_mode = "local"

            # Botão Buscar Salas
            button_width = 200
            button_height = 50
            button_y = 500
            browse_button = pygame.Rect(config.SCREEN_WIDTH // 2 - 310, button_y, button_width, button_height)
            if browse_button.collidepoint(mouse_pos):
                self.view_manager.set_view("ROOM_BROWSER")
                self.view_manager.connection_mode = self.view_manager.connection_mode
                self.load_room_list(mode=self.view_manager.connection_mode)
                return

            # Botão Entrar
            join_button = pygame.Rect(config.SCREEN_WIDTH // 2 - 100, button_y, button_width, button_height)
            if join_button.collidepoint(mouse_pos):
                self.join_room_by_id()
                return

            # Botão Cancelar
            cancel_button = pygame.Rect(config.SCREEN_WIDTH // 2 + 110, button_y, button_width, button_height)
            if cancel_button.collidepoint(mouse_pos):
                self.view_manager.set_view("MENU")
                return

        # Entrada de teclado para os campos ativos
        elif event.type == pygame.KEYDOWN:
            if self.room_id_input_active:
                if event.key == pygame.K_BACKSPACE:
                    self.room_id_input = self.room_id_input[:-1]
                elif event.key == pygame.K_RETURN:
                    self.room_id_input_active = False
                elif len(self.room_id_input) < 8:  # Limitar tamanho do ID
                    if event.unicode.isdigit():  # Aceitar apenas dígitos
                        self.room_id_input += event.unicode
            elif self.password_input_active:
                if event.key == pygame.K_BACKSPACE:
                    self.password_input = self.password_input[:-1]
                elif event.key == pygame.K_RETURN:
                    self.password_input_active = False
                elif len(self.password_input) < 20:  # Limitar tamanho da senha
                    if event.unicode.isprintable():
                        self.password_input += event.unicode

    def join_room_by_id(self):
        """Entrar na sala usando o ID digitado"""
        if not self.room_id_input:
            self.error_message = "Digite o ID da sala"
            self.message_timer = pygame.time.get_ticks()
            return

        # Criar o jogador
        self.player = Player(self.player_name, self.player_balance, str(uuid.uuid4()))

        # Conectar à sala baseado no modo selecionado
        success = False
        if self.view_manager.connection_mode == "online":
            success = self.connect_to_online_room(self.room_id_input, self.password_input)
        else:
            success = self.connect_to_local_room(self.room_id_input, self.password_input)

        if success:
            self.view_manager.set_view("LOBBY")
            self.host_mode = False
            self.success_message = "Conectado à sala com sucesso!"
            self.message_timer = pygame.time.get_ticks()
        else:
            # Mensagem de erro será definida pelas funções de conexão
            self.message_timer = pygame.time.get_ticks()

    def handle_find_rooms_click(self):
        """Manipular clique no botão Buscar Salas"""
        if not self.player_name:
            self.player_name = "Player"
            self.player_balance = get_player_balance(self.player_name)
        self.view_manager.set_view("JOIN_ROOM")
        self.room_id_input = ""
        self.room_id_input_active = True
        self.password_input = ""
        self.password_input_active = False
        self.view_manager.connection_mode = "online"  # Padrão: online

    def on_message_received(self, sender_id, message):
        """Processar mensagens recebidas de outros jogadores"""
        try:
            from shared.network.message import MessageType
            
            # Processar mensagem com base no tipo
            if message.msg_type == MessageType.JOIN_REQUEST:
                # Novo jogador se conectou
                player_data = message.content
                player_name = player_data.get("player_name", "Jogador Desconhecido")
                player_balance = player_data.get("balance", 1000)
                
                # Se somos o host, adicionar o jogador ao jogo
                if self.host_mode and self.game:
                    from shared.models.player import Player
                    new_player = Player(player_name, player_balance, sender_id)
                    self.game.add_player(new_player)
                    self.game_state = self.game.get_game_state()
                    
                    # Enviar mensagem de boas-vindas
                    if hasattr(self.game, "messages"):
                        self.game.messages.append(f"{player_name} entrou na sala!")
                    
                    # Enviar o estado atualizado do jogo para todos
                    self.broadcast_game_state()
                    
                if hasattr(self, 'game_client'):
                    # Atualizar a lista de mensagens no cliente
                    if not hasattr(self.game_client, 'messages'):
                        self.game_client.messages = []
                    self.game_client.messages.append(f"{player_name} entrou na sala!")
                
            elif message.msg_type == MessageType.PLAYER_ACTION:
                # Processar ação do jogador
                if self.host_mode and self.game:
                    action = message.content.get("action")
                    if action == "HIT":
                        success, msg = self.game.hit(sender_id)
                        if success and hasattr(self.game, "messages"):
                            self.game.messages.append(msg)
                    elif action == "STAND":
                        success, msg = self.game.stand(sender_id)
                        if success and hasattr(self.game, "messages"):
                            self.game.messages.append(msg)
                    elif action == "PLACE_BET":
                        bet_amount = message.content.get("amount", 0)
                        success, msg = self.game.place_bet(sender_id, bet_amount)
                        if success:
                            player = next((p for p in self.game.state_manager.players if p.player_id == sender_id), None)
                            if player and hasattr(self.game, "messages"):
                                self.game.messages.append(f"{player.name} apostou {bet_amount}")
                    
                    # Atualizar o estado do jogo
                    self.game_state = self.game.get_game_state()
                    
                    # Verificar se todos os jogadores fizeram suas apostas
                    if self.game_state["state"] == "BETTING" and all(p["current_bet"] > 0 for p in self.game_state["players"]):
                        self.game._deal_initial_cards()
                        self.game_state = self.game.get_game_state()
                    
                    # Enviar estado atualizado para todos
                    self.broadcast_game_state()
                    
            elif message.msg_type == MessageType.GAME_STATE:
                # Atualizar estado do jogo recebido do host
                self.game_state = message.content
                
                # Passar o estado para o game_client se estiver disponível
                if hasattr(self, 'game_client'):
                    self.game_client.game_state = self.game_state
                    
                    # Se o jogo começou, mudar para a tela de jogo
                    if self.game_state.get("state") != "LOBBY":
                        self.view_manager.set_view("GAME")
            
            # Não precisamos de REQUEST_UPDATE, usaremos o sistema existente
                    
        except Exception as e:
            print(f"Erro ao processar mensagem: {e}")
            import traceback
            traceback.print_exc()

    def on_player_disconnected(self, player_id):
        """Callback para quando um jogador se desconecta"""
        print(f"Jogador desconectado: {player_id}")

        # Se somos o host, remover o jogador do jogo
        if self.host_mode and self.game:
            self.game.remove_player(player_id)
            self.broadcast_game_state()
            
    def leave_lobby(self):
        """Sair da sala atual"""
        try:
            # Se estiver conectado ao serviço de matchmaking, notificar saída
            if hasattr(self, 'room_id') and self.room_id and hasattr(self, 'matchmaking_service'):
                try:
                    self.matchmaking_service.leave_room(self.room_id, self.player_name)
                except Exception as e:
                    print(f"Erro ao notificar saída no matchmaking: {e}")
            
            # Fechar as conexões P2P se existirem
            if hasattr(self, 'p2p_manager') and self.p2p_manager:
                try:
                    # Enviar mensagem de desconexão se possível
                    if hasattr(self, 'player') and self.player:
                        from shared.network.message import Message, MessageType
                        # Na versão atual não há tipo DISCONNECT, informamos com um JOIN_REQUEST negativo
                        # que mantém compatibilidade com a implementação atual
                        disconnect_message = Message(
                            msg_type=MessageType.JOIN_REQUEST,
                            sender_id=self.player.player_id,
                            content={
                                "player_id": self.player.player_id,
                                "player_name": self.player_name,
                                "leaving": True
                            }
                        )
                        self.p2p_manager.send_message(disconnect_message)
                    
                    # Fechar conexões
                    self.p2p_manager.close()
                except Exception as e:
                    print(f"Erro ao fechar conexões P2P: {e}")
            
            # Limpar dados da sala
            self.room_id = None
            self.host_mode = False
            self.game_state = None
            self.p2p_manager = None
            
            # Atualizar o cliente do jogo
            if hasattr(self, 'game_client'):
                self.game_client.game = None
                self.game_client.game_state = None
                self.game_client.host_mode = False
                self.game_client.p2p_manager = None
            
            # Voltar para o menu principal
            self.view_manager.set_view("MENU")
            
        except Exception as e:
            print(f"Erro ao sair da sala: {e}")
            import traceback
            traceback.print_exc()
            # Mesmo com erro, tentar voltar ao menu
            self.view_manager.set_view("MENU")

    def broadcast_game_state(self):
        """Enviar o estado atual do jogo para todos os jogadores conectados"""
        if not hasattr(self, 'p2p_manager') or not self.p2p_manager:
            return
            
        # Só o host pode enviar o estado do jogo para todos
        if self.host_mode and hasattr(self, 'game') and self.game:
            # Obter o estado atualizado do jogo
            game_state = self.game.get_game_state()
            
            # Atualizar o estado local
            self.game_state = game_state
            
            # Atualizar o cliente do jogo se disponível
            if hasattr(self, 'game_client'):
                self.game_client.game_state = game_state
                
            # Se o p2p manager estiver disponível, enviar para todos os jogadores
            from shared.network.message import Message, MessageType
            game_state_message = Message(
                msg_type=MessageType.GAME_STATE,
                sender_id=self.player.player_id,
                content=game_state
            )
            
            # Broadcast para todos os jogadores conectados
            self.p2p_manager.send_message(game_state_message)
            
            # Também atualizar o estado no serviço de matchmaking se estiver no modo online
            if self.view_manager.connection_mode == "online" and self.room_id:
                players = [p["name"] for p in game_state["players"]]
                try:
                    self.matchmaking_service.update_room(self.room_id, players)
                except Exception as e:
                    print(f"Erro ao atualizar sala no matchmaking: {e}")
        
        # Se for cliente, não faz broadcast, apenas atualiza o estado local
        elif hasattr(self, 'game_state') and self.game_state:
            # Atualizar o cliente do jogo
            if hasattr(self, 'game_client'):
                self.game_client.game_state = self.game_state

    def render_lobby(self):
        """Renderizar a tela de lobby/sala de espera"""
        # Background
        self.screen.fill(config.GREEN)
        
        # Título com nome da sala
        title = self.large_font.render(f"Sala: {self.room_name}", True, config.WHITE)
        self.screen.blit(title, (config.SCREEN_WIDTH // 2 - title.get_width() // 2, 20))
        
        # Informações da sala
        room_info_lines = [
            f"ID da Sala: {self.room_id}",
            f"Host: {self.host_name}",
            f"Senha: {'Sim' if hasattr(self, 'password_input') and self.password_input else 'Não'}"
        ]
        
        for i, line in enumerate(room_info_lines):
            info_text = self.medium_font.render(line, True, config.WHITE)
            self.screen.blit(info_text, (30, 80 + i * 35))
        
        # Título da lista de jogadores
        players_title = self.medium_font.render("Jogadores na Sala:", True, config.WHITE)
        self.screen.blit(players_title, (30, 200))
        
        # Lista de jogadores
        player_list_x = 50
        player_list_y = 250
        player_list_width = 400
        player_list_height = 300
        
        # Painel de jogadores
        pygame.draw.rect(self.screen, (0, 70, 0), (player_list_x, player_list_y, 
                                               player_list_width, player_list_height))
        pygame.draw.rect(self.screen, config.WHITE, (player_list_x, player_list_y, 
                                               player_list_width, player_list_height), 2)
        
        # Obter a lista atualizada de jogadores
        connected_players = []
        
        # Para o host, obtemos os jogadores do jogo
        if self.host_mode and hasattr(self, 'game') and self.game:
            for player in self.game.state_manager.players:
                connected_players.append(player.name)
        # Para clientes, usamos o estado do jogo
        elif hasattr(self, 'game_state') and self.game_state:
            for player in self.game_state.get("players", []):
                connected_players.append(player["name"])
        
        # Se ainda estiver vazia, pelo menos mostrar o jogador atual
        if not connected_players:
            connected_players.append(self.player_name)
        
        # Desenhar lista de jogadores
        for i, player_name in enumerate(connected_players):
            # Destaque para o host
            is_host = player_name == self.host_name
            player_color = (255, 215, 0) if is_host else config.WHITE  # Dourado para host
            
            player_text = self.medium_font.render(player_name, True, player_color)
            player_y = player_list_y + 20 + i * 40
            
            # Coroa para o host
            if is_host:
                host_icon = self.medium_font.render("👑", True, (255, 215, 0))
                self.screen.blit(host_icon, (player_list_x + 20, player_y))
                self.screen.blit(player_text, (player_list_x + 60, player_y))
            else:
                self.screen.blit(player_text, (player_list_x + 20, player_y))
        
        # Caixa de chat/mensagens
        chat_x = player_list_x + player_list_width + 50
        chat_y = player_list_y
        chat_width = config.SCREEN_WIDTH - chat_x - 50
        chat_height = player_list_height
        
        # Painel de chat
        pygame.draw.rect(self.screen, (0, 50, 0), (chat_x, chat_y, chat_width, chat_height))
        pygame.draw.rect(self.screen, config.WHITE, (chat_x, chat_y, chat_width, chat_height), 2)
        
        # Título do chat
        chat_title = self.medium_font.render("Mensagens", True, config.WHITE)
        chat_title_rect = chat_title.get_rect(midtop=(chat_x + chat_width // 2, chat_y + 10))
        self.screen.blit(chat_title, chat_title_rect)
        
        # Mensagens (se existirem)
        message_y = chat_y + 50
        if hasattr(self, 'messages') and self.messages:
            for message in self.messages[-8:]:  # Mostrar até 8 mensagens mais recentes
                message_text = self.small_font.render(message, True, config.WHITE)
                # Limitar tamanho da mensagem
                if message_text.get_width() > chat_width - 30:
                    # Truncar texto
                    words = message.split()
                    current_line = ""
                    for word in words:
                        test_line = current_line + " " + word if current_line else word
                        test_text = self.small_font.render(test_line, True, config.WHITE)
                        if test_text.get_width() <= chat_width - 30:
                            current_line = test_line
                        else:
                            rendered_line = self.small_font.render(current_line, True, config.WHITE)
                            self.screen.blit(rendered_line, (chat_x + 15, message_y))
                            message_y += 25
                            current_line = word
                    
                    # Renderizar a última linha se houver
                    if current_line:
                        rendered_line = self.small_font.render(current_line, True, config.WHITE)
                        self.screen.blit(rendered_line, (chat_x + 15, message_y))
                        message_y += 25
                else:
                    self.screen.blit(message_text, (chat_x + 15, message_y))
                    message_y += 25
        
        # Botões
        button_y = chat_y + chat_height + 30
        button_width = 250
        button_height = 60
        
        # Botão de Iniciar Jogo (apenas para o host)
        if self.host_mode:
            start_button = pygame.Rect(config.SCREEN_WIDTH // 2 - button_width - 20, button_y, 
                                      button_width, button_height)
            start_color = (0, 150, 0)
            pygame.draw.rect(self.screen, start_color, start_button, border_radius=10)
            pygame.draw.rect(self.screen, config.WHITE, start_button, 2, border_radius=10)
            start_text = self.medium_font.render("Iniciar Jogo", True, config.WHITE)
            start_text_rect = start_text.get_rect(center=start_button.center)
            self.screen.blit(start_text, start_text_rect)
        
        # Botão de Sair da Sala
        leave_button = pygame.Rect(config.SCREEN_WIDTH // 2 + 20, button_y, 
                                  button_width, button_height)
        leave_color = (180, 0, 0)
        pygame.draw.rect(self.screen, leave_color, leave_button, border_radius=10)
        pygame.draw.rect(self.screen, config.WHITE, leave_button, 2, border_radius=10)
        leave_text = self.medium_font.render("Sair da Sala", True, config.WHITE)
        leave_text_rect = leave_text.get_rect(center=leave_button.center)
        self.screen.blit(leave_text, leave_text_rect)

    def process_player_action(self, player_id, action_data):
        """Processar uma ação de jogador (host)"""
        action_type = action_data["action_type"]
        action_data = action_data["action_data"]

        if action_type == ActionType.PLACE_BET:
            success, message = self.game.place_bet(player_id, action_data["amount"])
        elif action_type == ActionType.HIT:
            success, message = self.game.hit(player_id)
        elif action_type == ActionType.STAND:
            success, message = self.game.stand(player_id)
        else:
            success, message = False, "Ação desconhecida"

        # Adicionar mensagem ao jogo
        if success:
            self.game.messages.append(message)

        # Atualizar estado do jogo para todos
        self.broadcast_game_state()

    def start_game(self):
        """Iniciar o jogo"""
        try:
            if not self.host_mode:
                print("Apenas o host pode iniciar o jogo")
                return
                
            # Verificar se há jogadores suficientes
            if len(self.game.state_manager.players) < 1:
                print("É necessário pelo menos um jogador para iniciar o jogo")
                return
                
            # Iniciar o jogo
            self.game.start_game()
            self.game_state = self.game.get_game_state()
            
            # Transmitir estado para todos os jogadores
            from shared.network.message import Message, MessageType
            start_message = Message(
                msg_type=MessageType.GAME_STATE,
                sender_id=self.player.player_id,
                content=self.game_state
            )
            
            self.p2p_manager.send_message(start_message)
            
            # Mudar para a tela de jogo
            self.view_manager.set_view("GAME")
            
            # Atualizar o game_client
            if hasattr(self, 'game_client'):
                self.game_client.game = self.game
                self.game_client.game_state = self.game_state
                self.game_client.host_mode = True
            
            print("Jogo iniciado com sucesso!")
            
        except Exception as e:
            print(f"Erro ao iniciar o jogo: {e}")
            import traceback
            traceback.print_exc()

    def handle_event(self, event):
        """Processa eventos da interface"""
        
        # Eventos para a tela de criar sala
        if self.current_view == "CREATE_ROOM":
            # Processamento de input de texto
            if event.type == pygame.KEYDOWN:
                if self.room_name_input_active:
                    if event.key == pygame.K_RETURN:
                        self.room_name_input_active = False
                    elif event.key == pygame.K_BACKSPACE:
                        self.room_name_input = self.room_name_input[:-1]
                    else:
                        # Adicionar caracter ao nome da sala
                        if len(self.room_name_input) < 20:  # Limite de 20 caracteres
                            self.room_name_input += event.unicode
                
                elif self.password_input_active:
                    if event.key == pygame.K_RETURN:
                        self.password_input_active = False
                    elif event.key == pygame.K_BACKSPACE:
                        self.password_input = self.password_input[:-1]
                    else:
                        # Adicionar caracter à senha
                        if len(self.password_input) < 20:  # Limite de 20 caracteres
                            self.password_input += event.unicode
            
            # Cliques do mouse
            if event.type == pygame.MOUSEBUTTONDOWN:
                # Coordenadas do form
                form_width = 500
                form_x = config.SCREEN_WIDTH // 2 - form_width // 2
                form_y = 150
                
                # Verifica clique no campo de nome da sala
                name_box = pygame.Rect(form_x + 30, form_y + 30 + 40, 440, 40)
                if name_box.collidepoint(event.pos):
                    self.room_name_input_active = True
                    self.password_input_active = False
                
                # Verifica clique no campo de senha
                password_box = pygame.Rect(form_x + 30, form_y + 30 + 100 + 40, 440, 40)
                if password_box.collidepoint(event.pos):
                    self.password_input_active = True
                    self.room_name_input_active = False
                
                # Verifica clique fora dos campos para desativar inputs
                if not name_box.collidepoint(event.pos) and not password_box.collidepoint(event.pos):
                    self.room_name_input_active = False
                    self.password_input_active = False
                
                # Botão Voltar
                back_button = pygame.Rect(config.SCREEN_WIDTH // 2 - 310, 500, 200, 50)
                if back_button.collidepoint(event.pos):
                    self.view_manager.set_view("MENU")
                    self.reset_room_data()
                
                # Botão Criar Sala
                create_button = pygame.Rect(config.SCREEN_WIDTH // 2 + 110, 500, 200, 50)
                if create_button.collidepoint(event.pos):
                    self.create_room()

    def handle_lobby_event(self, event):
        """Lidar com eventos na tela de lobby"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            
            # Área de listas de jogadores
            player_list_y = 250
            player_list_height = 300
            
            # Área de botões
            button_y = player_list_y + player_list_height + 30
            button_width = 250
            button_height = 60
            
            # Botão de Iniciar Jogo (apenas para o host)
            if self.host_mode:
                start_button = pygame.Rect(config.SCREEN_WIDTH // 2 - button_width - 20, button_y, 
                                         button_width, button_height)
                if start_button.collidepoint(mouse_pos):
                    self.start_game()
                    return
            
            # Botão de Sair da Sala
            leave_button = pygame.Rect(config.SCREEN_WIDTH // 2 + 20, button_y, 
                                     button_width, button_height)
            if leave_button.collidepoint(mouse_pos):
                self.leave_lobby()
                return