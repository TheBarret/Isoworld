import pygame
import math
import json
from pathlib import Path
from enum import IntEnum
from typing import List, Dict, Tuple, Optional

class TileType(IntEnum):
    WATER = 0
    SAND = 1
    DIRT = 2
    PATH = 3
    GRASS = 4
    ROCKS = 5
    ICE = 6

class Config:
    FPS = 30
    CAMERA_SPEED = 10
    CAMERA_LERP = 0.5
    SCREEN_WIDTH = 800
    SCREEN_HEIGHT = 800
    TILE_WIDTH = 64
    TILE_HEIGHT = 32
    
    BG_COLOR = (135, 206, 235)
    SHADOWS = 75
    
    # Color mapping
    TILE_COLORS: Dict[TileType, Tuple[int, int, int]] = {
        TileType.WATER: (90, 90, 255),
        TileType.SAND: (202, 182, 158),
        TileType.DIRT: (161, 110, 29),
        TileType.PATH: (153, 153, 153),
        TileType.GRASS: (147, 196, 125),
        TileType.ROCKS: (91, 91, 91),
        TileType.ICE: (111, 168, 220),
    }
    
    # Height mapping
    TILE_HEIGHTS: Dict[TileType, int] = {
        TileType.WATER: 0,
        TileType.SAND: 1,
        TileType.DIRT: 1,
        TileType.PATH: 1,
        TileType.GRASS: 1,
        TileType.ROCKS: 2,
        TileType.ICE: 1,
    }
    @staticmethod
    def load_world(file_path: Path) -> List[List[int]]:
        with open(file_path, 'r') as f:
            data = json.load(f)
            return data['layout']

class Camera:
    def __init__(self, x: float = 10, y: float = 10, lerp: float = 0.1):
        self.x = x
        self.y = y
        self.target_x = x
        self.target_y = y
        self.lerp_speed = lerp
    
    def move(self, dx: float, dy: float) -> None:
        self.target_x += dx
        self.target_y += dy
        
    def update(self) -> None:
        # Smooth camera movement using linear interpolation
        self.x += (self.target_x - self.x) * self.lerp_speed
        self.y += (self.target_y - self.y) * self.lerp_speed

class Tile:
    def __init__(self, x: int, y: int, tile_type: TileType, height: Optional[int] = None):
        self.x = x
        self.y = y
        self.tile_type = tile_type
        self.height = height if height is not None else Config.TILE_HEIGHTS[tile_type]
        self.color = (0,0,0)
        self.base = Config.TILE_COLORS[tile_type]
        self.selected = False
        self.hover = False
        self.selected_color = tuple(min(255, c + 30) for c in self.base)
        self.hover_color = tuple(min(255, c + 15) for c in self.base)
        
    def cart_to_iso(self) -> Tuple[float, float]:
        iso_x = (self.x - self.y) * (Config.TILE_WIDTH // 2)
        iso_y = (self.x + self.y) * (Config.TILE_HEIGHT // 2)
        return iso_x, iso_y
        
    def contains_point(self, screen_x: float, screen_y: float, camera_x: float, camera_y: float) -> bool:
        # Get tile's screen position
        iso_x, iso_y = self.cart_to_iso()
        tile_screen_x = iso_x + camera_x
        tile_screen_y = iso_y + camera_y - self.height * Config.TILE_HEIGHT
        
        # Define the four corners of the diamond
        corners = [
            (tile_screen_x, tile_screen_y),  # Top
            (tile_screen_x + Config.TILE_WIDTH // 2, tile_screen_y + Config.TILE_HEIGHT // 2),  # Right
            (tile_screen_x, tile_screen_y + Config.TILE_HEIGHT),  # Bottom
            (tile_screen_x - Config.TILE_WIDTH // 2, tile_screen_y + Config.TILE_HEIGHT // 2)   # Left
        ]
        
        # Convert screen coordinates to local tile coordinates
        local_x = screen_x - tile_screen_x
        local_y = screen_y - tile_screen_y
        
        # Calculate half-width and half-height of the diamond
        half_w = Config.TILE_WIDTH // 2
        half_h = Config.TILE_HEIGHT // 2
        
        # Check if point is inside diamond using normalized coordinates
        if half_w == 0 or half_h == 0:
            return False
            
        # Transform point to diamond space
        dx = abs(local_x / half_w)
        dy = abs(local_y / half_h)
        
        return dx + dy <= 1

    def draw(self, screen: pygame.Surface, offset_x: float, offset_y: float) -> None:
        iso_x, iso_y = self.cart_to_iso()
        iso_x += offset_x
        iso_y += offset_y - self.height * Config.TILE_HEIGHT

        # Define colors with optional highlight for selected or hovered tiles
        self.color = self.selected_color if self.selected else self.hover_color if self.hover else self.base
        left_color = tuple(max(0, c - Config.SHADOWS) for c in self.color)
        right_color = tuple(min(255, c + Config.SHADOWS) for c in self.color)

        # Calculate tile vertices
        top = [
            (iso_x, iso_y),
            (iso_x + Config.TILE_WIDTH // 2, iso_y + Config.TILE_HEIGHT // 2),
            (iso_x, iso_y + Config.TILE_HEIGHT),
            (iso_x - Config.TILE_WIDTH // 2, iso_y + Config.TILE_HEIGHT // 2)
        ]

        if self.height > 0:
            # Left face
            left_face = [
                top[2], top[3],
                (top[3][0], top[3][1] + self.height * Config.TILE_HEIGHT),
                (top[2][0], top[2][1] + self.height * Config.TILE_HEIGHT)
            ]
            pygame.draw.polygon(screen, left_color, left_face)

            # Right face
            right_face = [
                top[1], top[2],
                (top[2][0], top[2][1] + self.height * Config.TILE_HEIGHT),
                (top[1][0], top[1][1] + self.height * Config.TILE_HEIGHT)
            ]
            pygame.draw.polygon(screen, right_color, right_face)

        # Draw top face
        pygame.draw.polygon(screen, self.color, top)
        
        # Draw outline if selected or hovered
        if self.selected:
            pygame.draw.lines(screen, (255, 0, 0), True, top, 2)
        elif self.hover:
            pygame.draw.lines(screen, (200, 200, 200), True, top, 1)

class Map:
    def __init__(self, map_data: List[List[int]]):
        self.map_data = map_data
        self.tiles = self._generate_tiles()
        self.camera = Camera(
            x=Config.SCREEN_WIDTH // 2,
            y=Config.SCREEN_HEIGHT // 4,
            lerp=Config.CAMERA_LERP
        )
        self.selected_tile = None
        self.hovered_tile = None
        self.sorted_tiles = sorted(self.tiles, key=lambda t: (t.x + t.y, t.x - t.y))

    def _is_visible(self, tile: Tile, cam_x: float, cam_y: float, screen_width: int, screen_height: int) -> bool:
        iso_x, iso_y = tile.cart_to_iso()
        screen_x = iso_x + cam_x
        screen_y = iso_y + cam_y - tile.height * Config.TILE_HEIGHT
        return (-Config.TILE_WIDTH < screen_x < screen_width and
                -Config.TILE_HEIGHT < screen_y < screen_height)

    def _generate_tiles(self) -> List[Tile]:
        return [
            Tile(x, y, TileType(tile_type))
            for y, row in enumerate(self.map_data)
            for x, tile_type in enumerate(row)
        ]

    def draw(self, screen: pygame.Surface) -> None:
        cam_x, cam_y = self.camera.x, self.camera.y
        screen_width, screen_height = Config.SCREEN_WIDTH, Config.SCREEN_HEIGHT

        visible_tiles = [tile for tile in self.sorted_tiles if self._is_visible(tile, cam_x, cam_y, screen_width, screen_height)]
        self._update_hover_state(*pygame.mouse.get_pos())
        for tile in visible_tiles:
            tile.draw(screen, cam_x, cam_y)
    
    def move_camera(self, dx: float, dy: float) -> None:
        iso_dx = (dx - dy) * Config.CAMERA_SPEED * 0.5
        iso_dy = (dx + dy) * Config.CAMERA_SPEED * 0.25
        self.camera.move(iso_dx, iso_dy)
        
    def update(self) -> None:
        self.camera.update()

    def _update_hover_state(self, screen_x: int, screen_y: int) -> None:
        # Reset all hover states
        if self.hovered_tile:
            self.hovered_tile.hover = False
            self.hovered_tile = None
            
        for tile in reversed(self.sorted_tiles):     
            if tile.contains_point(screen_x, screen_y, self.camera.x, self.camera.y):
                tile.hover = True
                self.hovered_tile = tile
                break
                
    def handle_click(self, screen_x: int, screen_y: int) -> None:
        # Deselect previously selected tile
        if self.selected_tile:
            self.selected_tile.selected = False
            self.selected_tile = None

        # Check tiles in reverse draw order (top to bottom) for more intuitive selection
        sorted_tiles = sorted(
            self.tiles,
            key=lambda t: (t.x + t.y, t.x - t.y),
            reverse=True
        )

        for tile in sorted_tiles:
            if tile.contains_point(screen_x, screen_y, self.camera.x, self.camera.y):
                tile.selected = True
                self.selected_tile = tile
                break


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((Config.SCREEN_WIDTH, Config.SCREEN_HEIGHT))
        pygame.display.set_caption("Isometric World")
        self.clock = pygame.time.Clock()
        self.running = True
        self.map = Map(Config.load_world('world.json'))
        self.font = pygame.font.Font(None, 36)

    def handle_input(self) -> None:
        keys = pygame.key.get_pressed()
        dx = dy = 0
        
        if keys[pygame.K_w]: dy += 1
        if keys[pygame.K_s]: dy -= 1
        if keys[pygame.K_a]: dx += 1
        if keys[pygame.K_d]: dx -= 1
        if keys[pygame.K_ESCAPE]: self.running = False
        
        if dx != 0 or dy != 0:
            self.map.move_camera(dx, dy)

    def run(self) -> None:
        while self.running:
            self._handle_events()
            self.handle_input()
            self.map.update()
            self._update_screen()
            self.clock.tick(Config.FPS)
        pygame.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    self.map.handle_click(*pygame.mouse.get_pos())

    def _update_screen(self) -> None:
        self.screen.fill(Config.BG_COLOR)
        self.map.draw(self.screen)
        
        # Draw FPS counter
        fps_text = self.font.render(f"FPS: {int(self.clock.get_fps())}", True, (255, 255, 255))
        self.screen.blit(fps_text, (10, 10))
        
        pygame.display.flip()

if __name__ == "__main__":
    game = Game()
    game.run()