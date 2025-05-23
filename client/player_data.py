import os
import json

# Caminho absoluto para o arquivo de dados
PLAYER_DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "player_data.txt")

def load_player_data():
    """Carregar dados dos jogadores do arquivo"""
    try:
        if os.path.exists(PLAYER_DATA_FILE):
            with open(PLAYER_DATA_FILE, 'r') as file:
                player_data = json.load(file)
                return player_data
        else:
            # Se o arquivo não existir, retornar um dicionário vazio
            return {}
    except Exception as e:
        print(f"Erro ao carregar dados dos jogadores: {e}")
        return {}

def get_player_name():
    """Obter o nome do jogador, usando o primeiro nome do dicionário se disponível"""
    data = load_player_data()
    if not data:
        return "Player"
    # Retorna o primeiro nome encontrado no dicionário
    return next(iter(data.keys()), "Player")

def save_player_data(player_data):
    """Salvar dados dos jogadores no arquivo"""
    try:
        with open(PLAYER_DATA_FILE, 'w') as file:
            json.dump(player_data, file)
        print(f"Dados salvos com sucesso em: {PLAYER_DATA_FILE}")
        return True
    except Exception as e:
        print(f"Erro ao salvar dados dos jogadores: {e}")
        return False

def get_player_balance(player_name):
    """Obter o saldo de um jogador pelo nome"""
    player_data = load_player_data()
    return player_data.get(player_name, 1000)  # Saldo padrão de 1000 para novos jogadores

def update_player_balance(player_name, new_balance):
    """Atualizar o saldo de um jogador"""
    player_data = load_player_data()
    
    # Se o saldo chegou a 0, resetar para 100
    if new_balance <= 0:
        new_balance = 100
    
    # Garantir que o saldo seja um número inteiro
    new_balance = int(new_balance)
    
    # Atualizar o saldo no dicionário
    player_data[player_name] = new_balance
    
    # Salvar os dados e verificar se foi bem sucedido
    if save_player_data(player_data):
        return True
    else:
        print(f"Erro ao atualizar saldo do jogador {player_name}")
        return False

def check_player_eliminated(player_name, balance):
    """Verificar se um jogador foi eliminado (saldo 0)"""
    if balance <= 0:
        return True, 100  # Eliminado, novo saldo é 100
    return False, balance
