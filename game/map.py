import pygame
import random
from typing import List, Tuple, Optional
from enum import Enum

class TileType(Enum):
    GRASS = 1
    WATER = 2
    FOREST = 3
    MOUNTAIN = 4
    DIRT = 5  # Brown patch

class Tile:
    def __init__(self, x: int, y: int, tile_type: TileType):
        self.x = x
        self.y = y
        self.tile_type = tile_type
        self.resource_amount = 0
        self.building = None
        
        # Base screen position for oblique view
        self.base_screen_x = (x - y) * 32
        self.base_screen_y = (x + y) * 16
        
        # Cache for points at different zoom levels
        self._points_cache = {}
        
    def get_points(self, zoom_level: float = 1.0) -> List[Tuple[float, float]]:
        # Return cached points if available
        if zoom_level in self._points_cache:
            return self._points_cache[zoom_level]
        # Calculate scaled screen position
        screen_x = self.base_screen_x * zoom_level
        screen_y = self.base_screen_y * zoom_level
        # Create 4-point diamond (isometric square)
        points = [
            (screen_x, screen_y - 16 * zoom_level),  # Top
            (screen_x + 32 * zoom_level, screen_y),  # Right
            (screen_x, screen_y + 16 * zoom_level),  # Bottom
            (screen_x - 32 * zoom_level, screen_y),  # Left
        ]
        self._points_cache[zoom_level] = points
        return points
        
    def render(self, screen: pygame.Surface, zoom_level: float = 1.0, camera_x: float = 0, camera_y: float = 0):
        try:
            # Get scaled points
            points = self.get_points(zoom_level)
            # Apply camera offset
            offset_points = [(int(x + camera_x), int(y + camera_y)) for x, y in points]
            # Check if tile is visible on screen
            screen_rect = screen.get_rect()
            tile_rect = pygame.Rect(
                int(min(x for x, _ in offset_points)),
                int(min(y for _, y in offset_points)),
                int(max(x for x, _ in offset_points) - min(x for x, _ in offset_points)),
                int(max(y for _, y in offset_points) - min(y for _, y in offset_points))
            )
            if not screen_rect.colliderect(tile_rect):
                return
            colors = {
                TileType.GRASS: (34, 139, 34),  # Forest green
                TileType.WATER: (0, 0, 139),    # Dark blue
                TileType.FOREST: (0, 100, 0),   # Dark green
                TileType.MOUNTAIN: (139, 137, 137),  # Gray
                TileType.DIRT: (139, 69, 19)    # Brown
            }
            # Draw tile diamond
            pygame.draw.polygon(screen, colors[self.tile_type], offset_points)
            pygame.draw.polygon(screen, (0, 0, 0), offset_points, 1)  # Grid lines

            # No numbers displayed
        except Exception as e:
            print(f"Error rendering tile: {e}")

class GameMap:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.tiles: List[List[Tile]] = []
        self.generate_map()
        
    def generate_map(self):
        # Initialize empty map
        self.tiles = [[None for _ in range(self.width)] for _ in range(self.height)]
        
        # Step 1: Fill all with grass
        for y in range(self.height):
            for x in range(self.width):
                self.tiles[y][x] = Tile(x, y, TileType.GRASS)

        # Step 2: Calculate how many water and mountain tiles are needed
        total_tiles = self.width * self.height
        num_water = int(total_tiles * 0.025)  # 2.5% water (like before)
        num_mountain = int(total_tiles * 0.02)  # 2% mountain (like before)

        # Step 3: Place water patches further from the player's and enemy's stonekeeps
        avoid_centers = [(13, 13), (69, 5)]
        avoid_radius = 8
        self._place_resource_patches(TileType.WATER, num_water, patch_size_range=(4, 12), avoid_center=avoid_centers, avoid_radius=avoid_radius)
        # Step 4: Place mountain patches avoiding both stonekeeps
        avoid_centers = [(13, 13), (69, 5)]
        avoid_radius = 8
        self._place_resource_patches(TileType.MOUNTAIN, num_mountain, patch_size_range=(4, 10), avoid_center=avoid_centers, avoid_radius=avoid_radius)
        # Step 4b: Place small dirt (brown) patches avoiding both stonekeeps
        num_dirt = int(total_tiles * 0.01)  # 1% of tiles
        self._place_resource_patches(TileType.DIRT, num_dirt, patch_size_range=(2, 5), avoid_center=avoid_centers, avoid_radius=avoid_radius)
        # Step 5: Place forest tiles randomly (as before)
        for y in range(self.height):
            for x in range(self.width):
                if self.tiles[y][x].tile_type == TileType.GRASS and random.random() < 0.075:
                    self.tiles[y][x].tile_type = TileType.FOREST

        # Add resources to appropriate tiles
        self.add_resources()

    def _place_resource_patches(self, tile_type, total_count, patch_size_range=(4, 10), avoid_center=None, avoid_radius=0):
        placed = 0
        attempts = 0
        max_attempts = 1000
        while placed < total_count and attempts < max_attempts:
            patch_size = random.randint(*patch_size_range)
            patch_center_x = random.randint(0, self.width - 1)
            patch_center_y = random.randint(0, self.height - 1)
            # If avoid_center and avoid_radius are set, skip if too close
            if avoid_center is not None and avoid_radius > 0:
                centers = avoid_center if isinstance(avoid_center, list) else [avoid_center]
                too_close = False
                for acx, acy in centers:
                    dist = ((patch_center_x - acx) ** 2 + (patch_center_y - acy) ** 2) ** 0.5
                    if dist < avoid_radius:
                        too_close = True
                        break
                if too_close:
                    attempts += 1
                    continue
            patch_tiles = []
            # Use a simple BFS to fill the patch
            queue = [(patch_center_x, patch_center_y)]
            visited = set()
            while queue and len(patch_tiles) < patch_size:
                cx, cy = queue.pop(0)
                if (cx, cy) in visited:
                    continue
                if 0 <= cx < self.width and 0 <= cy < self.height:
                    # If avoid_center and avoid_radius are set, skip if too close
                    if avoid_center is not None and avoid_radius > 0:
                        centers = avoid_center if isinstance(avoid_center, list) else [avoid_center]
                        too_close = False
                        for acx, acy in centers:
                            dist = ((cx - acx) ** 2 + (cy - acy) ** 2) ** 0.5
                            if dist < avoid_radius:
                                too_close = True
                                break
                        if too_close:
                            continue
                    if self.tiles[cy][cx].tile_type == TileType.GRASS:
                        self.tiles[cy][cx].tile_type = tile_type
                        patch_tiles.append((cx, cy))
                        placed += 1
                        if placed >= total_count:
                            break
                        # Add neighbors
                        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                            nx, ny = cx+dx, cy+dy
                            if 0 <= nx < self.width and 0 <= ny < self.height and (nx,ny) not in visited:
                                queue.append((nx, ny))
                visited.add((cx, cy))
            attempts += 1
        
    def add_resources(self):
        # Add wood to forests
        for y in range(self.height):
            for x in range(self.width):
                tile = self.tiles[y][x]
                if tile.tile_type == TileType.FOREST:
                    tile.resource_amount = random.randint(100, 500)
                    
    def get_tile_at(self, x: int, y: int) -> Optional[Tile]:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return None
        
    def get_tile_at_screen_pos(self, screen_x: int, screen_y: int, zoom_level: float = 1.0, camera_x: float = 0, camera_y: float = 0) -> Optional[Tile]:
        try:
            # Convert screen coordinates to tile coordinates
            screen_x = (screen_x - camera_x) / zoom_level
            screen_y = (screen_y - camera_y) / zoom_level
            
            # Convert to tile coordinates
            tile_x = int((screen_x / 32 + screen_y / 16) / 2)
            tile_y = int((screen_y / 16 - screen_x / 32) / 2)
            
            return self.get_tile_at(tile_x, tile_y)
        except Exception as e:
            print(f"Error getting tile at screen pos: {e}")
            return None
        
    def can_build_at(self, x: int, y: int, width: int = 1, height: int = 1) -> bool:
        # Check all tiles covered by the building
        for dy in range(height):
            for dx in range(width):
                tx, ty = x + dx, y + dy
                tile = self.get_tile_at(tx, ty)
                if not tile or tile.tile_type != TileType.GRASS or tile.building:
                    return False
        return True
        
    def render(self, screen: pygame.Surface, zoom_level: float = 1.0, camera_x: float = 0, camera_y: float = 0):
        try:
            # Render tiles with an extra border to always show upper and left edges
            margin = 2  # Number of extra tiles to render outside the map on each side
            for y in range(-margin, self.height):
                for x in range(-margin, self.width):
                    if 0 <= x < self.width and 0 <= y < self.height:
                        self.tiles[y][x].render(screen, zoom_level, camera_x, camera_y)
                    else:
                        # Render an empty tile (e.g., black or a border color)
                        # Optionally, you could skip this to just show the background
                        pass
        except Exception as e:
            print(f"Error rendering map: {e}")
                
    def get_walkable_neighbors(self, x: int, y: int) -> List[Tuple[int, int]]:
        neighbors = []
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        
        for dx, dy in directions:
            new_x, new_y = x + dx, y + dy
            tile = self.get_tile_at(new_x, new_y)
            if tile and tile.tile_type != TileType.WATER and tile.tile_type != TileType.MOUNTAIN:
                neighbors.append((new_x, new_y))
                
        return neighbors 