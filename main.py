import pygame
import sys
import os
import shared.config as config

# Adicione o diretório raiz ao path para importar os módulos compartilhados
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from client.game_client import BlackjackClient

# Inicializar pygame
pygame.init()

def show_splash_screen():
    """Mostrar tela de splash com animação"""
    screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    pygame.display.set_caption("Blackjack 21 P2P - Carregando...")
    clock = pygame.time.Clock()

    # Fontes
    title_font = pygame.font.SysFont("Arial", 72)
    subtitle_font = pygame.font.SysFont("Arial", 36)

    # Textos
    title = title_font.render("Blackjack 21", True, config.WHITE)
    subtitle = subtitle_font.render("P2P Version", True, config.WHITE)
    loading = subtitle_font.render("Carregando...", True, config.WHITE)

    # Posições
    title_pos = (config.SCREEN_WIDTH // 2 - title.get_width() // 2, config.SCREEN_HEIGHT // 3)
    subtitle_pos = (config.SCREEN_WIDTH // 2 - subtitle.get_width() // 2, config.SCREEN_HEIGHT // 2)
    loading_pos = (config.SCREEN_WIDTH // 2 - loading.get_width() // 2, 2 * config.SCREEN_HEIGHT // 3)

    # Animação de loading
    dots = 0
    start_time = pygame.time.get_ticks()

    running = True
    while running:
        current_time = pygame.time.get_ticks()
        elapsed_time = (current_time - start_time) // 1000  # Segundos

        # Atualizar dots a cada 500ms
        if elapsed_time * 2 > dots:
            dots = elapsed_time * 2
            if dots > 3:
                dots = 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # Limpar tela
        screen.fill(config.GREEN)

        # Desenhar textos
        screen.blit(title, title_pos)
        screen.blit(subtitle, subtitle_pos)
        
        # Atualizar texto de loading com dots
        loading_text = subtitle_font.render("Carregando" + "." * dots, True, config.WHITE)
        screen.blit(loading_text, loading_pos)

        pygame.display.flip()
        clock.tick(60)

        # Sair após 3 segundos
        if elapsed_time >= 3:
            running = False

def main():
    """Função principal"""
    try:
        # Mostrar tela de splash
        show_splash_screen()
        
        # Verificar se o servidor de lobby está disponível
        try:
            from shared.network.connection_checker import check_server_connection
            from server.matchmaking import MatchmakingService
            
            # Tenta conectar ao servidor de lobby com timeout curto
            matchmaking = MatchmakingService()
            success, _ = matchmaking.list_games()
            
            if not success:
                print("AVISO: Servidor de lobby não está disponível.")
                print("Para jogar online, execute primeiro o servidor com:")
                print("python server/run_lobby_server.py")
                print("Continuando no modo offline...")
        except Exception as server_error:
            print(f"Erro ao verificar servidor: {server_error}")
            print("Continuando no modo offline...")

        # Iniciar o jogo
        client = BlackjackClient()
        client.start()

    except Exception as e:
        print(f"Erro ao iniciar o jogo: {e}")
        pygame.quit()
        sys.exit(1)

if __name__ == '__main__':
    main()


