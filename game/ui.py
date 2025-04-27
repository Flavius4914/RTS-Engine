import pygame
from typing import Dict, List, Tuple, Optional
from .resources import ResourceManager, ResourceType

class Button:
    def __init__(self, x: int, y: int, width: int, height: int, text: str, color: Tuple[int, int, int]):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover = False
        
    def render(self, screen: pygame.Surface):
        color = self.color if not self.hover else tuple(min(c + 30, 255) for c in self.color)
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, (0, 0, 0), self.rect, 2)
        
        font = pygame.font.Font(None, 24)
        text_surface = font.render(self.text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)
        
    def handle_mouse(self, pos: Tuple[int, int]) -> bool:
        self.hover = self.rect.collidepoint(pos)
        return self.hover

class UserInterface:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.buttons: List[Button] = []
        self.setup_buttons()
        
    def setup_buttons(self):
        # Resource gathering buttons
        self.buttons.append(Button(10, 10, 100, 30, "Woodcutter", (139, 69, 19)))
        self.buttons.append(Button(120, 10, 100, 30, "Quarry", (169, 169, 169)))
        self.buttons.append(Button(230, 10, 100, 30, "Farm", (34, 139, 34)))
        
        # Military buttons
        self.buttons.append(Button(10, 50, 100, 30, "Barracks", (139, 0, 0)))
        self.buttons.append(Button(120, 50, 100, 30, "Archery", (160, 82, 45)))
        self.buttons.append(Button(230, 50, 100, 30, "Swordsman", (70, 130, 180)))
        
    def render(self):
        # Create a surface for UI elements (not affected by camera/zoom)
        ui_surface = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        
        # Render resource counters
        self.render_resources(ui_surface)
        
        # Render buttons
        for button in self.buttons:
            button.render(ui_surface)
            
        # Blit UI surface onto main screen
        self.screen.blit(ui_surface, (0, 0))
            
    def render_resources(self, screen: pygame.Surface):
        font = pygame.font.Font(None, 24)
        y_offset = 10
        
        for resource_type in ResourceType:
            amount = 0  # We'll get this from the resource manager later
            text = f"{resource_type.value}: {amount}"
            text_surface = font.render(text, True, (255, 255, 255))
            screen.blit(text_surface, (self.screen.get_width() - 150, y_offset))
            y_offset += 25
            
    def handle_mouse(self, pos: Tuple[int, int]) -> Optional[str]:
        for button in self.buttons:
            if button.handle_mouse(pos):
                return button.text
        return None 