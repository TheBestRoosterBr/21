import pygame
import sys
import os
import json
import uuid
import time
from pygame.locals import *

from client.ui.view_manager import ViewManager, GameView
from server import room

# Adicione o diretório raiz ao path para importar os módulos compartilhados
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models.player import Player
from shared.models.game import Game
from shared.network.message import Message, MessageType, ActionType
from shared.network.p2p_manager import P2PManager
from server.matchmaking import MatchmakingService
from client.card_sprites import CardSprites
from client.player_data import get_player_balance, update_player_balance, check_player_eliminated, get_player_name
import shared.config as config
import client.ui.menu as menu


class BlackjackClient:
    def __init__(self):
        """Inicializar o cliente do jogo"""
        self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        pygame.display.set_caption("Blackjack P2P")
        self.clock = pygame.time.Clock()
        self.running = True

        self.messages = []
        self.player_name = get_player_name()
        self.player_balance = get_player_balance(self.player_name)
        self.view_manager = ViewManager()
        self.menu = menu.Menu(self.screen, self.player_name, self.player_balance, self.view_manager)
        self.room = room.Room(self.screen, self.player_name, self.player_balance, self.view_manager)

        self.player = None
        self.dealer = None
        self.players = []
        self.my_server = None
        self.client_socket = None
        self.server_address = ""
        self.current_bet = 0
        self.bet_amount = 100  # Valor inicial da aposta
        self.selected_bot_count = 1
        self.selected_bot_strategy = "random"
        self.cursor_visible = True
        self.cursor_timer = 0
        self.p2p_manager = None
        self.matchmaking_service = MatchmakingService()
        self.game = None
        self.game_state = None
        self.host_mode = False

        # Fontes
        self.title_font = pygame.font.SysFont("Arial", 48)
        self.large_font = pygame.font.SysFont("Arial", 36)
        self.medium_font = pygame.font.SysFont("Arial", 24)
        self.small_font = pygame.font.SysFont("Arial", 18)

        # Carregar sprites das cartas
        self.card_sprites = CardSprites()


    def start(self):
        """Iniciar o 'loop' principal do jogo"""
        self.running = True
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                self.handle_event(event)

            self.update()
            self.render()
            self.clock.tick(60)

        # Salvar o saldo do jogador antes de sair
        if self.player and hasattr(self.player, 'balance'):
            update_player_balance(self.player_name, self.player.balance)
            print(f"Salvando saldo final: {self.player_name} = {self.player.balance}")
        
        # Fechar conexões se existirem
        if hasattr(self, 'p2p_manager') and self.p2p_manager:
            self.p2p_manager.close()
            
        pygame.quit()
        sys.exit()

    def handle_event(self, event):
        """Lidar com eventos de entrada do usuário"""
        if self.view_manager.current_view == "MENU":
            self.menu.handle_menu_event(event)
        elif self.view_manager.current_view == "LOBBY":
            self.room.handle_lobby_event(event)
        elif self.view_manager.current_view == "GAME":
            self.handle_game_event(event)
        elif self.view_manager.current_view == "BOT_SELECTION":
            self.handle_bot_selection_event(event)
        elif self.view_manager.current_view == "CREATE_ROOM":
            self.room.password_input = ""
            self.room.password_input_active = True
            self.room.room_name_input = f"Sala de {self.player_name}"
            self.room.room_name_input_active = False
            self.room.room_id = self.room.matchmaking_service.generate_room_id()
            self.room.handle_create_room_event(event)
        elif self.view_manager.current_view == "JOIN_ROOM":
            self.room.handle_join_room_event(event)
        elif self.view_manager.current_view == "ROOM_BROWSER":
            self.room.load_room_list(mode=self.view_manager.connection_mode)
            self.room.handle_room_browser_event(event)

    def render(self):
        """Renderizar a interface do jogo"""
        self.screen.fill(config.GREEN)

        if self.view_manager.current_view == "MENU":
            self.menu.render()
        elif self.view_manager.current_view == "LOBBY":
            self.room.render_lobby()
        elif self.view_manager.current_view == "GAME":
            self.render_game()
        elif self.view_manager.current_view == "BOT_SELECTION":
            self.render_bot_selection()
        elif self.view_manager.current_view == "CREATE_ROOM":
            self.room.render_create_room()
        elif self.view_manager.current_view == "JOIN_ROOM":
            self.room.render_join_room()
        elif self.view_manager.current_view == "ROOM_BROWSER":
            self.room.render_room_browser()
        pygame.display.flip()

    def handle_bot_selection_event(self, event):
        """Lidar com eventos na tela de seleção de bots"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            
            # Botões para selecionar o número de bots
            button_width = 300
            button_height = 60
            button_x = config.SCREEN_WIDTH // 2 - button_width // 2
            
            # Botão para 1 bot
            bot1_button = pygame.Rect(button_x, 200, button_width, button_height)
            if bot1_button.collidepoint(mouse_pos):
                self.start_single_player(1)
                return
                
            # Botão para 2 bots
            bot2_button = pygame.Rect(button_x, 280, button_width, button_height)
            if bot2_button.collidepoint(mouse_pos):
                self.start_single_player(2)
                return
                
            # Botão para 3 bots
            bot3_button = pygame.Rect(button_x, 360, button_width, button_height)
            if bot3_button.collidepoint(mouse_pos):
                self.start_single_player(3)
                return
                
            # Botão para voltar
            back_button = pygame.Rect(button_x, 460, button_width, button_height)
            if back_button.collidepoint(mouse_pos):
                self.view_manager.go_back()
                return

    def handle_game_event(self, event):
        """Lidar com eventos durante o jogo"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()

            # Verificar se é nossa vez
            is_our_turn = (
                    self.game_state and
                    self.game_state["state"] == "PLAYER_TURN" and
                    self.game_state["players"][self.game_state["current_player_index"]]["id"] == self.player.player_id
            )

            # Botão de voltar ao menu (apenas no modo single player)
            menu_button = pygame.Rect(10, 10, 120, 40)
            if len(self.game_state["players"]) <= 4 and menu_button.collidepoint(mouse_pos):  # Single player mode
                self.view_manager.go_back()
                self.game = None
                self.game_state = None
                self.host_mode = False
                return

            # Altura reservada para controles/chat na parte inferior
            FOOTER_HEIGHT = 150
            footer_start_y = config.SCREEN_HEIGHT - FOOTER_HEIGHT
            
            # Área de controles
            controls_x = 20
            controls_width = config.SCREEN_WIDTH // 2 - 40
            button_y = footer_start_y + 45

            # Botões de ajuste de aposta (apenas na fase de apostas)
            if self.game_state["state"] == "BETTING":
                # Posição do valor da aposta
                bet_amount_x = controls_x + 120
                bet_amount_text = self.medium_font.render(f"{self.bet_amount}", True, config.WHITE)

                # Botão de diminuir aposta
                btn_width = 36
                btn_height = 36
                btn_y = footer_start_y + 12

                decrease_bet_button = pygame.Rect(bet_amount_x + bet_amount_text.get_width() + 15, btn_y, btn_width, btn_height)
                if decrease_bet_button.collidepoint(mouse_pos):
                    self.decrease_bet()
                    return

                # Botão de aumentar aposta
                increase_bet_button = pygame.Rect(decrease_bet_button.right + 10, btn_y, btn_width, btn_height)
                if increase_bet_button.collidepoint(mouse_pos):
                    self.increase_bet()
                    return

                # Botão principal de aposta
                bet_button = pygame.Rect(controls_x, button_y, controls_width, 50)
                if bet_button.collidepoint(mouse_pos):
                    self.place_bet()
                    return

            elif self.game_state["state"] == "PLAYER_TURN" and is_our_turn:
                # Botões de ação durante o turno
                button_width = (controls_width - 10) // 2
                
                # Botão de Hit
                hit_button = pygame.Rect(controls_x, button_y, button_width, 50)
                if hit_button.collidepoint(mouse_pos):
                    self.hit()
                    return

                # Botão de Stand
                stand_button = pygame.Rect(controls_x + button_width + 10, button_y, button_width, 50)
                if stand_button.collidepoint(mouse_pos):
                    self.stand()
                    return

            elif self.game_state["state"] == "GAME_OVER":
                # Botão de Nova Rodada
                new_round_button = pygame.Rect(controls_x, button_y, controls_width, 50)
                if new_round_button.collidepoint(mouse_pos):
                    self.new_round()
                    return

    def update(self):
        """Atualizar o estado do jogo"""
        # Só atualiza o p2p_manager se ele existir (modo multiplayer)
        if hasattr(self, 'p2p_manager') and self.p2p_manager:
            self.p2p_manager.update()  # Process any pending network messages

        # Atualizar estado do jogo se for o host
        if self.host_mode and self.game:
            # Verificar se todos os jogadores fizeram suas apostas
            if (self.game_state and 
                self.game_state["state"] == "BETTING" and 
                all(player["current_bet"] > 0 for player in self.game_state["players"])):
                # Se ainda não distribuiu as cartas, distribuir
                if self.game_state["state"] == "BETTING":
                    self.game._deal_initial_cards()
                    self.room.broadcast_game_state()

            # Bot play logic
            if self.game_state and self.game_state["state"] == "PLAYER_TURN":
                current_player = self.game_state["players"][self.game_state["current_player_index"]]
                if current_player["name"].startswith("Bot"):
                    self.bot_play()
                    
                # Verificar se o jogo acabou implicitamente (todos pararam ou estouraram)
                active_players = [p for p in self.game_state["players"] 
                                if not p["is_busted"] and (p["id"] != self.game_state["players"][self.game_state["current_player_index"]]["id"])]
                if not active_players:
                    # Se não há mais jogadores ativos além do atual, o jogo termina
                    self.check_winner()

        # Atualizar mensagens do jogo
        if self.game_state and "messages" in self.game_state:
            self.messages = self.game_state["messages"]

    def render_game(self):
        """Renderizar a tela do jogo"""
        if not self.game_state:
            return

        # Background com gradiente
        self.screen.fill((0, 50, 0))  # Verde base escuro
        
        # Área superior (título)
        title_bg = pygame.Rect(0, 0, config.SCREEN_WIDTH, 60)
        pygame.draw.rect(self.screen, (0, 80, 0), title_bg)
        pygame.draw.rect(self.screen, (0, 100, 0), title_bg, 2)  # Borda
        
        # Título
        title = self.title_font.render("Blackjack 21", True, config.WHITE)
        self.screen.blit(title, (config.SCREEN_WIDTH // 2 - title.get_width() // 2, 10))

        # Botão de Voltar ao Menu (apenas no modo single player)
        if len(self.game_state["players"]) <= 4:  # Single player mode
            menu_button = pygame.Rect(10, 10, 120, 40)
            # Efeito hover
            mouse_pos = pygame.mouse.get_pos()
            menu_color = (220, 0, 0) if menu_button.collidepoint(mouse_pos) else (180, 0, 0)
            pygame.draw.rect(self.screen, menu_color, menu_button, border_radius=10)
            pygame.draw.rect(self.screen, config.WHITE, menu_button, 2, border_radius=10)
            back_text = self.medium_font.render("Menu", True, config.WHITE)
            text_rect = back_text.get_rect(center=menu_button.center)
            self.screen.blit(back_text, text_rect)

        # Informações do jogador atual
        current_player = self.game_state["players"][self.game_state["current_player_index"]]
        current_player_text = self.medium_font.render(f"Vez de: {current_player['name']}", True, config.WHITE)
        self.screen.blit(current_player_text, (20, 70))

        # Estado atual do jogo
        state_text = {
            "BETTING": "Fase de Apostas",
            "DEALING": "Distribuindo Cartas",
            "PLAYER_TURN": "Turno dos Jogadores",
            "GAME_OVER": "Fim da Rodada"
        }.get(self.game_state["state"], self.game_state["state"])
        
        state_colors = {
            "BETTING": (0, 100, 200),
            "DEALING": (0, 150, 150),
            "PLAYER_TURN": (0, 150, 0),
            "GAME_OVER": (150, 0, 0)
        }
        
        state_color = state_colors.get(self.game_state["state"], config.WHITE)
        state_display = self.medium_font.render(state_text, True, state_color)
        state_rect = state_display.get_rect(topright=(config.SCREEN_WIDTH - 20, 70))
        self.screen.blit(state_display, state_rect)

        # Layout modificado - Divisão da tela em áreas
        # Nova distribuição de espaço:
        # - Área central mais ampla para as cartas
        # - Chat e controles na parte inferior, mais compactos
        # - Posicionamento melhor para evitar sobreposições
        
        # Altura reservada para controles/chat na parte inferior
        FOOTER_HEIGHT = 150
        
        # Área central do jogo (maior, sem bordas invasivas)
        game_area_height = config.SCREEN_HEIGHT - 100 - FOOTER_HEIGHT
        game_area = pygame.Rect(10, 100, config.SCREEN_WIDTH - 20, game_area_height)
        # Sem desenhar retângulo preenchido, apenas uma borda sutil
        pygame.draw.rect(self.screen, (0, 100, 0), game_area, 2, border_radius=5)

        # Renderizar cartas e informações de cada jogador
        player_count = len(self.game_state["players"])
        
        # Identificar o jogador humano
        human_player_index = next((i for i, p in enumerate(self.game_state["players"]) 
                                 if not p["name"].startswith("Bot")), 0)
        
        # Definir posições dos jogadores - mais espaço para evitar sobreposições
        # Jogador humano agora está mais acima para evitar sobreposição com os controles
        if player_count == 2:
            player_positions = [
                (config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT - FOOTER_HEIGHT - 120),  # Jogador (mais alto)
                (config.SCREEN_WIDTH // 2, 230)                                   # Bot (cima, mais baixo)
            ]
        elif player_count == 3:
            player_positions = [
                (config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT - FOOTER_HEIGHT - 120),  # Jogador (mais alto)
                (config.SCREEN_WIDTH // 4, 230),                                  # Bot 1 (esquerda, mais baixo)
                (3 * config.SCREEN_WIDTH // 4, 230)                               # Bot 2 (direita, mais baixo)
            ]
        elif player_count == 4:
            player_positions = [
                (config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT - FOOTER_HEIGHT - 120),  # Jogador (mais alto)
                (config.SCREEN_WIDTH // 4, 230),                                  # Bot 1 (esquerda, mais baixo)
                (config.SCREEN_WIDTH // 2, 180),                                  # Bot 2 (cima)
                (3 * config.SCREEN_WIDTH // 4, 230)                               # Bot 3 (direita, mais baixo)
            ]
        else:
            player_positions = [
                (config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT - FOOTER_HEIGHT - 120),
                (config.SCREEN_WIDTH // 2, 230)                                   # Bot mais baixo
            ]
        
        # Tamanho das cartas (maior para o jogador humano)
        HUMAN_CARD_WIDTH = 120
        HUMAN_CARD_HEIGHT = 180
        BOT_CARD_WIDTH = 90
        BOT_CARD_HEIGHT = 135
        
        for i, player in enumerate(self.game_state["players"]):
            x, y = player_positions[i]
            is_human = not player["name"].startswith("Bot")
            
            # Evitar desenhar retângulos de fundo grandes - apenas um painel de informações compacto
            info_height = 70
            info_panel = pygame.Rect(x - 150, y - info_height - 20, 300, info_height)
            
            # Desenhar apenas um fundo sutil para as informações do jogador
            bg_color = (0, 70, 0)  # Cor mais sutil para todos os jogadores
            info_alpha = pygame.Surface((info_panel.width, info_panel.height), pygame.SRCALPHA)
            info_alpha.fill((0, 70, 0, 180))  # Semi-transparente
            self.screen.blit(info_alpha, info_panel)
            
            # Para o jogador atual, um destaque visual
            if player["id"] == current_player["id"]:
                pygame.draw.rect(self.screen, (255, 215, 0), info_panel, 2, border_radius=5)  # Borda dourada
            else:
                pygame.draw.rect(self.screen, (0, 100, 0), info_panel, 1, border_radius=5)  # Borda sutil
            
            # Nome do jogador
            name_font = self.large_font if is_human else self.medium_font
            player_info = name_font.render(f"{player['name']}", True, config.WHITE)
            self.screen.blit(player_info, (x - player_info.get_width() // 2, y - info_height - 10))
            
            # Informações do jogador - mais compactas
            info_text = f"Saldo: {player['balance']} | Aposta: {player['current_bet']}"
            if show_value := (is_human or self.game_state["state"] == "GAME_OVER"):
                info_text += f" | Valor: {player['hand_value']}"
                if player['is_busted']:
                    info_text += " (Estouro!)"
            
            info_color = config.RED if player['is_busted'] else config.WHITE
            player_info_text = self.small_font.render(info_text, True, info_color)
            self.screen.blit(player_info_text, (x - player_info_text.get_width() // 2, y - info_height + 25))

            # Renderizar cartas do jogador com melhor espaçamento
            if 'hand' in player:
                card_width = HUMAN_CARD_WIDTH if is_human else BOT_CARD_WIDTH
                card_height = HUMAN_CARD_HEIGHT if is_human else BOT_CARD_HEIGHT
                
                # Maior espaçamento para o jogador humano, cartas mais espalhadas
                spacing = 40 if is_human else 30
                
                # Calcular largura total e posição inicial para centralizar
                total_width = (len(player['hand']) - 1) * spacing + card_width
                start_x = x - total_width // 2
                
                for j, card in enumerate(player['hand']):
                    card_x = start_x + j * spacing
                    card_y = y
                    
                    # Desenhar fundo preto para a carta, exatamente do mesmo tamanho
                    # Sem bordas extras, apenas um fundo do tamanho da carta
                    self.render_card_back(card_x, card_y, scale=card_width/config.CARD_WIDTH)
                    
                    # Mostrar cartas viradas para baixo para bots durante o jogo
                    if not is_human and self.game_state["state"] != "GAME_OVER":
                        self.render_card_back(card_x, card_y, scale=card_width/config.CARD_WIDTH)
                    else:
                        self.render_card(card, card_x, card_y, scale=card_width/config.CARD_WIDTH)

        # Footer redesenhado - mais elegante e compacto
        footer_start_y = config.SCREEN_HEIGHT - FOOTER_HEIGHT
        
        # Fundo do footer com gradiente
        footer_rect = pygame.Rect(0, footer_start_y, config.SCREEN_WIDTH, FOOTER_HEIGHT)
        footer_gradient = pygame.Surface((config.SCREEN_WIDTH, FOOTER_HEIGHT))
        for y in range(FOOTER_HEIGHT):
            alpha = min(200, int(y * 1.5))
            pygame.draw.line(footer_gradient, (0, 40, 0, alpha), (0, y), (config.SCREEN_WIDTH, y))
        self.screen.blit(footer_gradient, footer_rect)
        
        # Linha divisória sutil
        pygame.draw.line(self.screen, (0, 100, 0), (0, footer_start_y), (config.SCREEN_WIDTH, footer_start_y), 2)

        # Área de mensagens redesenhada - mais à direita
        messages_width = config.SCREEN_WIDTH // 2 - 40
        messages_area = pygame.Rect(config.SCREEN_WIDTH // 2 + 20, footer_start_y + 10, messages_width, FOOTER_HEIGHT - 20)
        
        # Título da área de mensagens
        msg_title = self.medium_font.render("Mensagens do Jogo", True, config.WHITE)
        msg_title_rect = msg_title.get_rect(midtop=(messages_area.centerx, footer_start_y + 5))
        self.screen.blit(msg_title, msg_title_rect)

        # Fundo das mensagens semi-transparente
        msg_bg = pygame.Surface((messages_area.width, messages_area.height), pygame.SRCALPHA)
        msg_bg.fill((0, 0, 0, 80))  # Semi-transparente
        self.screen.blit(msg_bg, messages_area)
        pygame.draw.rect(self.screen, (0, 100, 0), messages_area, 1)  # Borda sutil

        # Mensagens do jogo com melhor formatação
        message_y = footer_start_y + 35
        messages = self.game_state["messages"][-5:]  # Limitar a 5 mensagens
        for msg in messages:
            message_text = self.small_font.render(msg, True, config.WHITE)
            # Limitar o comprimento da mensagem
            if message_text.get_width() > messages_area.width - 20:
                while message_text.get_width() > messages_area.width - 20:
                    msg = msg[:-1]
                    message_text = self.small_font.render(msg + "...", True, config.WHITE)
            message_rect = message_text.get_rect(x=messages_area.x + 10, y=message_y)
            self.screen.blit(message_text, message_rect)
            message_y += 20  # Menor espaçamento entre mensagens

        # Área de botões - completamente redesenhada
        controls_x = 20
        controls_width = config.SCREEN_WIDTH // 2 - 40
        button_y = footer_start_y + 45  # Centralizado no footer
        is_our_turn = (current_player["id"] == self.player.player_id)

        def draw_button(rect, color, hover_color, text, enabled=True):
            """Desenha um botão elegante com efeitos de hover e sombra"""
            mouse_pos = pygame.mouse.get_pos()
            is_hover = rect.collidepoint(mouse_pos) and enabled
            
            alpha = 255 if enabled else 150
            
            # Sombra sutil
            shadow_rect = rect.copy()
            shadow_rect.y += 2
            shadow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            shadow.fill((0, 0, 0, 100))
            self.screen.blit(shadow, shadow_rect)
            
            # Botão com cor baseada no estado (hover/normal/desabilitado)
            button_color = hover_color if is_hover else color
            if not enabled:
                # Dessaturar cores para botões desabilitados
                r, g, b = button_color
                avg = (r + g + b) // 3
                button_color = (avg, avg, avg)
            
            pygame.draw.rect(self.screen, button_color, rect, border_radius=10)
            
            # Borda mais evidente para botões interativos
            border_color = (255, 255, 255, 150) if is_hover else (255, 255, 255, 100)
            border = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(border, border_color, border.get_rect(), 2, border_radius=10)
            self.screen.blit(border, rect)
            
            # Texto com sombra sutil para maior legibilidade
            text_color = (255, 255, 255, alpha)
            text_surface = self.medium_font.render(text, True, text_color)
            text_rect = text_surface.get_rect(center=rect.center)
            
            # Sombra leve no texto
            shadow_surf = self.medium_font.render(text, True, (0, 0, 0, 100))
            shadow_rect = shadow_surf.get_rect(center=(text_rect.centerx + 1, text_rect.centery + 1))
            self.screen.blit(shadow_surf, shadow_rect)
            
            # Texto principal
            self.screen.blit(text_surface, text_rect)
            
            return is_hover

        # Botões específicos baseados no estado do jogo
        if self.game_state["state"] == "BETTING":
            # Área de apostas redesenhada - mais bonita e clara
            bet_panel = pygame.Rect(controls_x, footer_start_y + 10, controls_width, 30)
            pygame.draw.rect(self.screen, (0, 60, 0), bet_panel, border_radius=5)
            pygame.draw.rect(self.screen, (0, 100, 0), bet_panel, 1, border_radius=5)
            
            # Título da aposta
            bet_title = self.medium_font.render("Sua Aposta:", True, config.WHITE)
            self.screen.blit(bet_title, (controls_x + 10, footer_start_y + 14))
            
            # Valor da aposta em destaque
            bet_amount_text = self.medium_font.render(f"{self.bet_amount}", True, config.WHITE)
            bet_amount_x = controls_x + 120
            self.screen.blit(bet_amount_text, (bet_amount_x, footer_start_y + 14))
            
            # Botões de ajuste de aposta mais visíveis
            btn_width = 36
            btn_height = 36
            btn_y = footer_start_y + 12
            
            # Botão de diminuir aposta
            decrease_bet_button = pygame.Rect(bet_amount_x + bet_amount_text.get_width() + 15, btn_y, btn_width, btn_height)
            mouse_pos = pygame.mouse.get_pos()
            decrease_color = (220, 0, 0) if decrease_bet_button.collidepoint(mouse_pos) else (180, 0, 0)
            pygame.draw.rect(self.screen, decrease_color, decrease_bet_button, border_radius=18)
            pygame.draw.rect(self.screen, config.WHITE, decrease_bet_button, 2, border_radius=18)
            
            # Texto centralizado no botão
            decrease_text = self.large_font.render("-", True, config.WHITE)
            decrease_rect = decrease_text.get_rect(center=decrease_bet_button.center)
            self.screen.blit(decrease_text, decrease_rect)
            
            # Botão de aumentar aposta
            increase_bet_button = pygame.Rect(decrease_bet_button.right + 10, btn_y, btn_width, btn_height)
            increase_color = (0, 220, 0) if increase_bet_button.collidepoint(mouse_pos) else (0, 180, 0)
            pygame.draw.rect(self.screen, increase_color, increase_bet_button, border_radius=18)
            pygame.draw.rect(self.screen, config.WHITE, increase_bet_button, 2, border_radius=18)
            
            # Texto centralizado no botão
            increase_text = self.large_font.render("+", True, config.WHITE)
            increase_rect = increase_text.get_rect(center=increase_bet_button.center)
            self.screen.blit(increase_text, increase_rect)

            # Botão principal de aposta
            bet_button = pygame.Rect(controls_x, button_y, controls_width, 50)
            bet_color = (0, 140, 220) if bet_button.collidepoint(mouse_pos) else (0, 100, 180)
            pygame.draw.rect(self.screen, bet_color, bet_button, border_radius=10)
            pygame.draw.rect(self.screen, config.WHITE, bet_button, 2, border_radius=10)
            
            # Texto do botão de aposta
            bet_text = self.medium_font.render("Confirmar Aposta", True, config.WHITE)
            bet_text_rect = bet_text.get_rect(center=bet_button.center)
            self.screen.blit(bet_text, bet_text_rect)

        elif self.game_state["state"] == "PLAYER_TURN":
            # Botões de ação durante o turno
            button_width = (controls_width - 10) // 2
            
            # Botão de Hit
            hit_button = pygame.Rect(controls_x, button_y, button_width, 50)
            draw_button(hit_button, (0, 100, 180), (0, 140, 220), "Pedir Carta", is_our_turn)

            # Botão de Stand
            stand_button = pygame.Rect(controls_x + button_width + 10, button_y, button_width, 50)
            draw_button(stand_button, (180, 0, 0), (220, 0, 0), "Parar", is_our_turn)
            
            # Se não for a vez do jogador, mostrar de quem é a vez
            if not is_our_turn:
                waiting_text = f"Aguardando {current_player['name']}..."
                waiting_surface = self.medium_font.render(waiting_text, True, config.WHITE)
                waiting_rect = waiting_surface.get_rect(midtop=(controls_x + controls_width // 2, button_y - 40))
                self.screen.blit(waiting_surface, waiting_rect)

        elif self.game_state["state"] == "GAME_OVER":
            # Botão de Nova Rodada
            new_round_button = pygame.Rect(controls_x, button_y, controls_width, 50)
            draw_button(new_round_button, (0, 150, 0), (0, 180, 0), "Nova Rodada")

    def render_card(self, card, x, y, scale=1.0):
        """Renderizar uma carta de baralho com escala personalizada"""
        # Calcular escala baseada no tamanho desejado da carta
        final_scale = self.card_sprites.CARD_WIDTH / config.CARD_WIDTH * scale
        
        # Obter a sprite da carta com a escala apropriada
        card_sprite = self.card_sprites.get_card(card["suit"], card["value"], final_scale)
        
        # Desenhar a carta na posição especificada
        self.screen.blit(card_sprite, (x, y))

    def render_card_back(self, x, y, scale=1.0):
        """Renderizar o verso de uma carta com escala personalizada"""
        final_scale = self.card_sprites.CARD_WIDTH / config.CARD_WIDTH * scale
        card_back = self.card_sprites.get_card_back(final_scale)
        self.screen.blit(card_back, (x, y))



    def hit(self):
        """Pedir mais uma carta"""
        if not self.host_mode:
            # Cliente envia solicitação para o host
            hit_message = Message.create_action_message(
                self.player.player_id,
                ActionType.HIT
            )
            self.p2p_manager.send_message(hit_message)
        else:
            # Host processa diretamente
            success, message = self.game.hit(self.player.player_id)
            if success:
                self.game.messages.append(message)
                self.game_state = self.game.get_game_state()  # Atualizar o game state
            self.room.broadcast_game_state()

    def stand(self):
        """Parar de pedir cartas"""
        if not self.host_mode:
            # Cliente envia solicitação para o host
            stand_message = Message.create_action_message(
                self.player.player_id,
                ActionType.STAND
            )
            self.p2p_manager.send_message(stand_message)
        else:
            # Host processa diretamente
            success, message = self.game.stand(self.player.player_id)
            if success:
                self.game.messages.append(message)
                self.game_state = self.game.get_game_state()  # Atualizar o game state
            self.room.broadcast_game_state()

    def place_bet(self):
        """Colocar uma aposta"""
        # Verificar se o jogador tem saldo suficiente
        if self.player.balance < self.bet_amount:
            self.game.messages.append(f"Saldo insuficiente! Você tem apenas {self.player.balance} moedas.")
            # Ajustar a aposta para o valor máximo disponível
            self.bet_amount = self.player.balance
            self.game.place_bet(self.player.player_id, self.bet_amount)
            self.game.messages.append(f"{self.player_name} apostou {self.bet_amount}")
            self.game_state = self.game.get_game_state()  # Atualizar o game state
            self.room.broadcast_game_state()
            return
            
        if not self.host_mode:
            # Cliente envia solicitação para o host
            bet_message = Message.create_action_message(
                self.player.player_id,
                ActionType.PLACE_BET,
                {"amount": self.bet_amount}
            )
            self.p2p_manager.send_message(bet_message)
        else:
            # Host processa diretamente
            success, message = self.game.place_bet(self.player.player_id, self.bet_amount)
            if success:
                self.game.messages.append(f"{self.player.name} apostou {self.bet_amount}")
                # Verificar se todos os jogadores fizeram suas apostas
                if all(player.current_bet > 0 for player in self.game.state_manager.players):
                    self.game._deal_initial_cards()
            self.game_state = self.game.get_game_state()  # Atualizar o game state
            self.room.broadcast_game_state()


    def new_round(self):
        """Iniciar uma nova rodada"""
        if not self.game:
            return
            
        # Verificar se o jogador foi eliminado (saldo <= 0)
        human_player = next((p for p in self.game.state_manager.players if p.player_id == self.player.player_id), None)
        if human_player:
            eliminated, new_balance = check_player_eliminated(human_player.name, human_player.balance)
            if eliminated:
                self.game.messages.append(f"{human_player.name} foi eliminado! Saldo resetado para 100.")
                human_player.balance = new_balance
                self.player_balance = new_balance
                update_player_balance(human_player.name, new_balance)

        # Resetar o jogo para uma nova rodada
        success, message = self.game.start_new_round()
        if success:
            self.game.messages.append("Nova rodada iniciada!")
            
            # Fazer apostas iniciais automaticamente
            for player in self.game.state_manager.players:
                # Verificar se o jogador tem saldo suficiente
                if player.balance >= 100:
                    self.game.place_bet(player.player_id, 100)
                else:
                    # Se for o jogador humano com saldo insuficiente
                    if player.player_id == self.player.player_id:
                        # Voltar para o menu
                        self.game.messages.append(f"{player.name} não tem saldo suficiente para apostar!")
                        self.view_manager.set_view("MENU")
                        return
            
            # Atualizar o game state após as apostas
            self.game_state = self.game.get_game_state()
            
            # Distribuir cartas iniciais
            self.game._deal_initial_cards()
            
            # Atualizar o game state novamente após distribuir as cartas
            self.game_state = self.game.get_game_state()
            
            # Broadcast do estado do jogo
            self.room.broadcast_game_state()
        else:
            print(f"Erro ao iniciar nova rodada: {message}")


    def increase_bet(self):
        """Aumentar o valor da aposta"""
        if self.player and self.player.balance > self.bet_amount:
            self.bet_amount = min(self.bet_amount + 10, self.player.balance)
            self.room.broadcast_game_state()

    def decrease_bet(self):
        """Diminuir o valor da aposta"""
        if self.bet_amount > 10:  # Valor mínimo de aposta
            self.bet_amount = max(self.bet_amount - 10, 10)
            self.room.broadcast_game_state()

    def create_bot(self, name, strategy="default"):
        """Criar um bot com a estratégia especificada
        Estratégias:
        - default: Para em 17+, pede em 16-
        - aggressive: Para em 18+, pede em 17-
        - conservative: Para em 15+, pede em 14-
        """
        bot_player = Player(name, 1000, str(uuid.uuid4()))
        bot_player.strategy = strategy
        return bot_player

    def start_single_player(self, num_bots=1):
        """Iniciar jogo single player contra o número selecionado de bots"""
        print(f"Iniciando jogo single player com {self.player_name}, saldo: {self.player_balance}")
        
        # Criar jogador
        self.player = Player(self.player_name, self.player_balance, str(uuid.uuid4()))
        
        # Criar novo jogo
        self.game = Game()
        
        # Adicionar jogador humano primeiro (para garantir que começa)
        self.game.initialize_game(self.player)
        
        # Criar e adicionar bots com estratégias diferentes
        bot_names = ["Bot Conservador", "Bot Normal", "Bot Agressivo"]
        bot_strategies = ["conservative", "default", "aggressive"]
        
        # Adicionar apenas o número de bots selecionado
        for i in range(min(num_bots, 3)):
            bot_player = self.create_bot(bot_names[i], bot_strategies[i])
            self.game.add_player(bot_player)
        
        # Configurar como host e iniciar o jogo
        self.host_mode = True
        self.view_manager.set_view("GAME")
        
        # Iniciar o jogo
        self.game.start_game()
        self.game_state = self.game.get_game_state()
        self.game.messages.append(f"Jogo iniciado contra {num_bots} bot(s)!")
        
        # Garantir que as apostas iniciais sejam feitas
        initial_bet = min(100, self.player.balance)  # Não apostar mais do que o jogador tem
        self.game.place_bet(self.player.player_id, initial_bet)  # Aposta inicial do jogador
        
        # Apostas iniciais dos bots
        for player in self.game.state_manager.players:
            if player.player_id != self.player.player_id:
                self.game.place_bet(player.player_id, 100)
        
        # Distribuir cartas iniciais
        self.game._deal_initial_cards()
        self.room.broadcast_game_state()

    def bot_play(self):
        """Lógica de jogo dos bots"""
        if not self.game_state:
            return

        current_player = self.game_state["players"][self.game_state["current_player_index"]]
        # Verifique se o jogador atual é um bot (nome começa com "Bot")
        if not current_player["name"].startswith("Bot"):
            return

        # Lógica de apostas do bot
        if self.game_state["state"] == "BETTING":
            # Bot sempre aposta 100
            success, message = self.game.place_bet(current_player["id"], 100)
            if success:
                self.game.messages.append(f"{current_player['name']} apostou 100")
                self.game_state = self.game.get_game_state()  # Atualizar o game state
            self.room.broadcast_game_state()
            return

        # Lógica de jogo do bot
        if self.game_state["state"] == "PLAYER_TURN":
            # Verificar se o jogador humano estourou
            human_player = next((p for p in self.game_state["players"] if not p["name"].startswith("Bot")), None)
            if human_player and human_player["is_busted"]:
                # Se o jogador humano estourou, o bot para
                success, message = self.game.stand(current_player["id"])
                if success:
                    self.game.messages.append(f"{current_player['name']} parou")
                    self.game_state = self.game.get_game_state()  # Atualizar o game state
                self.room.broadcast_game_state()
                return

            # Esperar um pouco para simular "pensamento"
            time.sleep(0.5)  # Reduzido para manter o jogo fluido com múltiplos bots

            # Encontrar a estratégia do bot atual
            hand_value = current_player["hand_value"]
            bot_player = next((p for p in self.game.state_manager.players if p.player_id == current_player["id"]), None)
            
            if bot_player:
                strategy = getattr(bot_player, "strategy", "default")
                
                # Aplicar estratégia
                limit = 17  # Padrão
                if strategy == "aggressive":
                    limit = 18
                elif strategy == "conservative":
                    limit = 15
                
                if hand_value < limit:
                    success, message = self.game.hit(current_player["id"])
                    if success:
                        self.game.messages.append(f"{current_player['name']} pediu carta")
                        self.game_state = self.game.get_game_state()  # Atualizar o game state
                else:
                    success, message = self.game.stand(current_player["id"])
                    if success:
                        self.game.messages.append(f"{current_player['name']} parou")
                        self.game_state = self.game.get_game_state()  # Atualizar o game state

            self.room.broadcast_game_state()

    def check_winner(self):
        """Verificar o vencedor da rodada"""
        if not self.game_state:
            return

        players = self.game_state["players"]
        
        # Separar jogadores humanos e bots
        human_player = next((p for p in players if not p["name"].startswith("Bot")), None)
        if not human_player:
            return
            
        active_players = [p for p in players if not p["is_busted"]]
        
        # Se todos estouraram, não há vencedor
        if not active_players:
            self.game.messages.append("Todos estouraram! Ninguém ganha.")
            self.game_state["state"] = "GAME_OVER"
            return
            
        # Se apenas um jogador não estourou, ele é o vencedor
        if len(active_players) == 1:
            winner = active_players[0]
            self.game.messages.append(f"{winner['name']} venceu! (Único jogador não estourado)")
            
            # Processar resultado (apenas para jogadores humanos)
            if winner["name"] == self.player.name:
                old_balance = self.player.balance
                # Calcular o prêmio (soma de todas as apostas)
                total_pot = sum(p["current_bet"] for p in players)
                # Atualizar o saldo (já incluído no objeto player)
                new_balance = self.player.balance
                print(f"Jogador {self.player.name} venceu! Saldo atualizado: {old_balance} -> {new_balance} (ganhou {total_pot})")
                # Salvar no arquivo
                update_player_balance(self.player.name, new_balance)
                self.player_balance = new_balance
                
            self.game_state["state"] = "GAME_OVER"
            return
            
        # Se múltiplos jogadores não estouraram, encontre o maior valor
        max_value = max(p["hand_value"] for p in active_players)
        winners = [p for p in active_players if p["hand_value"] == max_value]
        
        # Anunciar vencedores
        if len(winners) == 1:
            self.game.messages.append(f"{winners[0]['name']} venceu com {max_value} pontos!")
            
            # Processar resultado (apenas para jogadores humanos)
            if winners[0]["name"] == self.player.name:
                old_balance = self.player.balance
                # Atualizar o saldo (já incluído no objeto player)
                new_balance = self.player.balance
                print(f"Jogador {self.player.name} venceu! Saldo atualizado: {old_balance} -> {new_balance}")
                # Salvar no arquivo
                update_player_balance(self.player.name, new_balance)
                self.player_balance = new_balance
        else:
            winner_names = ", ".join(w["name"] for w in winners)
            self.game.messages.append(f"Empate entre {winner_names} com {max_value} pontos!")
            
            # Verificar se o jogador humano está entre os vencedores
            if any(w["name"] == self.player.name for w in winners):
                old_balance = self.player.balance
                # Atualizar o saldo (já incluído no objeto player)
                new_balance = self.player.balance
                print(f"Jogador {self.player.name} empatou! Saldo atualizado: {old_balance} -> {new_balance}")
                # Salvar no arquivo
                update_player_balance(self.player.name, new_balance)
                self.player_balance = new_balance
            
        self.game_state["state"] = "GAME_OVER"
        self.room.broadcast_game_state()

    def render_bot_selection(self):
        """Renderizar a tela de seleção de bots"""
        # Background
        self.screen.fill((0, 40, 0))  # Verde escuro base
        
        # Título
        title_bg = pygame.Rect(0, 0, config.SCREEN_WIDTH, 120)
        pygame.draw.rect(self.screen, (0, 30, 0), title_bg)
        
        title = self.title_font.render("Selecione o Número de Bots", True, (240, 240, 240))
        title_rect = title.get_rect(center=(config.SCREEN_WIDTH // 2, 60))
        self.screen.blit(title, title_rect)
        
        def draw_selection_button(rect, text, color, hover_color):
            """Desenhar botão de seleção com efeito hover"""
            mouse_pos = pygame.mouse.get_pos()
            is_hover = rect.collidepoint(mouse_pos)
            
            # Sombra
            shadow_rect = rect.copy()
            shadow_rect.y += 2
            pygame.draw.rect(self.screen, (0, 0, 0, 128), shadow_rect, border_radius=15)
            
            # Botão
            current_color = hover_color if is_hover else color
            pygame.draw.rect(self.screen, current_color, rect, border_radius=15)
            
            # Borda
            if is_hover:
                pygame.draw.rect(self.screen, (255, 255, 255, 128), rect, 2, border_radius=15)
            
            # Texto
            text_surface = self.medium_font.render(text, True, (240, 240, 240))
            text_rect = text_surface.get_rect(center=rect.center)
            self.screen.blit(text_surface, text_rect)
        
        # Botões para selecionar o número de bots
        button_width = 300
        button_height = 60
        button_x = config.SCREEN_WIDTH // 2 - button_width // 2
        
        # Cores dos botões
        button_colors = [
            ((0, 100, 180), (0, 140, 230)),  # 1 Bot
            ((0, 130, 150), (0, 170, 190)),  # 2 Bots
            ((0, 150, 120), (0, 190, 160)),  # 3 Bots
            ((150, 30, 30), (190, 50, 50))   # Voltar
        ]
        
        # Botão para 1 bot
        bot1_button = pygame.Rect(button_x, 200, button_width, button_height)
        draw_selection_button(bot1_button, "Jogar com 1 Bot", button_colors[0][0], button_colors[0][1])
        
        # Botão para 2 bots
        bot2_button = pygame.Rect(button_x, 280, button_width, button_height)
        draw_selection_button(bot2_button, "Jogar com 2 Bots", button_colors[1][0], button_colors[1][1])
        
        # Botão para 3 bots
        bot3_button = pygame.Rect(button_x, 360, button_width, button_height)
        draw_selection_button(bot3_button, "Jogar com 3 Bots", button_colors[2][0], button_colors[2][1])
        
        # Botão para voltar
        back_button = pygame.Rect(button_x, 460, button_width, button_height)
        draw_selection_button(back_button, "Voltar", button_colors[3][0], button_colors[3][1])
        
        # Descrição dos tipos de bots
        info_y = 550
        info_texts = [
            "Bot Conservador: Para com 15+ pontos",
            "Bot Normal: Para com 17+ pontos",
            "Bot Agressivo: Para com 18+ pontos"
        ]
        
        info_rect = pygame.Rect(config.SCREEN_WIDTH // 2 - 300, info_y - 20, 600, 150)
        pygame.draw.rect(self.screen, (0, 50, 0), info_rect, border_radius=10)
        pygame.draw.rect(self.screen, (0, 80, 0), info_rect, 2, border_radius=10)
        
        for i, text in enumerate(info_texts):
            info_text = self.small_font.render(text, True, (220, 220, 220))
            text_rect = info_text.get_rect(centerx=config.SCREEN_WIDTH // 2, y=info_y + i * 30)
            self.screen.blit(info_text, text_rect)

    def render_message(self, message, color):
        """Renderizar uma mensagem temporária na tela"""
        message_surface = self.medium_font.render(message, True, color)
        message_rect = message_surface.get_rect(center=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT - 50))
        
        # Fundo semi-transparente
        padding = 10
        bg_rect = pygame.Rect(message_rect.x - padding, message_rect.y - padding, 
                            message_rect.width + padding * 2, message_rect.height + padding * 2)
        bg_surface = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        bg_surface.fill((0, 0, 0, 150))
        self.screen.blit(bg_surface, bg_rect)
        
        # Desenhar borda
        pygame.draw.rect(self.screen, color, bg_rect, 2, border_radius=5)
        
        # Desenhar mensagem
        self.screen.blit(message_surface, message_rect)



