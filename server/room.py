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
        self.screen = screen
        self.title_font = pygame.font.SysFont("Arial", 48)
        self.large_font = pygame.font.SysFont("Arial", 36)
        self.medium_font = pygame.font.SysFont("Arial", 24)
        self.small_font = pygame.font.SysFont("Arial", 18)
        self.player_name = player_name
        self.player_balance = player_balance
        self.view_manager = view_manager
        self.room_list = []
        self.room_id = ""  # Inicialmente vazio, será definido apenas quando a sala for criada
        self.room_id_input = ""
        self.room_id_input_active = False
        self.room_name_input = ""
        self.room_name_input_active = False
        self.password_input = ""
        self.password_input_active = False
        self.room_browser_scroll = 0
        self.selected_room_index = -1
        self.error_message = ""
        self.success_message = ""
        self.message_timer = 0
        self.player = None
        self.game = None
        self.host_mode = False
        self.game_state = None
        self.p2p_manager = P2PManager()
        self.matchmaking_service = MatchmakingService()
        self.room_list_status = ""

    def render_create_room(self):
        """Renderiza a tela de criar sala"""
        # Background com gradiente
        self.screen.fill((0, 40, 0))  # Verde escuro base

        # Área do título
        title_bg = pygame.Rect(0, 0, config.SCREEN_WIDTH, 120)
        pygame.draw.rect(self.screen, (0, 30, 0), title_bg)

        # Título
        title = self.title_font.render("Criar Sala", True, (240, 240, 240))
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

        # Nome da Sala
        name_label = self.medium_font.render("Nome da Sala:", True, config.WHITE)
        self.screen.blit(name_label, (form_x + 30, y_offset))

        # Campo de entrada para o nome da sala
        name_box = pygame.Rect(form_x + 30, y_offset + 40, 440, 40)

        # Cor da borda baseada no estado de foco
        if self.room_name_input_active:
            name_border_color = (100, 200, 255)  # Azul quando ativo
        else:
            name_border_color = (0, 100, 0)  # Verde escuro padrão

        pygame.draw.rect(self.screen, name_border_color, name_box, border_radius=5)
        pygame.draw.rect(self.screen, (240, 240, 240), pygame.Rect(name_box.x + 2, name_box.y + 2,
                                                                   name_box.width - 4, name_box.height - 4),
                         border_radius=5)

        # Texto do nome da sala
        cursor = "|" if self.room_name_input_active and pygame.time.get_ticks() % 1000 < 500 else ""
        name_text = self.medium_font.render(self.room_name_input + cursor, True, (0, 0, 0))
        self.screen.blit(name_text, (name_box.x + 10, name_box.y + 5))

        y_offset += 100

        # Senha
        password_label = self.medium_font.render("Senha (opcional):", True, config.WHITE)
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

        y_offset += 100

        # ID da Sala
        if not self.room_id:
            # Não gere o ID aqui, apenas mostre um placeholder
            id_text = self.medium_font.render("ID da Sala: Será gerado automaticamente", True, (255, 255, 0))
        else:
            # Mostra o ID já gerado
            id_text = self.medium_font.render(f"ID da Sala: {self.room_id}", True, (255, 255, 0))
        
        self.screen.blit(id_text, (form_x + 30, y_offset))

        # Botões de ação
        button_width = 200
        button_height = 50
        button_y = 500

        # Botão Voltar
        back_button = pygame.Rect(config.SCREEN_WIDTH // 2 - 310, button_y, button_width, button_height)
        mouse_pos = pygame.mouse.get_pos()
        back_color = (100, 100, 100) if back_button.collidepoint(mouse_pos) else (80, 80, 80)
        pygame.draw.rect(self.screen, back_color, back_button, border_radius=10)
        pygame.draw.rect(self.screen, config.WHITE, back_button, 2, border_radius=10)
        back_text = self.medium_font.render("Voltar", True, config.WHITE)
        back_text_rect = back_text.get_rect(center=back_button.center)
        self.screen.blit(back_text, back_text_rect)

        # Botão Criar
        create_button = pygame.Rect(config.SCREEN_WIDTH // 2 + 110, button_y, button_width, button_height)
        create_color = (0, 150, 0) if create_button.collidepoint(mouse_pos) else (0, 120, 0)
        pygame.draw.rect(self.screen, create_color, create_button, border_radius=10)
        pygame.draw.rect(self.screen, config.WHITE, create_button, 2, border_radius=10)
        create_text = self.medium_font.render("Criar Sala", True, config.WHITE)
        create_text_rect = create_text.get_rect(center=create_button.center)
        self.screen.blit(create_text, create_text_rect)

        # Exibir mensagens de erro ou sucesso
        if self.error_message:
            error_surf = self.medium_font.render(self.error_message, True, (255, 100, 100))
            error_rect = error_surf.get_rect(center=(config.SCREEN_WIDTH // 2, 570))
            self.screen.blit(error_surf, error_rect)
        
        if self.success_message:
            success_surf = self.medium_font.render(self.success_message, True, (100, 255, 100))
            success_rect = success_surf.get_rect(center=(config.SCREEN_WIDTH // 2, 570))
            self.screen.blit(success_surf, success_rect)

    def create_room(self):
        """Criar uma nova sala"""
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
        self.p2p_manager = P2PManager(
            player_id=self.player.player_id,
            is_host=True,
            callback=self.on_message_received,
            disconnect_callback=self.on_player_disconnected
        )
        
        # Iniciar o servidor P2P
        self.p2p_manager.start_server(port=5555)
        
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
        return True

    def handle_create_room_event(self, event):
        """Manipular eventos na tela de criar sala"""
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
            mouse_pos = pygame.mouse.get_pos()
            
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

    def reset_room_data(self):
        """Reseta os dados da sala"""
        self.room_name_input = ""
        self.password_input = ""
        self.room_id = ""
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
        title = self.large_font.render("Buscar Salas", True, config.WHITE)
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
        
        # Botões
        button_y = list_y + list_height + 20
        button_width = 180
        button_height = 50
        button_spacing = 20
        
        # Botão de atualizar
        refresh_button = pygame.Rect(list_x, button_y, button_width, button_height)
        pygame.draw.rect(self.screen, (0, 100, 180), refresh_button, border_radius=10)
        pygame.draw.rect(self.screen, config.WHITE, refresh_button, 2, border_radius=10)
        refresh_text = self.medium_font.render("Atualizar", True, config.WHITE)
        refresh_text_rect = refresh_text.get_rect(center=refresh_button.center)
        self.screen.blit(refresh_text, refresh_text_rect)
        
        # Botão de entrar
        join_button = pygame.Rect(list_x + button_width + button_spacing, button_y, button_width, button_height)
        join_color = (0, 150, 0) if self.selected_room_index >= 0 else (100, 100, 100)
        pygame.draw.rect(self.screen, join_color, join_button, border_radius=10)
        pygame.draw.rect(self.screen, config.WHITE, join_button, 2, border_radius=10)
        join_text = self.medium_font.render("Entrar", True, config.WHITE)
        join_text_rect = join_text.get_rect(center=join_button.center)
        self.screen.blit(join_text, join_text_rect)
        
        # Botão de entrar com ID
        join_id_button = pygame.Rect(join_button.right + button_spacing, button_y, button_width, button_height)
        pygame.draw.rect(self.screen, (150, 100, 0), join_id_button, border_radius=10)
        pygame.draw.rect(self.screen, config.WHITE, join_id_button, 2, border_radius=10)
        join_id_text = self.medium_font.render("Entrar com ID", True, config.WHITE)
        join_id_text_rect = join_id_text.get_rect(center=join_id_button.center)
        self.screen.blit(join_id_text, join_id_text_rect)
        
        # Botão de voltar
        back_button = pygame.Rect(join_id_button.right + button_spacing, button_y, button_width, button_height)
        pygame.draw.rect(self.screen, (150, 0, 0), back_button, border_radius=10)
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
                    print(f"Sala selecionada: {self.room_list[self.selected_room_index]['room_name']}")
            
            # Botões
            button_y = list_y + list_height + 20
            button_width = 180
            button_height = 50
            button_spacing = 20
            
            # Botão de atualizar
            refresh_button = pygame.Rect(list_x, button_y, button_width, button_height)
            if refresh_button.collidepoint(mouse_pos):
                self.load_room_list(mode=self.view_manager.connection_mode)
                return
                
            # Botão de entrar
            join_button = pygame.Rect(list_x + button_width + button_spacing, button_y, button_width, button_height)
            if join_button.collidepoint(mouse_pos) and self.selected_room_index >= 0:
                self.join_selected_room(self.selected_room_index)
                return
                
            # Botão de entrar com ID
            join_id_button = pygame.Rect(join_button.right + button_spacing, button_y, button_width, button_height)
            if join_id_button.collidepoint(mouse_pos):
                self.view_manager.set_view("JOIN_ROOM")
                return
                
            # Botão de voltar
            back_button = pygame.Rect(join_id_button.right + button_spacing, button_y, button_width, button_height)
            if back_button.collidepoint(mouse_pos):
                self.view_manager.go_back()
                return

    def load_room_list(self, mode="online"):
        """Carregar lista de salas disponíveis"""
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
            
        # Atualizar a seleção
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
                host_ip, host_port = self.host_address.split(":")
                host_port = int(host_port)
            else:
                print("Formato de endereço de host inválido")
                return False
                
            # Criar jogador
            from shared.models.player import Player
            self.player = Player(self.player_name, self.player_balance, str(uuid.uuid4()))
            
            # Inicializar o gerenciador P2P
            from shared.network.p2p_manager import P2PManager
            self.p2p_manager = P2PManager(
                player_id=self.player.player_id,
                callback=self.on_message_received,
                disconnect_callback=self.on_player_disconnected
            )
            
            # Conectar ao host
            self.p2p_manager.connect_to_host(host_ip, host_port)
            
            # Enviar mensagem de conexão
            from shared.network.message import Message, MessageType
            connection_message = Message.create_connection_message(
                player_id=self.player.player_id,
                player_data={
                    "name": self.player_name,
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
        """Callback para mensagens recebidas"""
        if message.msg_type == MessageType.GAME_STATE:
            # Atualizar o estado do jogo
            self.game_state = message.content

            # Se o jogo começou, mudar para a view do jogo
            if self.game_state["state"] not in ["WAITING_FOR_PLAYERS"]:
                self.view_manager.set_view("GAME")

        elif message.msg_type == MessageType.JOIN_REQUEST and self.host_mode:
            # Processar solicitação de entrada (apenas o host)
            player_id = message.content["player_id"]
            player_name = message.content["player_name"]

            # Criar novo jogador e adicionar ao jogo
            new_player = Player(player_name, 1000, player_id)
            success, player_index = self.game.add_player(new_player)

            # Enviar resposta
            response = Message.create_join_response(
                self.player.player_id,
                success,
                self.game.game_id if success else None,
                "Jogo já iniciado" if not success else None
            )
            self.p2p_manager.send_message(response, player_id)

            # Atualizar lobby no matchmaking service
            player_list = [p.name for p in self.game.state_manager.players]
            self.matchmaking_service.update_lobby(self.game.game_id, player_list)

            # Enviar estado atualizado do jogo para todos
            self.broadcast_game_state()

        elif message.msg_type == MessageType.JOIN_RESPONSE and not self.host_mode:
            # Processar resposta de solicitação de entrada
            if message.content["accepted"]:
                print(f"Entrou no jogo {message.content['game_id']}")
            else:
                print(f"Falha ao entrar no jogo: {message.content['reason']}")
                self.view_manager.set_view("MENU")

        elif message.msg_type == MessageType.PLAYER_ACTION:
            # Processar ação do jogador (apenas o host)
            if self.host_mode:
                self.process_player_action(sender_id, message.content)

    def on_player_disconnected(self, player_id):
        """Callback para quando um jogador se desconecta"""
        print(f"Jogador desconectado: {player_id}")

        # Se somos o host, remover o jogador do jogo
        if self.host_mode and self.game:
            self.game.remove_player(player_id)
            self.broadcast_game_state()
            
    def leave_lobby(self):
        """Sair do lobby e voltar ao menu"""
        if self.p2p_manager:
            self.p2p_manager.close()
            self.p2p_manager = None

        if self.game and self.game.game_id:
            self.matchmaking_service.leave_game(self.game.game_id)

        self.game = None
        self.game_state = None
        self.view_manager.set_view("MENU")
        self.host_mode = False
        
    def broadcast_game_state(self):
        """Enviar o estado atual do jogo para todos os jogadores"""
        if self.host_mode and self.game:
            self.game_state = self.game.get_game_state()
            if hasattr(self, 'p2p_manager') and self.p2p_manager:  # Only send messages in multiplayer mode
                game_state_message = Message.create_game_state_message(
                    self.player.player_id,
                    self.game_state
                )
                self.p2p_manager.send_message(game_state_message)

    def render_lobby(self):
        """Renderizar a tela de lobby"""
        # Título
        title = self.title_font.render("Lobby", True, config.WHITE)
        self.screen.blit(title, (config.SCREEN_WIDTH // 2 - title.get_width() // 2, 50))

        # ID do jogo
        if self.game:
            game_id_text = self.medium_font.render(f"ID do Jogo: {self.game.game_id}", True, config.WHITE)
            self.screen.blit(game_id_text, (100, 150))

            # Status do host
            host_status = self.medium_font.render(
                "Você é o host" if self.host_mode else "Aguardando o host iniciar",
                True, config.BLUE if self.host_mode else config.WHITE
            )
            self.screen.blit(host_status, (100, 200))

        # Lista de jogadores
        players_title = self.large_font.render("Jogadores:", True, config.WHITE)
        self.screen.blit(players_title, (100, 250))

        y_pos = 300
        if self.game_state:
            for player in self.game_state["players"]:
                player_text = self.medium_font.render(
                    f"{player['name']} - Saldo: {player['balance']} " +
                    ("(Host)" if player['is_host'] else ""),
                    True, config.WHITE
                )
                self.screen.blit(player_text, (120, y_pos))
                y_pos += 40

        # Botões
        if self.host_mode:
            start_button = pygame.Rect(100, 600, 200, 50)
            pygame.draw.rect(self.screen, config.BLUE, start_button)
            start_text = self.medium_font.render("Iniciar Jogo", True, config.WHITE)
            self.screen.blit(start_text, (125, 610))

        back_button = pygame.Rect(100, 700, 200, 50)
        pygame.draw.rect(self.screen, config.RED, back_button)
        back_text = self.medium_font.render("Voltar", True, config.WHITE)
        self.screen.blit(back_text, (160, 710))

        # Instruções
        instructions = [
            "Aguardando jogadores...",
            "Mínimo de 2 jogadores para iniciar",
            "O host controla o início do jogo"
        ]

        y_pos = 500
        for instruction in instructions:
            text = self.small_font.render(instruction, True, config.WHITE)
            self.screen.blit(text, (100, y_pos))
            y_pos += 25
    
    def handle_lobby_event(self, event):
        """Lidar com eventos na tela de lobby"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()

            # Botão de iniciar jogo (só para o host)
            if self.host_mode and 100 <= mouse_pos[0] <= 300 and 600 <= mouse_pos[1] <= 650:
                self.start_game()

            # Botão de voltar
            elif 100 <= mouse_pos[0] <= 300 and 700 <= mouse_pos[1] <= 750:
                self.leave_lobby()
    
    def create_game(self):
        """Criar um novo jogo como host"""
        self.player = Player(self.player_name, self.player_balance, str(uuid.uuid4()))
        self.game = Game()
        self.game.initialize_game(self.player)

        # Iniciar o servidor P2P
        self.p2p_manager = P2PManager(host=True)
        self.p2p_manager.register_message_callback(self.on_message_received)
        self.p2p_manager.register_connection_callback(on_player_connected)
        self.p2p_manager.register_disconnection_callback(self.on_player_disconnected)
        self.p2p_manager.start()

        # Criar lobby no serviço de matchmaking
        success, game_id, lobby = self.matchmaking_service.create_game(self.player_name)
        if success:
            self.game.game_id = game_id
            self.view_manager.set_view("LOBBY")
            self.host_mode = True
            self.game_state = self.game.get_game_state()
        else:
            print(f"Erro ao criar lobby: {lobby}")

    def join_game_screen(self):
        """Mostrar tela para entrar em um jogo existente"""
        # Na implementação real, você pode adicionar uma tela para listar lobbies disponíveis
        # Simplificado para este exemplo
        success, lobbies = self.matchmaking_service.list_games()
        if success and lobbies:
            # Apenas entrar no primeiro lobby disponível para este exemplo
            self.join_game(lobbies[0]["game_id"])
        else:
            print("Nenhum jogo disponível")

    def join_game(self, game_id):
        """Entrar em um jogo existente"""
        self.player = Player(self.player_name, self.player_balance, str(uuid.uuid4()))

        # Conectar ao lobby
        success, lobby = self.matchmaking_service.join_game(game_id)
        if not success:
            print(f"Erro ao entrar no lobby: {lobby}")
            return

        # Conectar ao host P2P
        host_address = lobby["host_address"]
        self.p2p_manager = P2PManager(host=False)
        self.p2p_manager.register_message_callback(self.on_message_received)
        self.p2p_manager.start()

        connect_success, message = self.p2p_manager.connect_to_host(host_address)
        if connect_success:
            # Enviar mensagem de solicitação para entrar
            join_message = Message.create_join_request(
                self.player.player_id,
                self.player.name
            )
            self.p2p_manager.send_message(join_message)

            self.view_manager.set_view("LOBBY")
            self.host_mode = False
        else:
            print(f"Erro ao conectar ao host: {message}")

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
        """Iniciar o jogo (apenas host)"""
        if not self.host_mode:
            return

        success, message = self.game.start_game()
        if success:
            self.game.messages.append("O jogo começou!")
            self.view_manager.set_view("GAME")
            self.broadcast_game_state()
        else:
            print(f"Erro ao iniciar o jogo: {message}")

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