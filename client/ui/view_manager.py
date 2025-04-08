from enum import Enum, auto

class GameView(Enum):
    """Enum representing different game views/screens"""
    MENU = auto()
    BOT_SELECTION = auto()
    ROOM_BROWSER = auto()
    CREATE_ROOM = auto()
    JOIN_ROOM = auto()
    LOBBY = auto()
    GAME = auto()

class ViewManager:
    """Manages the current view state of the game"""
    
    def __init__(self):
        self._current_view = GameView.MENU
        self._view_history = []
        self.connection_mode = 'online'

    
    @property
    def current_view(self):
        """Get the current view as a string (for backward compatibility)"""
        return self._current_view.name
    
    def set_view(self, view_name: str):
        """Set the current view by name"""
        try:
            new_view = GameView[view_name]
            self._view_history.append(self._current_view)
            self._current_view = new_view
        except KeyError:
            raise ValueError(f"Invalid view name: {view_name}")
    
    def go_back(self):
        """Return to the previous view"""
        if self._view_history:
            self._current_view = self._view_history.pop()
    
    def is_view(self, view_name: str) -> bool:
        """Check if current view matches the given view name"""
        try:
            return self._current_view == GameView[view_name]
        except KeyError:
            return False 