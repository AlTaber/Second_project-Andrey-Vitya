import pygame
import copy
import random
import os
import sys


def load_image(name, colorkey=None):
    fullname = os.path.join('Images', name)
    # если файл не существует, то выходим
    if not os.path.isfile(fullname):
        print(f"Файл с изображением '{fullname}' не найден")
        sys.exit()
    image = pygame.image.load(fullname)
    if colorkey is not None:
        image = image.convert()
        if colorkey == -1:
            colorkey = image.get_at((0, 0))
        image.set_colorkey(colorkey)
    else:
        image = image.convert_alpha()
    return image


def approximate_color(r, g, b, max_color_modifier):
    color_modifier = random.randint(max_color_modifier * -1, max_color_modifier + 1)
    r = 255 if r + color_modifier > 255 else (0 if r + color_modifier < 0 else r + color_modifier)
    g = 255 if g + color_modifier > 255 else (0 if g + color_modifier < 0 else g + color_modifier)
    b = 255 if b + color_modifier > 255 else (0 if b + color_modifier < 0 else b + color_modifier)
    return [r, g, b]


class Board:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.board = [[Sandbox.GameObjects.Air()] * width for _ in range(height)]
        # значения по умолчанию
        self.left = 10
        self.top = 10
        self.cell_size = 30
        self.current_material = "air"
        self.brush = 1

    def set_view(self, left, top, cell_size):
        self.left = left
        self.top = top
        self.cell_size = cell_size

    def set_material(self, material):
        self.current_material = material

    def set_brush(self, brush):
        self.brush = brush if brush % 2 == 1 else brush - 1

    def render(self, surf):
        for i in range(self.width):
            for j in range(self.height):
                pygame.draw.rect(surf, color=self.board[j][i].color, rect=(
                    self.left + i * self.cell_size,
                    self.top + j * self.cell_size,
                    self.cell_size,
                    self.cell_size))

    def get_cell(self, mouse_pos):
        if not self.left <= mouse_pos[0] <= self.left + self.width * self.cell_size - 1 or \
           not self.top <= mouse_pos[1] <= self.top + self.height * self.cell_size - 1:
            return None
        x, y = mouse_pos[0] - self.left, mouse_pos[1] - self.top
        return x // self.cell_size, y // self.cell_size

    def on_click(self, cell_pos):
        if cell_pos is None:
            return
        x, y = cell_pos
        if self.brush == 1:
            self.board[y][x] = self.generate_material(self.current_material)
        else:
            for i in range(-1 * (self.brush // 2), self.brush // 2 + 1):
                for j in range(-1 * (self.brush // 2), self.brush // 2 + 1):
                    try:
                        if y + i >= 0 and x + j >= 0:
                            self.board[y + i][x + j] = self.generate_material(self.current_material)
                    except Exception:
                        pass

    def get_click(self, mouse_pos):
        cell = self.get_cell(mouse_pos)
        self.on_click(cell)

    def switch(self, cell1, cell2):
        cl1 = self.board[cell1[0]][cell1[1]]
        self.board[cell1[0]][cell1[1]] = self.board[cell2[0]][cell2[1]]
        self.board[cell2[0]][cell2[1]] = cl1

    def replace(self, cell, material_id):
        self.board[cell[0]][cell[1]] = self.generate_material(material_id)

    def get_neighbors_coords(self, cell):
        result = []
        for coords in [(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)]:
            if (0 <= cell[0] + coords[0] < self.height) and (0 <= cell[1] + coords[1] < self.width):
                result.append((cell[0] + coords[0], cell[1] + coords[1]))
        return result

    def fire(self, coords):
        element = self.board[coords[0]][coords[1]]
        if element.type == "water":
            self.replace(coords, "vapor")

    def tick_board(self):
        temp = copy.deepcopy(self.board)
        random_i = list(range(self.width))
        random.shuffle(random_i)
        to_switch = []
        for i in random_i:
            for j in range(self.height):
                element = temp[j][i]
                # свойства элемента
                if element.type == "vapor":
                    if random.randint(0, 50) == 0:
                        self.replace((j, i), "water")
                if element.type == "fire":
                    if element.temperature <= 1:
                        self.replace((j, i), "air")
                    else:
                        self.board[j][i].fade()
                    for coords in self.get_neighbors_coords((j, i)):
                        self.fire(coords)
                # физика элемента
                if element.cls == "falling":
                    if j != self.height - 1:
                        if element.weight > temp[j + 1][i].weight:
                            to_switch.append(((j, i), (j + 1, i)))
                elif element.cls in ["liquid", "gas"]:
                    if j != self.height - 1:
                        if element.weight > temp[j + 1][i].weight:
                            to_switch.append(((j, i), (j + 1, i)))
                        else:
                            d_step_r_l = []
                            if i != 0:
                                if element.weight > temp[j + 1][i - 1].weight:
                                    d_step_r_l.append(-1)
                            if i != self.width - 1:
                                if element.weight > temp[j + 1][i + 1].weight:
                                    d_step_r_l.append(1)
                            if d_step_r_l:
                                to_switch.append(((j, i), (j + 1, i + random.choice(d_step_r_l))))
                            else:
                                step_r_l = []
                                if i != 0:
                                    if temp[j][i - 1].weight < element.weight:
                                        step_r_l.append(-1)
                                if i != self.width - 1:
                                    if temp[j][i + 1].weight < element.weight:
                                        step_r_l.append(1)
                                if step_r_l:
                                    to_switch.append(((j, i), (j, i + random.choice(step_r_l))))
        for co in to_switch:
            self.switch(co[0], co[1])

    def generate_material(self, m_type):
        return {"air": Sandbox.GameObjects.Air(), "sand": Sandbox.GameObjects.Sand(),
                "water": Sandbox.GameObjects.Water(), "iron": Sandbox.GameObjects.Iron(),
                "vapor": Sandbox.GameObjects.Vapor(), "fire": Sandbox.GameObjects.Fire()}[m_type]


class ManageMenu:
    def __init__(self, board: Board):
        self.link_with_board = board
        self.left = board.left * 2 + board.cell_size * board.width
        self.top = board.top
        self.buttons = []

    class Button:
        def __init__(self, parent, coords, size, icon_name, button_type, item_id):
            self.coords = coords
            self.icon_name = icon_name
            self.button_type = button_type
            self.action = item_id
            self.parent = parent
            self.size = size
            self.selected = False
            self.mouse_on = False

        def activate(self):
            if self.button_type == 'B':
                self.parent.set_brush(self.action)
            elif self.button_type == 'M':
                self.parent.set_material(self.action)
            elif self.button_type == 'C':
                self.parent.custom_action(self.action)

    def render(self, surf):
        for button in self.buttons:
            button_color = None
            if button.selected:
                button_color = (16, 73, 169)
            elif button.mouse_on:
                button_color = (120, 120, 120)
            else:
                button_color = (89, 89, 89)
            pygame.draw.rect(surf, color=button_color, rect=(
                self.left + button.coords[0],
                self.top + button.coords[1],
                button.size[0],
                button.size[1]))

    def set_brush(self, size):
        self.link_with_board.set_brush(size)

    def set_material(self, material_id):
        self.link_with_board.set_material(material_id)

    def custom_action(self, action_id):
        pass

    def get_button(self, mouse_pos):
        for button in self.buttons:
            if button.coords[0] + self.left <= mouse_pos[0] <= button.coords[0] + button.size[0] + self.left and \
               button.coords[1] + self.top <= mouse_pos[1] <= button.coords[1] + button.size[1] + self.top:
                return button
        return None

    def on_click(self, button):
        if button is None:
            return
        button.activate()

    def get_click(self, mouse_pos):
        button = self.get_button(mouse_pos)
        self.on_click(button)


class Sandbox:
    def __init__(self):
        self.board = Board(50, 43)
        self.size = self.width, self.height = 1000, 692
        self.board.set_view(2, 2, 16)

    def run_game(self):
        screen = pygame.display.set_mode(self.size)
        clock = pygame.time.Clock()
        max_fps = 30
        running = True
        hold = False
        pygame.init()
        self.board.set_material("iron")
        self.board.set_brush(3)
        fps_font = pygame.font.Font(None, 32)
        fps_pos = (self.board.left * 2 + self.board.width * self.board.cell_size, 1)
        while running:
            screen.fill((70, 70, 70))
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    hold = True
                    self.board.get_click(event.pos)
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    hold = False
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                    self.board.set_material("water")
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 2:
                    self.board.set_material("fire")
            if hold:
                self.board.get_click(pygame.mouse.get_pos())
            self.board.render(screen)
            self.board.tick_board()
            clock.tick(max_fps)
            fps_now = str(clock.get_fps())[:4]
            text = fps_font.render(fps_now + " FPS", True, (80, 255, 255))
            screen.blit(text, fps_pos)
            pygame.display.flip()
        pygame.quit()

    class GameObjects:
        class Object:
            def __init__(self):
                self.cls = None
                self.type = None
                self.color = None
                self.weight = None
                self.durability = None
                self.soluble = None

        # Типы веществ
        class Gas(Object):
            def __init__(self):
                super().__init__()
                self.cls = "gas"
                self.soluble = False
                self.durability = 1

        class Falling(Object):
            def __init__(self):
                super().__init__()
                self.durability = 1
                self.cls = "falling"

        class Liquid(Object):
            def __init__(self):
                super().__init__()
                self.cls = "liquid"
                self.durability = 1
                self.soluble = False

        class Solid(Object):
            def __init__(self):
                super().__init__()
                self.cls = "solid"
                self.durability = 1

        class Special(Object):
            def __init__(self):
                super().__init__()
                self.cls = "special"

        # Основные вещества
        class Air(Gas):
            def __init__(self):
                super().__init__()
                self.type = "air"
                self.color = [0, 0, 0]
                self.weight = -10

        class Sand(Falling):
            def __init__(self):
                super().__init__()
                self.type = "sand"
                self.color = approximate_color(200, 200, 100, 10)
                self.weight = 10
                self.durability = 1
                self.soluble = False

        class Water(Liquid):
            def __init__(self):
                super().__init__()
                self.type = "water"
                self.color = approximate_color(30, 30, 200, 10)
                self.weight = 7
                self.durability = 10

        class Iron(Solid):
            def __init__(self):
                super().__init__()
                self.type = "iron"
                self.color = approximate_color(173, 173, 173, 2)
                self.weight = 20
                self.durability = 7

        class Vapor(Gas):
            def __init__(self):
                super().__init__()
                self.type = "vapor"
                self.color = approximate_color(222, 222, 222, 3)
                self.weight = -11

        class Fire(Special):
            def __init__(self):
                super().__init__()
                self.type = "fire"
                self.color = [222, 89, 22]
                self.weight = -100
                self.temperature = 5

            def fade(self):
                self.temperature -= 1
                self.color = {4: [194, 56, 6], 3: [161, 41, 8], 2: [135, 31, 12], 1: [102, 9, 9]}[self.temperature]

sandbox = Sandbox()
sandbox.run_game()