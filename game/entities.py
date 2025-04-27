import pygame
from typing import Tuple, Optional, List
from enum import Enum

class EntityType(Enum):
    BUILDING = 1
    UNIT = 2
    RESOURCE = 3

class Entity:
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.selected = False
        
        # Base screen position for oblique view
        self.base_screen_x = (x - y) * 32
        self.base_screen_y = (x + y) * 16
        
        # Cache for screen positions at different zoom levels
        self._screen_pos_cache = {}
        
    def get_screen_pos(self, zoom_level: float = 1.0) -> Tuple[float, float]:
        # Return cached position if available
        if zoom_level in self._screen_pos_cache:
            return self._screen_pos_cache[zoom_level]
            
        pos = (
            self.base_screen_x * zoom_level,
            self.base_screen_y * zoom_level
        )
        self._screen_pos_cache[zoom_level] = pos
        return pos
        
    def update(self):
        pass
        
    def render(self, screen: pygame.Surface, zoom_level: float = 1.0, camera_x: float = 0, camera_y: float = 0):
        if self.selected:
            # Draw selection circle
            screen_x, screen_y = self.get_screen_pos(zoom_level)
            screen_x += camera_x
            screen_y += camera_y
            
            # Check if entity is visible on screen
            screen_rect = screen.get_rect()
            entity_rect = pygame.Rect(
                screen_x - 20 * zoom_level,
                screen_y - 20 * zoom_level,
                40 * zoom_level,
                40 * zoom_level
            )
            
            if screen_rect.colliderect(entity_rect):
                pygame.draw.circle(screen, (255, 255, 0), (int(screen_x), int(screen_y)), int(20 * zoom_level), 2)

class Building(Entity):
    def __init__(self, x: int, y: int, building_type: str, resource_manager=None):
        if building_type in ["Stonekeep", "EnemyStonekeep"]:
            super().__init__(x, y, 128, 128)  # 2x2 tiles (each tile 64x64)
        elif building_type == "Stockpile":
            super().__init__(x, y, 256, 32)  # 4 tiles wide, half tile tall
        else:
            super().__init__(x, y, 64, 64)
        self.building_type = building_type
        self.health = 100
        self.max_health = 100
        self.production_rate = 0
        self._points_cache = {}
        self.resource_timer = 0  # Timer for resource production
        self.resource_manager = resource_manager
        
    def get_points(self, zoom_level: float = 1.0) -> List[Tuple[float, float]]:
        # Return cached points if available
        if zoom_level in self._points_cache:
            return self._points_cache[zoom_level]
        
        screen_x, screen_y = self.get_screen_pos(zoom_level)
        if self.building_type in ["Stonekeep", "EnemyStonekeep"]:
            # 2x2 tiles (128x128): draw a larger hex/octagon
            points = [
                (screen_x, screen_y - 64 * zoom_level),          # Top
                (screen_x + 64 * zoom_level, screen_y - 32 * zoom_level),     # Top right
                (screen_x + 64 * zoom_level, screen_y + 32 * zoom_level),     # Bottom right
                (screen_x, screen_y + 64 * zoom_level),          # Bottom
                (screen_x - 64 * zoom_level, screen_y + 32 * zoom_level),     # Bottom left
                (screen_x - 64 * zoom_level, screen_y - 32 * zoom_level),     # Top left
            ]
        else:
            # Default building (1x1 tile)
            points = [
                (screen_x, screen_y - 32 * zoom_level),          # Top
                (screen_x + 32 * zoom_level, screen_y - 16 * zoom_level),     # Top right
                (screen_x + 32 * zoom_level, screen_y + 16 * zoom_level),     # Bottom right
                (screen_x, screen_y + 32 * zoom_level),          # Bottom
                (screen_x - 32 * zoom_level, screen_y + 16 * zoom_level),     # Bottom left
                (screen_x - 32 * zoom_level, screen_y - 16 * zoom_level),     # Top left
            ]
        self._points_cache[zoom_level] = points
        return points
        
    def update(self, dt=1):
        # Resource gathering logic: every 30 seconds, add 10 resources
        from game.resources import ResourceType
        # Only produce if on a resource tile (handled by placement logic)
        if self.building_type == "Woodcutter" and self.resource_manager:
            self.resource_timer += dt
            if self.resource_timer >= 30:
                self.resource_manager.add_resource(ResourceType.WOOD, 10)
                self.resource_timer = 0
        elif self.building_type == "Quarry" and self.resource_manager:
            self.resource_timer += dt
            if self.resource_timer >= 30:
                self.resource_manager.add_resource(ResourceType.STONE, 10)
                self.resource_timer = 0
        elif self.building_type == "Farm" and self.resource_manager:
            self.resource_timer += dt
            if self.resource_timer >= 30:
                self.resource_manager.add_resource(ResourceType.FOOD, 10)
                self.resource_timer = 0
        # Call parent update if needed
        super().update()
        
    def render(self, screen: pygame.Surface, zoom_level: float = 1.0, camera_x: float = 0, camera_y: float = 0):
        try:
            # Get points and apply camera offset
            points = self.get_points(zoom_level)
            offset_points = [(x + camera_x, y + camera_y) for x, y in points]
            
            # Check if building is visible on screen
            screen_rect = screen.get_rect()
            building_rect = pygame.Rect(
                min(x for x, _ in offset_points),
                min(y for _, y in offset_points),
                max(x for x, _ in offset_points) - min(x for x, _ in offset_points),
                max(y for _, y in offset_points) - min(y for _, y in offset_points)
            )
            
            if not screen_rect.colliderect(building_rect):
                return
                
            # Draw building
            color = (139, 69, 19)  # Brown color for buildings
            pygame.draw.polygon(screen, color, offset_points)
            pygame.draw.polygon(screen, (0, 0, 0), offset_points, 1)
            
            # Draw health bar
            screen_x, screen_y = self.get_screen_pos(zoom_level)
            screen_x += camera_x
            screen_y += camera_y
            
            health_width = (self.health / self.max_health) * 64 * zoom_level
            health_x = screen_x - 32 * zoom_level
            health_y = screen_y - 40 * zoom_level
            pygame.draw.rect(screen, (255, 0, 0), (health_x, health_y, health_width, 5 * zoom_level))
            
            # Draw selection circle if selected
            if self.selected:
                pygame.draw.circle(screen, (255, 255, 0), (int(screen_x), int(screen_y)), int(20 * zoom_level), 2)
        except Exception as e:
            print(f"Error rendering building: {e}")

class Unit(Entity):
    def get_screen_pos(self, zoom_level: float = 1.0) -> Tuple[float, float]:
        # x and y are pixel coordinates for units
        return (self.x * zoom_level, self.y * zoom_level)

    def __init__(self, x: int, y: int, unit_type: str, team: str = "player"):
        super().__init__(x, y, 32, 32)
        self.unit_type = unit_type
        self.health = 100
        self.max_health = 100
        self.speed = 2
        self.target_pos: Optional[Tuple[int, int]] = None
        self.attack_damage = 10
        self.attack_range = 50
        self.team = team  # "player" or "enemy"
        # Cache for points at different zoom levels
        self._points_cache = {}
        
    def get_points(self, zoom_level: float = 1.0) -> List[Tuple[float, float]]:
        # Use pixel coordinates for the triangle, make it visible and centered on the unit
        screen_x, screen_y = self.get_screen_pos(zoom_level)
        size = 16 * zoom_level  # Half the triangle size (32px total)
        points = [
            (screen_x, screen_y - size),         # Top
            (screen_x + size, screen_y + size),  # Bottom right
            (screen_x - size, screen_y + size),  # Bottom left
        ]
        return points
        
    def move_to(self, target_pos: Tuple[int, int]):
        print(f"[DEBUG] {self.unit_type} at ({self.x:.2f}, {self.y:.2f}) received move command to {target_pos}")
        self.target_pos = target_pos
        
    def update(self, all_units=None):
        if all_units is None:
            all_units = []
        unit_radius = 16  # units are drawn as triangles in a ~32x32 box
        # --- Attack logic (units) ---
        attack_range = 30
        did_attack_unit = False
        for other in all_units:
            if other is not self and getattr(other, 'team', None) != self.team:
                dist = ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5
                if dist < attack_range:
                    other.health -= self.attack_damage * 0.1  # Damage per frame
                    self.health -= other.attack_damage * 0.05
                    self.target_pos = None
                    did_attack_unit = True
                    # print(f"{self.unit_type} at ({self.x:.1f},{self.y:.1f}) attacks {other.unit_type} at ({other.x:.1f},{other.y:.1f})")
        # --- Attack logic (buildings, use same collision as movement) ---
        from .entities import Building
        did_attack_building = False
        for building in [b for b in getattr(self, 'all_buildings', []) if isinstance(b, Building)]:
            btype = getattr(building, 'building_type', "").lower()
            # Consider building as enemy if player's unit and 'enemy' in type, or vice versa
            if self.team == "player" and "enemy" in btype:
                is_enemy_building = True
            elif self.team == "enemy" and "enemy" not in btype:
                is_enemy_building = True
            else:
                is_enemy_building = False
            if is_enemy_building:
                bx, by = building.x, building.y
                bw, bh = getattr(building, 'width', 64), getattr(building, 'height', 64)
                closest_x = min(max(self.x, bx), bx + bw)
                closest_y = min(max(self.y, by), by + bh)
                dist = ((self.x - closest_x) ** 2 + (self.y - closest_y) ** 2) ** 0.5
                if dist <= unit_radius:
                    building.health -= self.attack_damage * 0.08  # Damage per frame
                    self.target_pos = None
                    did_attack_building = True
                    # print(f"{self.unit_type} at ({self.x:.1f},{self.y:.1f}) attacks {building.building_type} at ({bx},{by})")
        # --- Prevent overlap with other units and buildings (block movement if collision would occur) ---
        if self.target_pos and not (did_attack_unit or did_attack_building):
            dx = self.target_pos[0] - self.x
            dy = self.target_pos[1] - self.y
            distance = (dx ** 2 + dy ** 2) ** 0.5
            if distance > self.speed:
                next_x = self.x + (dx / distance) * self.speed
                next_y = self.y + (dy / distance) * self.speed
                blocked = False
                # Check collision with units
                for other in all_units:
                    if other is not self:
                        dist = ((next_x - other.x) ** 2 + (next_y - other.y) ** 2) ** 0.5
                        if dist < 28:  # min_dist
                            blocked = True
                            # print(f"Blocked by unit at {other.x},{other.y}")
                            break
                # Check collision with buildings
                if not blocked:
                    for building in getattr(self, 'all_buildings', []):
                        bx, by = building.x, building.y
                        bw, bh = getattr(building, 'width', 64), getattr(building, 'height', 64)
                        closest_x = min(max(next_x, bx), bx + bw)
                        closest_y = min(max(next_y, by), by + bh)
                        dist = ((next_x - closest_x) ** 2 + (next_y - closest_y) ** 2) ** 0.5
                        if dist < unit_radius:
                            blocked = True
                            # print(f"Blocked by building at {bx},{by}")
                            break
                if not blocked:
                    self.x = next_x
                    self.y = next_y
                else:
                    self.target_pos = None
            else:
                self.target_pos = None
        # Clamp health
        self.health = max(0, self.health)

    def render(self, screen: pygame.Surface, zoom_level: float = 1.0, camera_x: float = 0, camera_y: float = 0):
        try:
            # Get points and apply camera offset
            points = self.get_points(zoom_level)
            offset_points = [(x + camera_x, y + camera_y) for x, y in points]
            
            # Check if unit is visible on screen
            screen_rect = screen.get_rect()
            unit_rect = pygame.Rect(
                min(x for x, _ in offset_points),
                min(y for _, y in offset_points),
                max(x for x, _ in offset_points) - min(x for x, _ in offset_points),
                max(y for _, y in offset_points) - min(y for _, y in offset_points)
            )
            
            if not screen_rect.colliderect(unit_rect):
                return
                
            # Draw unit as a triangle
            color = (0, 0, 255) if self.team == "player" else (255, 0, 0)  # Blue for player, red for enemy
            pygame.draw.polygon(screen, color, offset_points)
            pygame.draw.polygon(screen, (0, 0, 0), offset_points, 1)
            
            # Draw health bar
            screen_x, screen_y = self.get_screen_pos(zoom_level)
            screen_x += camera_x
            screen_y += camera_y
            
            health_width = (self.health / self.max_health) * 24 * zoom_level
            health_x = screen_x - 12 * zoom_level
            health_y = screen_y - 20 * zoom_level
            pygame.draw.rect(screen, (255, 0, 0), (health_x, health_y, health_width, 3 * zoom_level))
            
            # Draw selection circle if selected
            if self.selected:
                pygame.draw.circle(screen, (255, 255, 0), (int(screen_x), int(screen_y)), int(20 * zoom_level), 2)
        except Exception as e:
            print(f"Error rendering unit: {e}, x={self.x}, y={self.y}, type={type(self)}") 