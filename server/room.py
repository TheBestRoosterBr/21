import uuid

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
        self.room_id = ""
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

    def render_create_room(self):
        """Renderizar a tela de criação de sala"""
        # Background com gradiente
        self.screen.fill((0, 40, 0))  # Verde-escuro base

        # Área do título
        title_bg = pygame.Rect(0, 0, config.SCREEN_WIDTH, 120)
        pygame.draw.rect(self.screen, (0, 30, 0), title_bg)

        # Título
        title = self.title_font.render("Criar Sala", True, (240, 240, 240))
        title_rect = title.get_rect(center=(config.SCREEN_WIDTH // 2, 60))
        self.screen.blit(title, title_rect)

        # Área central com informações da sala
        form_width = 500
        form_height = 420
        form_x = config.SCREEN_WIDTH // 2 - form_width // 2
        form_y = 140

        form_bg = pygame.Rect(form_x, form_y, form_width, form_height)
        pygame.draw.rect(self.screen, (0, 60, 0), form_bg, border_radius=10)
        pygame.draw.rect(self.screen, (0, 100, 0), form_bg, 2, border_radius=10)

        y_offset = form_y + 30

        # ID da Sala (gerado automaticamente)
        id_label = self.medium_font.render("ID da Sala:", True, config.WHITE)
        self.screen.blit(id_label, (form_x + 30, y_offset))

        id_value = self.large_font.render(self.room_id, True, (255, 220, 0))
        self.screen.blit(id_value, (form_x + 250, y_offset))

        id_info = self.small_font.render("(Compartilhe este código com seus amigos)", True, (200, 200, 200))
        self.screen.blit(id_info, (form_x + 30, y_offset + 40))

        y_offset += 80

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

        password_info = self.small_font.render("Deixe em branco para sala sem senha", True, (200, 200, 200))
        self.screen.blit(password_info, (form_x + 30, y_offset + 90))

        y_offset += 140

        # Seleção de modo de conexão
        mode_label = self.medium_font.render("Modo de Conexão:", True, config.WHITE)
        self.screen.blit(mode_label, (form_x + 30, y_offset))

        # Opções de modo
        online_rect = pygame.Rect(form_x + 30, y_offset + 40, 200, 40)
        local_rect = pygame.Rect(form_x + 270, y_offset + 40, 200, 40)

        # Destacar a opção selecionada
        if self.view_manager.connection_mode_selection == "online":
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
        button_y = 600

        # Botão Criar
        create_button = pygame.Rect(config.SCREEN_WIDTH // 2 - 220, button_y, button_width, button_height)
        mouse_pos = pygame.mouse.get_pos()
        create_color = (0, 150, 0) if create_button.collidepoint(mouse_pos) else (0, 120, 0)
        pygame.draw.rect(self.screen, create_color, create_button, border_radius=10)
        pygame.draw.rect(self.screen, config.WHITE, create_button, 2, border_radius=10)
        create_text = self.medium_font.render("Criar Sala", True, config.WHITE)
        create_text_rect = create_text.get_rect(center=create_button.center)
        self.screen.blit(create_text, create_text_rect)

        # Botão Cancelar
        cancel_button = pygame.Rect(config.SCREEN_WIDTH // 2 + 20, button_y, button_width, button_height)
        cancel_color = (150, 0, 0) if cancel_button.collidepoint(mouse_pos) else (120, 0, 0)
        pygame.draw.rect(self.screen, cancel_color, cancel_button, border_radius=10)
        pygame.draw.rect(self.screen, config.WHITE, cancel_button, 2, border_radius=10)
        cancel_text = self.medium_font.render("Cancelar", True, config.WHITE)
        cancel_text_rect = cancel_text.get_rect(center=cancel_button.center)
        self.screen.blit(cancel_text, cancel_text_rect)

    def handle_create_room_event(self, event):
        """Manipular eventos na tela de criação de sala"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()

            # Ativar/desativar campos de entrada
            form_x = config.SCREEN_WIDTH // 2 - 250

            # Campo Nome da Sala
            name_box = pygame.Rect(form_x + 30, 140 + 120, 440, 40)
            if name_box.collidepoint(mouse_pos):
                self.room_name_input_active = True
                self.password_input_active = False

            # Campo Senha
            password_box = pygame.Rect(form_x + 30, 140 + 220, 440, 40)
            if password_box.collidepoint(mouse_pos):
                self.password_input_active = True
                self.room_name_input_active = False

            # Botões de modo de conexão
            online_rect = pygame.Rect(form_x + 30, 140 + 320, 200, 40)
            local_rect = pygame.Rect(form_x + 270, 140 + 320, 200, 40)

            if online_rect.collidepoint(mouse_pos):
                self.view_manager.connection_mode_selection = "online"
            elif local_rect.collidepoint(mouse_pos):
                self.view_manager.connection_mode_selection = "local"

            # Botões de ação
            button_width = 200
            button_height = 50
            button_y = 600

            # Botão Criar
            create_button = pygame.Rect(config.SCREEN_WIDTH // 2 - 220, button_y, button_width, button_height)
            if create_button.collidepoint(mouse_pos):
                self.create_room()

            # Botão Cancelar
            cancel_button = pygame.Rect(config.SCREEN_WIDTH // 2 + 20, button_y, button_width, button_height)
            if cancel_button.collidepoint(mouse_pos):
                self.view_manager.set_view("MENU")

        # Entrada de teclado para os campos ativos
        elif event.type == pygame.KEYDOWN:
            if self.room_name_input_active:
                if event.key == pygame.K_BACKSPACE:
                    self.room_name_input = self.room_name_input[:-1]
                elif event.key == pygame.K_RETURN:
                    self.room_name_input_active = False
                elif len(self.room_name_input) < 30:  # Limitar tamanho do nome
                    if event.unicode.isprintable():
                        self.room_name_input += event.unicode
            elif self.password_input_active:
                if event.key == pygame.K_BACKSPACE:
                    self.password_input = self.password_input[:-1]
                elif event.key == pygame.K_RETURN:
                    self.password_input_active = False
                elif len(self.password_input) < 20:  # Limitar tamanho da senha
                    if event.unicode.isprintable():
                        self.password_input += event.unicode

    def create_room(self):
        """Criar uma sala de jogo"""
        if not self.room_name_input:
            self.error_message = "O nome da sala não pode estar vazio"
            self.message_timer = pygame.time.get_ticks()
            return
        # Criar o jogador
        self.player = Player(self.player_name, self.player_balance, str(uuid.uuid4()))

        # Criar o jogo
        self.game = Game()
        self.game.initialize_game(self.player)

        # Definir o ID da sala
        self.game.game_id = self.room_id
        self.game.room_name = self.room_name_input
        self.game.password = self.password_input

        # Configurar servidor baseado no modo de conexão
        if self.view_manager.connection_mode == "online":
            self.setup_online_server()
        else:
            self.setup_local_server()

        # Registrar o jogo no serviço de matchmaking
        # (o método será diferente dependendo do modo selecionado)
        if self.view_manager.connection_mode == "online":
            self.register_online_room()
        else:
            self.register_local_room()

        # Exibir mensagem de sucesso
        self.success_message = "Sala criada com sucesso!"
        self.message_timer = pygame.time.get_ticks()

        # Mover para o lobby
        self.view_manager.set_view("LOBBY")
        self.host_mode = True
        self.game_state = self.game.get_game_state()

    def setup_online_server(self):
        """Configurar servidor para conexão online"""
        # TODO: Implementar servidor online usando sockets
        # Esta configuração deve permitir conexões pela internet
        # usando um servidor intermediário ou conexão direta
        self.p2p_manager = P2PManager(host=True)
        self.p2p_manager.register_message_callback(self.on_message_received)
        self.p2p_manager.register_connection_callback(on_player_connected)
        self.p2p_manager.register_disconnection_callback(self.on_player_disconnected)
        self.p2p_manager.start()

    def setup_local_server(self):
        """Configurar servidor para conexão em rede local"""
        # TODO: Implementar servidor local usando sockets
        # Esta configuração deve descobrir automaticamente
        # jogadores na mesma rede local
        self.p2p_manager = P2PManager(host=True, port=5555)
        self.p2p_manager.register_message_callback(self.on_message_received)
        self.p2p_manager.register_connection_callback(on_player_connected)
        self.p2p_manager.register_disconnection_callback(self.on_player_disconnected)
        self.p2p_manager.start()

    def register_online_room(self):
        """Registrar a sala no serviço de matchmaking online"""
        # TODO: Implementar registro no servidor de matchmaking online
        success, game_id, lobby = self.matchmaking_service.create_game(
            self.player_name,
            room_name=self.room_name_input,
            password=self.password_input
        )

        if success:
            self.game.game_id = game_id
        else:
            self.error_message = f"Erro ao criar sala: {lobby}"
            self.message_timer = pygame.time.get_ticks()

    def register_local_room(self):
        """Registrar a sala para descoberta na rede local"""
        # TODO: Implementar broadcast na rede local para anunciar a sala
        # Usar sockets UDP para broadcast na rede local
        success, game_id, lobby = self.matchmaking_service.create_local_game(
            self.player_name,
            room_name=self.room_name_input,
            password=self.password_input
        )

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
        if self.view_manager.connection_mode_selection == "online":
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
        """Renderizar a tela de navegação de salas disponíveis"""
        # Background com gradiente
        self.screen.fill((0, 40, 0))  # Verde escuro base

        # Área do título
        title_bg = pygame.Rect(0, 0, config.SCREEN_WIDTH, 120)
        pygame.draw.rect(self.screen, (0, 30, 0), title_bg)

        # Título
        mode_text = "Online" if self.view_manager.connection_mode == "online" else "Rede Local"
        title = self.title_font.render(f"Salas Disponíveis ({mode_text})", True, (240, 240, 240))
        title_rect = title.get_rect(center=(config.SCREEN_WIDTH // 2, 60))
        self.screen.blit(title, title_rect)

        # Botão de Atualizar
        refresh_button = pygame.Rect(config.SCREEN_WIDTH - 160, 60, 120, 40)
        mouse_pos = pygame.mouse.get_pos()
        refresh_color = (0, 130, 200) if refresh_button.collidepoint(mouse_pos) else (0, 100, 170)
        pygame.draw.rect(self.screen, refresh_color, refresh_button, border_radius=10)
        pygame.draw.rect(self.screen, config.WHITE, refresh_button, 2, border_radius=10)
        refresh_text = self.small_font.render("Atualizar", True, config.WHITE)
        refresh_text_rect = refresh_text.get_rect(center=refresh_button.center)
        self.screen.blit(refresh_text, refresh_text_rect)

        # Área central com a lista de salas
        list_width = 800
        list_height = 400
        list_x = config.SCREEN_WIDTH // 2 - list_width // 2
        list_y = 150

        list_bg = pygame.Rect(list_x, list_y, list_width, list_height)
        pygame.draw.rect(self.screen, (0, 60, 0), list_bg, border_radius=10)
        pygame.draw.rect(self.screen, (0, 100, 0), list_bg, 2, border_radius=10)

        # Cabeçalhos da lista
        header_y = list_y + 20
        headers = [
            {"text": "ID", "x": list_x + 50, "width": 100},
            {"text": "Nome da Sala", "x": list_x + 150, "width": 300},
            {"text": "Jogadores", "x": list_x + 470, "width": 100},
            {"text": "Protegida", "x": list_x + 590, "width": 120},
            {"text": "", "x": list_x + 720, "width": 80}  # Coluna para o botão Entrar
        ]

        for header in headers:
            text = self.medium_font.render(header["text"], True, (220, 220, 220))
            self.screen.blit(text, (header["x"], header_y))

        # Desenhar linha de separação
        pygame.draw.line(self.screen, (0, 100, 0), (list_x + 20, header_y + 40),
                         (list_x + list_width - 20, header_y + 40), 2)

        # Mensagem se não houver salas
        if not self.room_list:
            no_rooms_text = self.medium_font.render("Nenhuma sala disponível", True, (200, 200, 200))
            no_rooms_rect = no_rooms_text.get_rect(center=(list_x + list_width // 2, list_y + list_height // 2))
            self.screen.blit(no_rooms_text, no_rooms_rect)
        else:
            # Lista de salas
            item_height = 50
            visible_items = 6  # Número de itens visíveis na tela
            start_index = self.room_browser_scroll
            end_index = min(start_index + visible_items, len(self.room_list))

            for i in range(start_index, end_index):
                room = self.room_list[i]
                item_y = header_y + 60 + (i - start_index) * item_height

                # Destacar a sala selecionada
                if i == self.selected_room_index:
                    selection_rect = pygame.Rect(list_x + 10, item_y - 5, list_width - 20, item_height)
                    pygame.draw.rect(self.screen, (0, 80, 0), selection_rect, border_radius=5)

                # ID da sala
                id_text = self.medium_font.render(room["id"], True, config.WHITE)
                self.screen.blit(id_text, (list_x + 50, item_y))

                # Nome da sala
                name_text = self.medium_font.render(room["name"], True, config.WHITE)
                self.screen.blit(name_text, (list_x + 150, item_y))

                # Número de jogadores
                players_text = self.medium_font.render(f"{room['player_count']}/8", True, config.WHITE)
                self.screen.blit(players_text, (list_x + 470, item_y))

                # Indicação se tem senha
                has_password = room.get("has_password", False)
                password_text = self.medium_font.render("Sim" if has_password else "Não", True,
                                                        (255, 150, 150) if has_password else (150, 255, 150))
                self.screen.blit(password_text, (list_x + 590, item_y))

                # Botão Entrar
                join_button = pygame.Rect(list_x + 720, item_y - 5, 60, 30)
                join_color = (0, 150, 0) if join_button.collidepoint(mouse_pos) else (0, 120, 0)
                pygame.draw.rect(self.screen, join_color, join_button, border_radius=5)
                pygame.draw.rect(self.screen, config.WHITE, join_button, 1, border_radius=5)
                join_text = self.small_font.render("Entrar", True, config.WHITE)
                join_text_rect = join_text.get_rect(center=join_button.center)
                self.screen.blit(join_text, join_text_rect)

            # Controles de scroll
            if len(self.room_list) > visible_items:
                # Botão para cima
                up_button = pygame.Rect(list_x + list_width - 40, list_y + 20, 30, 30)
                up_color = (0, 130, 200) if up_button.collidepoint(mouse_pos) else (0, 100, 170)
                pygame.draw.rect(self.screen, up_color, up_button, border_radius=5)
                up_text = self.medium_font.render("▲", True, config.WHITE)
                up_text_rect = up_text.get_rect(center=up_button.center)
                self.screen.blit(up_text, up_text_rect)

                # Botão para baixo
                down_button = pygame.Rect(list_x + list_width - 40, list_y + list_height - 50, 30, 30)
                down_color = (0, 130, 200) if down_button.collidepoint(mouse_pos) else (0, 100, 170)
                pygame.draw.rect(self.screen, down_color, down_button, border_radius=5)
                down_text = self.medium_font.render("▼", True, config.WHITE)
                down_text_rect = down_text.get_rect(center=down_button.center)
                self.screen.blit(down_text, down_text_rect)

        # Botões de alternância de modo
        mode_y = list_y + list_height + 20

        # Botão de modo Online
        online_button = pygame.Rect(config.SCREEN_WIDTH // 2 - 220, mode_y, 200, 40)
        online_color = (0, 120, 210) if self.view_manager.connection_mode == "online" else (0, 80, 0)
        pygame.draw.rect(self.screen, online_color, online_button, border_radius=10)
        pygame.draw.rect(self.screen, config.WHITE, online_button, 2 if self.view_manager.connection_mode == "online" else 1,
                         border_radius=10)
        online_text = self.medium_font.render("Online", True, config.WHITE)
        online_text_rect = online_text.get_rect(center=online_button.center)
        self.screen.blit(online_text, online_text_rect)

        # Botão de modo Rede Local
        local_button = pygame.Rect(config.SCREEN_WIDTH // 2 + 20, mode_y, 200, 40)
        local_color = (0, 120, 210) if self.view_manager.connection_mode == "local" else (0, 80, 0)
        pygame.draw.rect(self.screen, local_color, local_button, border_radius=10)
        pygame.draw.rect(self.screen, config.WHITE, local_button, 2 if self.view_manager.connection_mode == "local" else 1,
                         border_radius=10)
        local_text = self.medium_font.render("Rede Local", True, config.WHITE)
        local_text_rect = local_text.get_rect(center=local_button.center)
        self.screen.blit(local_text, local_text_rect)

        # Botões de ação
        button_width = 200
        button_height = 50
        button_y = 650

        # Botão Criar Sala
        create_button = pygame.Rect(config.SCREEN_WIDTH // 2 - 310, button_y, button_width, button_height)
        create_color = (0, 150, 100) if create_button.collidepoint(mouse_pos) else (0, 120, 80)
        pygame.draw.rect(self.screen, create_color, create_button, border_radius=10)
        pygame.draw.rect(self.screen, config.WHITE, create_button, 2, border_radius=10)
        create_text = self.medium_font.render("Criar Sala", True, config.WHITE)
        create_text_rect = create_text.get_rect(center=create_button.center)
        self.screen.blit(create_text, create_text_rect)

        # Botão Entrar com ID
        join_id_button = pygame.Rect(config.SCREEN_WIDTH // 2 - 100, button_y, button_width, button_height)
        join_id_color = (0, 130, 180) if join_id_button.collidepoint(mouse_pos) else (0, 100, 150)
        pygame.draw.rect(self.screen, join_id_color, join_id_button, border_radius=10)
        pygame.draw.rect(self.screen, config.WHITE, join_id_button, 2, border_radius=10)
        join_id_text = self.medium_font.render("Entrar com ID", True, config.WHITE)
        join_id_text_rect = join_id_text.get_rect(center=join_id_button.center)
        self.screen.blit(join_id_text, join_id_text_rect)

        # Botão Voltar
        back_button = pygame.Rect(config.SCREEN_WIDTH // 2 + 110, button_y, button_width, button_height)
        back_color = (150, 0, 0) if back_button.collidepoint(mouse_pos) else (120, 0, 0)
        pygame.draw.rect(self.screen, back_color, back_button, border_radius=10)
        pygame.draw.rect(self.screen, config.WHITE, back_button, 2, border_radius=10)
        back_text = self.medium_font.render("Voltar", True, config.WHITE)
        back_text_rect = back_text.get_rect(center=back_button.center)
        self.screen.blit(back_text, back_text_rect)

    def handle_room_browser_event(self, event):
        """Manipular eventos na tela de lista de salas"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()

            # Botão de Atualizar
            refresh_button = pygame.Rect(config.SCREEN_WIDTH - 160, 60, 120, 40)
            if refresh_button.collidepoint(mouse_pos):
                self.load_room_list(self.view_manager.connection_mode)
                return

            # Área da lista de salas
            list_width = 800
            list_height = 400
            list_x = config.SCREEN_WIDTH // 2 - list_width // 2
            list_y = 150

            # Verificar clique em salas
            if self.room_list:
                item_height = 50
                visible_items = 6
                start_index = self.room_browser_scroll
                end_index = min(start_index + visible_items, len(self.room_list))

                for i in range(start_index, end_index):
                    item_y = list_y + 80 + (i - start_index) * item_height

                    # Seleção da sala
                    selection_area = pygame.Rect(list_x + 10, item_y - 5, list_width - 100, item_height)
                    if selection_area.collidepoint(mouse_pos):
                        self.selected_room_index = i

                    # Botão Entrar
                    join_button = pygame.Rect(list_x + 720, item_y - 5, 60, 30)
                    if join_button.collidepoint(mouse_pos):
                        self.join_selected_room(i)
                        return

            # Controles de scroll
            if len(self.room_list) > 6:
                # Botão para cima
                up_button = pygame.Rect(list_x + list_width - 40, list_y + 20, 30, 30)
                if up_button.collidepoint(mouse_pos) and self.room_browser_scroll > 0:
                    self.room_browser_scroll -= 1
                    return

                # Botão para baixo
                down_button = pygame.Rect(list_x + list_width - 40, list_y + list_height - 50, 30, 30)
                if down_button.collidepoint(mouse_pos) and self.room_browser_scroll < len(self.room_list) - 6:
                    self.room_browser_scroll += 1
                    return

            # Botões de alternância de modo
            mode_y = list_y + list_height + 20

            # Botão de modo Online
            online_button = pygame.Rect(config.SCREEN_WIDTH // 2 - 220, mode_y, 200, 40)
            if online_button.collidepoint(mouse_pos) and self.view_manager.connection_mode != "online":
                self.view_manager.connection_mode = "online"
                self.load_room_list("online")
                return

            # Botão de modo Rede Local
            local_button = pygame.Rect(config.SCREEN_WIDTH // 2 + 20, mode_y, 200, 40)
            if local_button.collidepoint(mouse_pos) and self.view_manager.connection_mode != "local":
                self.view_manager.connection_mode = "local"
                self.load_room_list("local")
                return

            # Botões de ação
            button_width = 200
            button_height = 50
            button_y = 650

            # Botão Criar Sala
            create_button = pygame.Rect(config.SCREEN_WIDTH // 2 - 310, button_y, button_width, button_height)
            if create_button.collidepoint(mouse_pos):
                self.handle_create_room_click()
                return

            # Botão Entrar com ID
            join_id_button = pygame.Rect(config.SCREEN_WIDTH // 2 - 100, button_y, button_width, button_height)
            if join_id_button.collidepoint(mouse_pos):
                self.view_manager.set_view("JOIN_ROOM")
                return

            # Botão Voltar
            back_button = pygame.Rect(config.SCREEN_WIDTH // 2 + 110, button_y, button_width, button_height)
            if back_button.collidepoint(mouse_pos):
                self.view_manager.set_view("MENU")
                return

    def handle_create_room_click(self):
        """Manipular clique no botão Criar Sala"""
        if not self.player_name:
            self.player_name = "Player"
            self.player_balance = get_player_balance(self.player_name)
        self.view_manager.set_view("CREATE_ROOM")

        self.view_manager.connection_mode = "online"  # Padrão: online

    def load_room_list(self, mode="online"):
        """Carregar a lista de salas disponíveis"""
        self.view_manager.connection_mode = mode
        self.selected_room_index = -1
        self.room_browser_scroll = 0

        if mode == "online":
            # Buscar salas online
            success, rooms = self.matchmaking_service.list_games()
            if success:
                self.room_list = []
                for room in rooms:
                    self.room_list.append({
                        "id": room["game_id"],
                        "name": room.get("room_name", f"Sala de {room['host_name']}"),
                        "player_count": len(room["players"]),
                        "has_password": room.get("has_password", False),
                        "host_address": room["host_address"],
                        "host_name": room["host_name"]
                    })
            else:
                self.error_message = "Não foi possível buscar as salas online"
                self.message_timer = pygame.time.get_ticks()
        else:
            # Buscar salas na rede local usando broadcast UDP
            success, rooms = self.matchmaking_service.list_local_games()
            if success:
                self.room_list = []
                for room in rooms:
                    self.room_list.append({
                        "id": room["game_id"],
                        "name": room.get("room_name", f"Sala de {room['host_name']}"),
                        "player_count": len(room["players"]),
                        "has_password": room.get("has_password", False),
                        "host_address": room["host_address"],
                        "host_name": room["host_name"]
                    })
            else:
                self.error_message = "Não foi possível buscar as salas na rede local"
                self.message_timer = pygame.time.get_ticks()

    def join_selected_room(self, room_index):
        """Entrar na sala selecionada"""
        if not self.room_list or room_index < 0 or room_index >= len(self.room_list):
            return

        room = self.room_list[room_index]

        # Se a sala tem senha, mostrar tela para digitar a senha
        if room.get("has_password", False):
            self.room_id_input = room["id"]
            self.password_input = ""
            self.password_input_active = True
            self.room_id_input_active = False
            self.view_manager.set_view("JOIN_ROOM")
            return

        # Se não tem senha, entrar diretamente
        # Criar o jogador
        self.player = Player(self.player_name, self.player_balance, str(uuid.uuid4()))

        # Conectar à sala
        success = False
        if self.view_manager.connection_mode == "online":
            success = self.connect_to_online_room(room["id"], "")
        else:
            success = self.connect_to_local_room(room["id"], "")

        if success:
            self.view_manager.set_view("LOBBY")
            self.host_mode = False
            self.success_message = "Conectado à sala com sucesso!"
            self.message_timer = pygame.time.get_ticks()
        else:
            self.error_message = "Não foi possível conectar à sala. Tente novamente."
            self.message_timer = pygame.time.get_ticks()

    def connect_to_online_room(self, room_id, password=""):
        """Conectar a uma sala online usando o ID da sala"""
        # Verificar se o ID da sala foi informado
        if not room_id:
            self.error_message = "ID da sala não informado"
            self.message_timer = pygame.time.get_ticks()
            return False

        # Obter informações da sala do serviço de matchmaking
        success, room_info = self.matchmaking_service.get_room_info(room_id)
        if not success:
            self.error_message = "Sala não encontrada"
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
        self.p2p_manager = P2PManager(host=False)
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
            self.player.name,
        )
        self.p2p_manager.send_message(join_message)

        # Juntar-se ao jogo no serviço de matchmaking
        self.matchmaking_service.join_game(room_id, self.player_name)

        # Aguardar resposta do host (será tratada em on_message_received)
        self.room_id = room_id
        return True

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
                self.view_manager.connection_mode_selection = "online"
            elif local_rect.collidepoint(mouse_pos):
                self.view_manager.connection_mode_selection = "local"

            # Botão Buscar Salas
            button_width = 200
            button_height = 50
            button_y = 500
            browse_button = pygame.Rect(config.SCREEN_WIDTH // 2 - 310, button_y, button_width, button_height)
            if browse_button.collidepoint(mouse_pos):
                self.view_manager.set_view("ROOM_BROWSER")
                self.view_manager.connection_mode = self.view_manager.connection_mode_selection
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
        if self.view_manager.connection_mode_selection == "online":
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
        self.view_manager.connection_mode_selection = "online"  # Padrão: online

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