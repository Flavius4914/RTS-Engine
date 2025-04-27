import pygame
import sys
import os
from typing import Dict, List, Optional, Tuple
from .entities import Entity, Building, Unit
from .resources import ResourceManager
from .map import GameMap
from .ui import UserInterface

class GameEngine:
    def __init__(self, screen_width: int = 1280, screen_height: int = 720):
        self.drag_selecting = False
        self.drag_start = None
        self.drag_end = None
        try:
            # Initialize Pygame
            if not pygame.get_init():
                pygame.init()
            
            # Set up display
            self.screen = pygame.display.set_mode((screen_width, screen_height))
            pygame.display.set_caption("Medieval Kingdom")
            self.clock = pygame.time.Clock()
            
            # Initialize game state
            self.running = False
            self.paused = False
            
            # Game state
            self.selected_entities: List[Entity] = []
            self.entities: List[Entity] = []
            self.buildings: List[Building] = []
            self.units: List[Unit] = []
            
            # Camera and zoom settings
            self.camera_x = 0
            self.camera_y = 0
            self.zoom_level = 1.0
            self.MIN_ZOOM = 0.5
            self.MAX_ZOOM = 2.0
            self.ZOOM_SPEED = 0.1
            
            # Game systems
            self.resource_manager = ResourceManager()
            self.game_map = GameMap(71, 71)  # Reduced map size to about half the number of tiles
            self.ui = UserInterface(self.screen)
            
            # Add Stonekeep at (9, 13)
            stonekeep = Building(9, 13, "Stonekeep")
            self.entities.append(stonekeep)
            self.buildings.append(stonekeep)
            self.game_map.tiles[13][9].building = stonekeep
            # Add Stockpile immediately to the right of player's stonekeep, (11, 13) to (14, 13)
            stockpile_right = Building(11, 13, "Stockpile")
            self.entities.append(stockpile_right)
            self.buildings.append(stockpile_right)
            for sx in range(11, 15):
                if 0 <= sx < self.game_map.width:
                    self.game_map.tiles[13][sx].building = stockpile_right
            # Place two stone (mountain) resources 6 tiles away from the stonekeep (5 tiles further)
            for dx, dy in [(6, 0), (0, 6)]:
                sx, sy = 9 + dx, 13 + dy
                if 0 <= sx < self.game_map.width and 0 <= sy < self.game_map.height:
                    self.game_map.tiles[sy][sx].tile_type = self.game_map.tiles[sy][sx].tile_type.__class__.MOUNTAIN
            # Place two stone (mountain) resources 6 tiles away from the enemy stonekeep at (65, 5)
            for dx, dy in [(6, 0), (0, 6)]:
                ex, ey = 65 + dx, 5 + dy
                if 0 <= ex < self.game_map.width and 0 <= ey < self.game_map.height:
                    self.game_map.tiles[ey][ex].tile_type = self.game_map.tiles[ey][ex].tile_type.__class__.MOUNTAIN

            # Add enemy Stonekeep at (65, 5)
            enemy_stonekeep = Building(65, 5, "EnemyStonekeep")
            self.entities.append(enemy_stonekeep)
            self.buildings.append(enemy_stonekeep)
            self.game_map.tiles[5][65].building = enemy_stonekeep
            # Add Stockpile immediately to the left of enemy stonekeep, (61, 5) to (64, 5)
            stockpile_enemy_left = Building(61, 5, "Stockpile")
            self.entities.append(stockpile_enemy_left)
            self.buildings.append(stockpile_enemy_left)
            for sx in range(61, 65):
                if 0 <= sx < self.game_map.width:
                    self.game_map.tiles[5][sx].building = stockpile_enemy_left
            # Spawn 5 enemy swordsmen near the enemy stonekeep
            # Place enemy units adjacent to the 2x2 enemy stonekeep at (65,5),(66,5),(65,6),(66,6)
            adjacent_offsets = [(-1,0), (2,0), (0,-1), (0,2), (2,2), (-1,2), (2,-1), (-1,-1)]
            spawn_tiles = []
            for dx, dy in adjacent_offsets:
                tx = 65 + dx - 8  # Move 8 tiles left
                ty = 5 + dy
                if 0 <= tx < self.game_map.width and 0 <= ty < self.game_map.height:
                    spawn_tiles.append((tx, ty))
            for i in range(5):
                tx, ty = spawn_tiles[i % len(spawn_tiles)]
                iso_x = (tx - ty) * 32
                iso_y = (tx + ty) * 16
                enemy_unit = Unit(iso_x, iso_y, "Swordsman", team="enemy")
                self.entities.append(enemy_unit)
                self.units.append(enemy_unit)
                self.game_map.tiles[ty][tx].unit = enemy_unit
            
            # Calculate initial camera position to center the map
            self.center_camera()
            
            # Game settings
            self.FPS = 60
            self.CAMERA_SPEED = 10
            
            # Building placement state
            self.building_to_place = None
            self.placement_preview = None

            # Win message state
            self.win_message_shown = False
            
        except Exception as e:
            print(f"Error initializing game engine: {e}")
            raise

    def center_camera(self):
        try:
            # Center on the middle tile of the map
            center_tile_x = self.game_map.width // 2
            center_tile_y = self.game_map.height // 2
            center_tile = self.game_map.get_tile_at(center_tile_x, center_tile_y)
            if center_tile:
                points = center_tile.get_points(self.zoom_level)
                center_x, center_y = points[0]  # Center of the tile
                self.camera_x = (self.screen.get_width() // 2) - int(center_x)
                self.camera_y = (self.screen.get_height() // 2) - int(center_y)
        except Exception as e:
            print(f"Error centering camera: {e}")
            
    def get_camera_limits(self) -> Tuple[float, float, float, float]:
        try:
            # Calculate map boundaries in screen coordinates
            map_width = self.game_map.width * 32 * self.zoom_level
            map_height = self.game_map.height * 16 * self.zoom_level
            screen_width, screen_height = self.screen.get_size()
            
            # Add padding to prevent empty space at edges
            padding = 100
            
            # Calculate limits
            min_x = screen_width - map_width - padding
            max_x = padding
            min_y = screen_height - map_height - padding
            max_y = padding
            
            return min_x, max_x, min_y, max_y
        except Exception as e:
            print(f"Error calculating camera limits: {e}")
            return 0, 0, 0, 0
            
    def clamp_camera_position(self):
        try:
            min_x, max_x, min_y, max_y = self.get_camera_limits()
            
            # Clamp camera position within limits
            self.camera_x = max(min_x, min(max_x, self.camera_x))
            self.camera_y = max(min_y, min(max_y, self.camera_y))
        except Exception as e:
            print(f"Error clamping camera position: {e}")
            
    def handle_events(self):
        try:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.paused = not self.paused
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        # First, check if a UI button was clicked
                        button_clicked = self.ui.handle_mouse(event.pos)
                        if button_clicked:
                            # Set placement mode according to button
                            if button_clicked == "Swordsman":
                                self.spawning_swordsman = True
                                self.placement_preview = None
                                self.building_to_place = None
                            elif button_clicked in ("Woodcutter", "Quarry", "Farm", "Barracks", "Archery"):
                                self.building_to_place = button_clicked
                                # Create a preview building object here if needed
                                # For now, just set a flag
                                self.placement_preview = Building(0, 0, button_clicked)
                                self.spawning_swordsman = False
                            else:
                                self.building_to_place = None
                                self.placement_preview = None
                                self.spawning_swordsman = False
                            # Do NOT start drag-select if UI button was clicked
                            continue
                        # If in placement mode, handle as placement
                        if (self.placement_preview and self.building_to_place) or getattr(self, 'spawning_swordsman', False):
                            self.handle_mouse_click(event.pos, button=1)
                        else:
                            self.drag_selecting = True
                            self.drag_start = event.pos
                            self.drag_end = event.pos
                    elif event.button == 3:  # Right click
                        self.handle_mouse_click(event.pos, button=3)
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1 and self.drag_selecting:
                        self.drag_end = event.pos
                        self.handle_drag_select(self.drag_start, self.drag_end)
                        self.drag_selecting = False
                        self.drag_start = None
                        self.drag_end = None
                    elif event.button == 1:
                        # Deselect all if not clicking a unit
                        mouse_pos = event.pos
                        clicked_unit = False
                        for entity in self.entities:
                            if isinstance(entity, Unit):
                                screen_x, screen_y = entity.get_screen_pos(self.zoom_level)
                                screen_x += self.camera_x
                                screen_y += self.camera_y
                                dx = mouse_pos[0] - screen_x
                                dy = mouse_pos[1] - screen_y
                                distance = (dx ** 2 + dy ** 2) ** 0.5
                                if distance < 20 * self.zoom_level:
                                    clicked_unit = True
                                    break
                        if not clicked_unit:
                            for entity in self.selected_entities:
                                entity.selected = False
                            self.selected_entities.clear()
                elif event.type == pygame.MOUSEMOTION:
                    if getattr(self, 'drag_selecting', False):
                        self.drag_end = pygame.mouse.get_pos()
                elif event.type == pygame.MOUSEWHEEL:
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    if event.y > 0:
                        self.zoom_in()
                    else:
                        self.zoom_out()
        except Exception as e:
            print(f"Error handling events: {e}")
        try:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.paused = not self.paused
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    # Building placement mode: handle left/right click for placement/cancel
                    if self.placement_preview and self.building_to_place:
                        self.handle_mouse_click(event.pos, button=event.button)
                        return
                    if event.button == 1:  # Left click
                        self.drag_selecting = True
                        self.drag_start = pygame.mouse.get_pos()
                        self.drag_end = self.drag_start
                        # Check UI buttons first
                        ui_result = self.ui.handle_mouse(event.pos)
                        if ui_result:
                            self.start_building_placement(ui_result)
                            return
                        self.handle_mouse_click(event.pos)
                    elif event.button == 3:  # Right click
                        self.handle_mouse_click(event.pos, button=3)
                    elif event.button == 4:  # Mouse wheel up
                        self.zoom_in()
                    elif event.button == 5:  # Mouse wheel down
                        self.zoom_out()
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1 and getattr(self, 'drag_selecting', False):
                        self.drag_end = pygame.mouse.get_pos()
                        self.handle_drag_select(self.drag_start, self.drag_end)
                        self.drag_selecting = False
                elif event.type == pygame.MOUSEMOTION:
                    if getattr(self, 'drag_selecting', False):
                        self.drag_end = pygame.mouse.get_pos()
                elif event.type == pygame.MOUSEWHEEL:
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    if event.y > 0:
                        self.zoom_in()
                    else:
                        self.zoom_out()
        except Exception as e:
            print(f"Error handling events: {e}")
            
    def zoom_in(self):
        try:
            if self.zoom_level < self.MAX_ZOOM:
                # Store old zoom level
                old_zoom = self.zoom_level
                
                # Increase zoom
                self.zoom_level = min(self.zoom_level + self.ZOOM_SPEED, self.MAX_ZOOM)
                
                # Get mouse position
                mouse_x, mouse_y = pygame.mouse.get_pos()
                
                # Calculate the world position under the mouse before zooming
                world_x = (mouse_x - self.camera_x) / old_zoom
                world_y = (mouse_y - self.camera_y) / old_zoom
                
                # Calculate new camera position to keep the world position under the mouse
                self.camera_x = mouse_x - world_x * self.zoom_level
                self.camera_y = mouse_y - world_y * self.zoom_level
                
                # Clamp camera position
                self.clamp_camera_position()
        except Exception as e:
            print(f"Error zooming in: {e}")
            
    def zoom_out(self):
        try:
            if self.zoom_level > self.MIN_ZOOM:
                # Store old zoom level
                old_zoom = self.zoom_level
                
                # Decrease zoom
                self.zoom_level = max(self.zoom_level - self.ZOOM_SPEED, self.MIN_ZOOM)
                
                # Get mouse position
                mouse_x, mouse_y = pygame.mouse.get_pos()
                
                # Calculate the world position under the mouse before zooming
                world_x = (mouse_x - self.camera_x) / old_zoom
                world_y = (mouse_y - self.camera_y) / old_zoom
                
                # Calculate new camera position to keep the world position under the mouse
                self.camera_x = mouse_x - world_x * self.zoom_level
                self.camera_y = mouse_y - world_y * self.zoom_level
                
                # Clamp camera position
                self.clamp_camera_position()
        except Exception as e:
            print(f"Error zooming out: {e}")
            
    def handle_drag_select(self, start: Tuple[int, int], end: Tuple[int, int]):
        # Select all units within the drag rectangle
        if not start or not end:
            return
        x1, y1 = start
        x2, y2 = end
        left, right = min(x1, x2), max(x1, x2)
        top, bottom = min(y1, y2), max(y1, y2)
        self.selected_entities.clear()
        for entity in self.entities:
            if isinstance(entity, Unit):
                screen_x, screen_y = entity.get_screen_pos(self.zoom_level)
                screen_x += self.camera_x
                screen_y += self.camera_y
                if left <= screen_x <= right and top <= screen_y <= bottom:
                    self.selected_entities.append(entity)
                    entity.selected = True
                else:
                    entity.selected = False

    def get_formation_positions(self, center: Tuple[float, float], count: int, spacing: float = 40.0):
        # Arrange positions in a grid centered at 'center'
        import math
        if count == 0:
            return []
        cols = math.ceil(math.sqrt(count))
        rows = math.ceil(count / cols)
        positions = []
        start_x = center[0] - (cols - 1) * spacing / 2
        start_y = center[1] - (rows - 1) * spacing / 2
        i = 0
        for r in range(rows):
            for c in range(cols):
                if i >= count:
                    break
                x = start_x + c * spacing
                y = start_y + r * spacing
                positions.append((x, y))
                i += 1
        return positions

    def handle_mouse_click(self, pos: Tuple[int, int], button: int = 1):
        if button == 3 and self.selected_entities:
            # Right click: move selected units to formation at click position
            positions = self.get_formation_positions(pos, len(self.selected_entities), spacing=40.0)
            for entity, dest in zip(self.selected_entities, positions):
                entity.move_to(dest)
            return
        # Swordsman spawn mode
        if getattr(self, 'spawning_swordsman', False):
            try:
                # Convert screen coordinates to world coordinates
                world_x = (pos[0] - self.camera_x) / self.zoom_level
                world_y = (pos[1] - self.camera_y) / self.zoom_level
                
                # Get clicked tile
                tile = self.game_map.get_tile_at_screen_pos(world_x, world_y, self.zoom_level, self.camera_x, self.camera_y)
                if tile:
                    iso_x = (tile.x - tile.y) * 32
                    iso_y = (tile.x + tile.y) * 16
                    print(f"[DEBUG] Spawning Swordsman at tile ({tile.x}, {tile.y}) -> iso ({iso_x}, {iso_y})")
                    swordsman = Unit(iso_x, iso_y, "Swordsman")
                    self.entities.append(swordsman)
                    self.units.append(swordsman)
                    self.game_map.tiles[tile.y][tile.x].unit = swordsman
                else:
                    print("[ERROR] No valid tile found for spawning Swordsman.")
            except Exception as e:
                print(f"Error spawning swordsman: {e}")
            self.spawning_swordsman = False
            self.placement_preview = None
            self.building_to_place = None
            return  # Do not process selection logic if placing unit
        else:
            # Building placement mode
            # Compute tile under mouse
            world_x = (pos[0] - self.camera_x) / self.zoom_level
            world_y = (pos[1] - self.camera_y) / self.zoom_level
            tile = self.game_map.get_tile_at_screen_pos(world_x, world_y, self.zoom_level, self.camera_x, self.camera_y)
            if self.placement_preview and self.building_to_place and tile:
                preview = self.placement_preview
                width = max(1, preview.width // 64)
                height = max(1, preview.height // 64)
                place_x = tile.x - (width // 2)
                place_y = tile.y - (height // 2)
                if button == 1:  # Left click to place
                    if self.game_map.can_build_at(place_x, place_y, width, height):
                        try:
                            building = Building(place_x, place_y, self.building_to_place, resource_manager=self.resource_manager)
                            self.entities.append(building)
                            self.buildings.append(building)
                            for dy in range(height):
                                for dx in range(width):
                                    t = self.game_map.get_tile_at(place_x + dx, place_y + dy)
                                    if t:
                                        t.building = building
                        except Exception as e:
                            print(f"Error placing building: {e}")
                        self.building_to_place = None
                        self.placement_preview = None
                    # If not valid, don't place, keep preview
                elif button == 3:  # Right click to cancel
                    self.building_to_place = None
                    self.placement_preview = None
                return  # Do not process selection logic if placing building

            # --- Regular selection/move logic below ---
            # Clear previous selection
            for entity in self.selected_entities:
                entity.selected = False
            self.selected_entities.clear()
            # Check if clicked on an entity
            for entity in self.entities:
                screen_x, screen_y = entity.get_screen_pos(self.zoom_level)
                screen_x += self.camera_x
                screen_y += self.camera_y
                dx = pos[0] - screen_x
                dy = pos[1] - screen_y
                distance = (dx ** 2 + dy ** 2) ** 0.5
                if distance < 20 * self.zoom_level:  # Selection radius
                    self.selected_entities.append(entity)
                    entity.selected = True
            # (Right click selection logic is handled above)
            # (No nested try/except here)

    def start_building_placement(self, building_type: str):
        try:
            if building_type == "Swordsman":
                self.spawning_swordsman = True
                self.building_to_place = None
                self.placement_preview = None
            else:
                self.building_to_place = building_type
                # Create a preview building
                self.placement_preview = Building(0, 0, building_type)
        except Exception as e:
            print(f"Error starting building placement: {e}")
            
    def update(self):
        try:
            if not self.paused:
                # --- Enemy AI: make enemy units attack player units if close ---
                for enemy in self.units:
                    if getattr(enemy, 'team', 'player') == 'enemy':
                        # Find nearest player unit
                        min_dist = float('inf')
                        target = None
                        for unit in self.units:
                            if getattr(unit, 'team', 'player') == 'player':
                                dist = ((enemy.x - unit.x) ** 2 + (enemy.y - unit.y) ** 2) ** 0.5
                                if dist < 400 and dist < min_dist:  # 400 px aggro range
                                    min_dist = dist
                                    target = unit
                        if target:
                            enemy.move_to((target.x, target.y))
                # Handle keyboard input for camera movement
                keys = pygame.key.get_pressed()
                if keys[pygame.K_LEFT]:
                    self.camera_x += self.CAMERA_SPEED / self.zoom_level
                if keys[pygame.K_RIGHT]:
                    self.camera_x -= self.CAMERA_SPEED / self.zoom_level
                if keys[pygame.K_UP]:
                    self.camera_y += self.CAMERA_SPEED / self.zoom_level
                if keys[pygame.K_DOWN]:
                    self.camera_y -= self.CAMERA_SPEED / self.zoom_level

                # WASD unit movement for selected units
                dx, dy = 0, 0
                if keys[pygame.K_a]:
                    dx -= 1
                if keys[pygame.K_d]:
                    dx += 1
                if keys[pygame.K_w]:
                    dy -= 1
                if keys[pygame.K_s]:
                    dy += 1
                if dx != 0 or dy != 0:
                    for entity in self.selected_entities:
                        if hasattr(entity, 'speed'):
                            norm = (dx ** 2 + dy ** 2) ** 0.5
                            if norm == 0:
                                continue
                            move_x = (dx / norm) * entity.speed
                            move_y = (dy / norm) * entity.speed
                            entity.x += move_x
                            entity.y += move_y
                    
                # Clamp camera position
                self.clamp_camera_position()
                
                # Update entities and handle unit collisions/attacks
                all_units = [e for e in self.entities if isinstance(e, Unit)]
                all_buildings = [e for e in self.entities if isinstance(e, Building)]
                to_remove = []
                to_remove_buildings = []
                for entity in self.entities:
                    if isinstance(entity, Unit):
                        entity.all_buildings = all_buildings
                        entity.update(all_units=all_units)
                        if entity.health <= 0:
                            to_remove.append(entity)
                    elif isinstance(entity, Building):
                        entity.update()
                        if hasattr(entity, 'health') and entity.health <= 0:
                            to_remove_buildings.append(entity)
                    else:
                        entity.update()
                # Remove dead units
                for dead in to_remove:
                    if dead in self.entities:
                        self.entities.remove(dead)
                    if dead in self.units:
                        self.units.remove(dead)
                    # Remove from map tile if needed
                    for row in self.game_map.tiles:
                        for tile in row:
                            if hasattr(tile, 'unit') and tile.unit is dead:
                                tile.unit = None
                # Remove destroyed buildings
                for b in to_remove_buildings:
                    if b in self.entities:
                        self.entities.remove(b)
                    if b in self.buildings:
                        self.buildings.remove(b)
                    # Optionally, remove from map tiles
                    for row in self.game_map.tiles:
                        for tile in row:
                            if hasattr(tile, 'building') and tile.building is b:
                                tile.building = None
                    
                # Update placement preview
                if self.placement_preview:
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    world_x = (mouse_x - self.camera_x) / self.zoom_level
                    world_y = (mouse_y - self.camera_y) / self.zoom_level
                    tile = self.game_map.get_tile_at_screen_pos(world_x, world_y, self.zoom_level, self.camera_x, self.camera_y)
                    if tile:
                        self.placement_preview.x = tile.x
                        self.placement_preview.y = tile.y

            # Check win condition: all enemy swordsmen defeated
            if not self.win_message_shown:
                enemy_swordsmen = [u for u in self.units if getattr(u, 'unit_type', None) == 'Swordsman' and getattr(u, 'team', None) == 'enemy' and getattr(u, 'health', 0) > 0]
                if len(enemy_swordsmen) == 0:
                    self.win_message_shown = True
        except Exception as e:
            print(f"Error in update: {e}")
            
    def render(self):
        try:
            # Clear screen
            self.screen.fill((0, 0, 0))
            
            # Render map
            self.game_map.render(self.screen, self.zoom_level, self.camera_x, self.camera_y)
            
            # Render entities
            for entity in self.entities:
                entity.render(self.screen, self.zoom_level, self.camera_x, self.camera_y)
            # Render selection rectangle if dragging
            if getattr(self, 'drag_selecting', False) and self.drag_start and self.drag_end:
                x1, y1 = self.drag_start
                x2, y2 = self.drag_end
                rect = pygame.Rect(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
                pygame.draw.rect(self.screen, (0, 255, 0), rect, 2)
            # Render placement preview
            if self.placement_preview:
                self.placement_preview.render(self.screen, self.zoom_level, self.camera_x, self.camera_y)
            # Render UI
            self.ui.render()

            # Render win message if player won
            if getattr(self, 'win_message_shown', False):
                font = pygame.font.Font(None, 80)
                text_surface = font.render("You won!", True, (255, 215, 0))
                text_rect = text_surface.get_rect(center=(self.screen.get_width() // 2, self.screen.get_height() // 2))
                # Draw a semi-transparent background
                overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 180))
                self.screen.blit(overlay, (0, 0))
                self.screen.blit(text_surface, text_rect)
            # Update display
            pygame.display.flip()
        except Exception as e:
            print(f"Error in render: {e}")
            
    def handle_drag_select(self, start, end):
        # Convert screen rectangle to world rectangle
        x1, y1 = start
        x2, y2 = end
        left = min(x1, x2)
        right = max(x1, x2)
        top = min(y1, y2)
        bottom = max(y1, y2)
        # Deselect all
        for entity in self.selected_entities:
            entity.selected = False
        self.selected_entities.clear()
        # Select all units in rectangle
        for entity in self.entities:
            if isinstance(entity, Unit):
                screen_x, screen_y = entity.get_screen_pos(self.zoom_level)
                screen_x += self.camera_x
                screen_y += self.camera_y
                if left <= screen_x <= right and top <= screen_y <= bottom:
                    entity.selected = True
                    self.selected_entities.append(entity)

    def run(self):
        try:
            self.running = True
            while self.running:
                self.handle_events()
                self.update()
                self.render()
                self.clock.tick(self.FPS)
        except Exception as e:
            print(f"Error in game loop: {e}")
        finally:
            pygame.quit()
            sys.exit() 