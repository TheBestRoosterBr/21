import sys

import pygame
import shared.config as config
from client.player_data import *
from client.ui.view_manager import ViewManager


class Menu:
    def __init__(self, screen, player_name, player_balance, view_manager, server_available=False):
        self.screen = screen
        self.show_tutorial = False
        self.title_font = pygame.font.SysFont("Arial", 48)
        self.large_font = pygame.font.SysFont("Arial", 36)
        self.medium_font = pygame.font.SysFont("Arial", 24)
        self.small_font = pygame.font.SysFont("Arial", 18)
        self.name_input_active = False
        self.player_name = player_name
        self.player_balance = player_balance
        self.view_manager = view_manager
        self.server_available = server_available


    def handle_menu_event(self, event):
        """Lidar com eventos na tela do menu"""
        play_alone_rect = pygame.Rect((config.SCREEN_WIDTH - 250) // 2, 280, 250, 50)
        if event.type == pygame.MOUSEBUTTONDOWN and play_alone_rect.collidepoint(event.pos):
            if not self.name_input_active:
                self.handle_solo_click()
                return
        play_online_rect = pygame.Rect((config.SCREEN_WIDTH - 250) // 2, 280 + 50 + 20, 250, 50)
        if event.type == pygame.MOUSEBUTTONDOWN and play_online_rect.collidepoint(event.pos):
            if not self.name_input_active:
                # Só permitir clique no botão online se o servidor estiver disponível
                if self.server_available:
                    self.handle_online_click()
                else:
                    print("Servidor online não disponível. Inicie o servidor primeiro.")
                return

        play_local_rect = pygame.Rect((config.SCREEN_WIDTH - 250) // 2, 280 + 2 * (50 + 20), 250, 50)
        if event.type == pygame.MOUSEBUTTONDOWN and play_local_rect.collidepoint(event.pos):
            if not self.name_input_active:
                self.handle_local_network_click()
                return

        exit_rect = pygame.Rect((config.SCREEN_WIDTH - 250) // 2, 280 + 3 * (50 + 20), 250, 50)
        if event.type == pygame.MOUSEBUTTONDOWN and exit_rect.collidepoint(event.pos):
            update_player_balance(self.player_name, self.player_balance)
            pygame.quit()
            sys.exit()

        name_input_rect = pygame.Rect(config.SCREEN_WIDTH // 2 - 90, 150, 180, 30)

        if event.type == pygame.MOUSEBUTTONDOWN:
            # Verificar se o clique foi dentro do campo de nome
            if name_input_rect.collidepoint(event.pos):
                # Ativar o campo de nome
                self.name_input_active = True
                if self.player_name == "Player" or self.player_name == "":
                    self.player_name = ""  # Limpar o nome padrão
            else:
                # Se o clique foi fora do campo e o campo estava ativo, desativar e atualizar o saldo
                if self.name_input_active:
                    self.name_input_active = False
                    # Se o nome ficou vazio, voltar para "Player"
                    if self.player_name == "":
                        self.player_name = "Player"
                    # Atualizar o saldo após mudar o nome
                    old_balance = self.player_balance
                    self.player_balance = get_player_balance(self.player_name)
                    print(
                        f"Nome atualizado para: {self.player_name}, saldo atualizado de {old_balance} para {self.player_balance}")
    
        # Manipular teclas para o campo de nome
        if event.type == pygame.KEYDOWN:
            if self.name_input_active:
                if event.key == pygame.K_RETURN:
                    # Confirmar o nome com a tecla Enter
                    self.name_input_active = False
                    if self.player_name == "":
                        self.player_name = "Player"
                    # Atualizar o saldo após confirmar o nome
                    old_balance = self.player_balance
                    self.player_balance = get_player_balance(self.player_name)
                    print(
                        f"Nome confirmado: {self.player_name}, saldo atualizado de {old_balance} para {self.player_balance}")
                elif event.key == pygame.K_BACKSPACE:
                    self.player_name = self.player_name[:-1]
                else:
                    # Limitar o nome a 20 caracteres
                    if len(self.player_name) < 20:
                        self.player_name = self.player_name + event.unicode
    
        # Verificar clique no botão de ajuda
        help_button = pygame.Rect(config.SCREEN_WIDTH - 50, 20, 40, 40)
        if event.type == pygame.MOUSEBUTTONDOWN and help_button.collidepoint(event.pos):
            self.show_tutorial = not self.show_tutorial
            return
    
        # Se o tutorial estiver aberto e o usuário clicar fora dele, fechar o tutorial
        if self.show_tutorial and event.type == pygame.MOUSEBUTTONDOWN:
            tutorial_rect = pygame.Rect(config.SCREEN_WIDTH // 2 - 200, config.SCREEN_HEIGHT // 2 - 150, 400, 300)
            if not tutorial_rect.collidepoint(event.pos):
                self.show_tutorial = False
                return
    
    
    def handle_solo_click(self):
        """Manipular clique no botão Jogar Sozinho"""
        # Certifique-se de que o nome não está no modo de edição
        if self.name_input_active:
            self.name_input_active = False
            if not self.player_name:
                self.player_name = "Player"
            self.player_balance = get_player_balance(self.player_name)
        self.view_manager.set_view("BOT_SELECTION")
    
    
    def handle_online_click(self):
        """Manipular clique no botão Jogar Online"""
        # Certifique-se de que o nome não está no modo de edição
        if self.name_input_active:
            self.name_input_active = False
            if not self.player_name:
                self.player_name = "Player"
            self.player_balance = get_player_balance(self.player_name)
        self.view_manager.conn = "online"
        self.view_manager.set_view("ROOM_BROWSER")

    
    
    def handle_local_network_click(self):
        """Manipular clique no botão Jogar em Rede Local"""
        # Certifique-se de que o nome não está no modo de edição
        if self.name_input_active:
            self.name_input_active = False
            if not self.player_name:
                self.player_name = "Player"
            self.player_balance = get_player_balance(self.player_name)
        self.view_manager.connection_mode = "local"
        self.view_manager.set_view("ROOM_BROWSER")

    def render(self):
        """Render the current view"""
        self.render_menu()
        if self.show_tutorial:
            self.render_tutorial_popup()


    def render_menu(self):
        """Renderizar a tela do menu"""
        # Desenhar o fundo com gradiente
        self.screen.fill((0, 100, 0))  # Verde escuro para o fundo

        # Desenhar área do título
        title_bg = pygame.Rect(0, 0, config.SCREEN_WIDTH, 120)
        pygame.draw.rect(self.screen, (0, 80, 0), title_bg)

        # Desenhar título do jogo
        title = self.title_font.render("Blackjack 21 P2P", True, (240, 240, 240))
        title_shadow = self.title_font.render("Blackjack 21 P2P", True, (0, 40, 0))
        title_rect = title.get_rect(center=(config.SCREEN_WIDTH // 2, 60))
        shadow_rect = title_shadow.get_rect(center=(config.SCREEN_WIDTH // 2 + 2, 62))
        self.screen.blit(title_shadow, shadow_rect)
        self.screen.blit(title, title_rect)

        # Não carregar o saldo toda vez - usar o valor já armazenado em self.player_balance

        # Campo de nome
        name_label = self.medium_font.render("Nome:", True, config.WHITE)
        self.screen.blit(name_label, (config.SCREEN_WIDTH // 2 - 150, 150))

        # Desenhar campo de nome com borda que muda de cor baseado no foco
        name_input_rect = pygame.Rect(config.SCREEN_WIDTH // 2 - 90, 150, 180, 30)
        mouse_pos = pygame.mouse.get_pos()
        hover_name_input = name_input_rect.collidepoint(mouse_pos)

        # Determinar a cor da borda baseado no estado do 'input'
        if self.name_input_active:
            border_color = (0, 120, 255)  # Azul quando ativo
        elif hover_name_input:
            border_color = (100, 180, 255)  # Azul-claro quando o mouse está em cima
        else:
            border_color = (0, 80, 0)  # Verde-escuro quando inativo

        # Desenhar campo de texto com cantos arredondados
        pygame.draw.rect(self.screen, config.WHITE, name_input_rect, border_radius=5)
        pygame.draw.rect(self.screen, border_color, name_input_rect, 2, border_radius=5)

        # Texto dentro do campo
        if self.player_name == "":
            name_text = self.small_font.render("Player", True, config.GRAY)
            self.screen.blit(name_text, (name_input_rect.x + 10, name_input_rect.y + 8))
        else:
            name_text = self.small_font.render(self.player_name, True, config.BLACK)
            text_rect = name_text.get_rect(midleft=(name_input_rect.x + 10, name_input_rect.centery))
            self.screen.blit(name_text, text_rect)

        # Adicionar cursor piscante quando o campo estiver ativo
        if self.name_input_active and pygame.time.get_ticks() % 1000 < 500:
            cursor_pos = name_input_rect.x + 10 + name_text.get_width()
            pygame.draw.line(self.screen, config.BLACK,
                             (cursor_pos, name_input_rect.y + 5),
                             (cursor_pos, name_input_rect.y + 25), 2)

        # Texto de ajuda abaixo do campo de nome
        hint_text = self.small_font.render("Clique para mudar seu nome", True, (200, 200, 200))
        self.screen.blit(hint_text, (config.SCREEN_WIDTH // 2 - 90, 185))

        # Exibir saldo do jogador
        balance_label = self.medium_font.render(f"Saldo: {self.player_balance} moedas", True, config.WHITE)
        self.screen.blit(balance_label, (config.SCREEN_WIDTH // 2 - 150, 220))

        # Aviso de saldo baixo
        if self.player_balance <= 100:
            warning_text = self.small_font.render("Saldo baixo!", True, (255, 100, 100))
            self.screen.blit(warning_text, (config.SCREEN_WIDTH // 2 + 100, 220))

        # Desenhar botões do menu
        self.draw_menu_buttons()

        # Botão de ajuda no canto superior direito
        help_button = pygame.Rect(config.SCREEN_WIDTH - 50, 20, 40, 40)
        mouse_pos = pygame.mouse.get_pos()
        help_color = (0, 120, 200) if help_button.collidepoint(mouse_pos) else (0, 80, 160)
        pygame.draw.rect(self.screen, help_color, help_button, border_radius=20)
        pygame.draw.rect(self.screen, config.WHITE, help_button, 2, border_radius=20)
        help_text = self.medium_font.render("?", True, config.WHITE)
        help_rect = help_text.get_rect(center=help_button.center)
        self.screen.blit(help_text, help_rect)

    def render_tutorial_popup(self):
        """Renderiza o pop-up de tutorial"""
        # Fundo semi-transparente para destacar o pop-up
        s = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        s.fill((0, 0, 0, 128))  # Preto semi-transparente
        self.screen.blit(s, (0, 0))

        # Desenhar o pop-up
        popup_rect = pygame.Rect(config.SCREEN_WIDTH // 2 - 250, config.SCREEN_HEIGHT // 2 - 200, 500, 420)
        pygame.draw.rect(self.screen, (0, 80, 0), popup_rect, border_radius=10)
        pygame.draw.rect(self.screen, config.WHITE, popup_rect, 3, border_radius=10)

        # Título do tutorial
        title = self.medium_font.render("Como Jogar Blackjack", True, config.WHITE)
        title_rect = title.get_rect(midtop=(popup_rect.centerx, popup_rect.y + 20))
        self.screen.blit(title, title_rect)

        # Linha separadora
        pygame.draw.line(self.screen, config.WHITE,
                         (popup_rect.x + 20, popup_rect.y + 50),
                         (popup_rect.x + popup_rect.width - 20, popup_rect.y + 50), 2)

        # Texto do tutorial
        tutorial_texts = [
            "Objetivo: Chegue o mais próximo possível de 21 pontos sem passar.",
            "Cartas numéricas valem seu número, figuras (J,Q,K) valem 10,",
            "e Ases podem valer 1 ou 11, conforme for melhor para a mão.",
            "",
            "Ações:",
            "- Hit: Peça mais uma carta.",
            "- Stand: Mantenha sua mão e passe a vez.",
            "- Apostar: Defina o valor da sua aposta no início de cada rodada.",
            "",
            "O dealer pega cartas até atingir pelo menos 17 pontos.",
            "Se você ultrapassar 21, perde automaticamente (estouro).",
            "Se o dealer estourar, você ganha.",
            "Se ninguém estourar, ganha quem tiver o valor mais alto."
        ]

        y_pos = popup_rect.y + 60
        for text in tutorial_texts:
            rendered_text = self.small_font.render(text, True, config.WHITE)
            text_rect = rendered_text.get_rect(topleft=(popup_rect.x + 30, y_pos))
            self.screen.blit(rendered_text, text_rect)
            y_pos += 25

        # Botão de fechar
        close_text = self.small_font.render("Clique em qualquer lugar para fechar", True, (200, 200, 200))
        close_rect = close_text.get_rect(midbottom=(popup_rect.centerx, popup_rect.bottom - 10))
        self.screen.blit(close_text, close_rect)

    def draw_menu_buttons(self):
        """Desenha os botões do menu principal"""

        # Função auxiliar para desenhar botões
        def draw_menu_button(rect, text, color, hover_color=(0, 120, 255), disabled=False, status_text=None):
            mouse_pos = pygame.mouse.get_pos()
            
            if disabled:
                button_color = (100, 100, 100)  # Cinza para botões desabilitados
            else:
                button_color = hover_color if rect.collidepoint(mouse_pos) else color

            # Desenhar botão com cantos arredondados
            pygame.draw.rect(self.screen, button_color, rect, border_radius=10)
            pygame.draw.rect(self.screen, config.WHITE, rect, 2, border_radius=10)

            # Texto do botão
            text_color = (180, 180, 180) if disabled else config.WHITE
            button_text = self.medium_font.render(text, True, text_color)
            text_rect = button_text.get_rect(center=rect.center)
            self.screen.blit(button_text, text_rect)
            
            # Status adicional (online/offline)
            if status_text:
                status_color = (0, 200, 0) if status_text == "Online" else (200, 0, 0)
                status = self.small_font.render(status_text, True, status_color)
                status_rect = status.get_rect(topright=(rect.right - 5, rect.bottom + 2))
                self.screen.blit(status, status_rect)

        # Posicionamento dos botões
        button_width = 250
        button_height = 50
        button_spacing = 20
        start_y = 280

        # Botão Jogar Sozinho
        play_alone_rect = pygame.Rect((config.SCREEN_WIDTH - button_width) // 2,
                                      start_y,
                                      button_width,
                                      button_height)
        draw_menu_button(play_alone_rect, "Jogar Sozinho", (0, 100, 0), (0, 150, 0))

        # Botão Jogar Online
        play_online_rect = pygame.Rect((config.SCREEN_WIDTH - button_width) // 2,
                                       start_y + button_height + button_spacing,
                                       button_width,
                                       button_height)
        online_status = "Online" if self.server_available else "Offline"
        draw_menu_button(
            play_online_rect, 
            "Jogar Online", 
            (0, 80, 150), (0, 100, 200), 
            disabled=not self.server_available,
            status_text=online_status
        )

        # Botão Jogar na Rede Local
        play_local_rect = pygame.Rect((config.SCREEN_WIDTH - button_width) // 2,
                                      start_y + 2 * (button_height + button_spacing),
                                      button_width,
                                      button_height)
        draw_menu_button(play_local_rect, "Jogar na Rede Local", (150, 100, 0), (200, 130, 0))

        # Botão Sair
        exit_rect = pygame.Rect((config.SCREEN_WIDTH - button_width) // 2,
                                start_y + 3 * (button_height + button_spacing),
                                button_width,
                                button_height)
        draw_menu_button(exit_rect, "Sair", (150, 0, 0), (200, 0, 0))


