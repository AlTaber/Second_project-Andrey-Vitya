import pygame
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
        self.pause = False

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

    def clear(self):
        self.board = [[Sandbox.GameObjects.Air()] * self.width for _ in range(self.height)]

    def set_pause(self, true):
        if true:
            self.pause = True
        else:
            self.pause = False

    def get_neighbors_coords(self, cell):
        result = []
        for coords in [(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)]:
            if (0 <= cell[0] + coords[0] < self.height) and (0 <= cell[1] + coords[1] < self.width):
                result.append((cell[0] + coords[0], cell[1] + coords[1]))
        return result

    def get_air_neighbors_coords(self, cell):
        return list(filter(lambda x: self.board[x[0]][x[1]].type == "air", self.get_neighbors_coords(cell)))

    def fire(self, coords):
        element = self.board[coords[0]][coords[1]]
        if element.type == "water":
            self.replace(coords, "vapor")
        elif element.type == "acid":
            self.replace(coords, "acid_vapor")
        elif element.cls in ["ignitable_solid", "ignitable_liquid"]:
            neighbors = [self.board[x[0]][x[1]].type for x in self.get_neighbors_coords(coords)]
            if 'air' in neighbors and "water" not in neighbors and "vapor" not in neighbors and\
                    "salt_water" not in neighbors:
                self.board[coords[0]][coords[1]].burn()
        elif element.type == "salt_water":
            air_neighbors = self.get_air_neighbors_coords(coords)
            if air_neighbors and random.randint(0, 3) == 0:
                self.replace(random.choice(air_neighbors), "vapor")
                self.replace(coords, "salt")
            else:
                self.replace(coords, "vapor")

    def fade(self, coords):
        if self.board[coords[0]][coords[1]].cls in ["ignitable_solid"] and \
           self.board[coords[0]][coords[1]].burning:
            neighbors = [self.board[x[0]][x[1]].type for x in self.get_neighbors_coords(coords)]
            if ("air" not in neighbors and "fire" not in neighbors) or "salt_water" in neighbors or \
                    "water" in neighbors or "vapor" in neighbors:
                self.board[coords[0]][coords[1]].fade()

    def set_fire_on_burning(self, coords):
        if self.board[coords[0]][coords[1]].type == "air" and random.randint(0, 20) == 0:
            self.replace(coords, "fire_4")

    def acid(self, coords):
        if self.board[coords[0]][coords[1]].soluble:
            self.replace(coords, "air")
            return True
        return False

    def salt(self, coords):
        if self.board[coords[0]][coords[1]].type == "water":
            self.replace(coords, "salt_water")

    def tick_board(self):
        if self.pause:
            return
        random_i = list(range(self.width))
        random.shuffle(random_i)
        to_switch = []
        to_fire = []
        to_fire_on_burning = []
        to_fade = []
        to_salt = []
        for i in random_i:
            for j in range(self.height):
                element = self.board[j][i]
                # свойства элемента
                if element.type == "vapor":
                    if random.randint(0, 50) == 0:
                        self.replace((j, i), "water")
                elif element.type == "acid_vapor":
                    if random.randint(0, 35) == 0:
                        self.replace((j, i), "acid")
                elif element.type == "fire":
                    if element.temperature <= 1:
                        self.replace((j, i), "air")
                    else:
                        self.board[j][i].fade()
                    for coords in self.get_neighbors_coords((j, i)):
                        to_fire.append(coords)
                elif element.type in ["acid", "acid_vapor"]:
                    for coords in self.get_neighbors_coords((j, i)):
                        if random.randint(0, 35) == 0:
                            if self.acid(coords):
                                self.replace((j, i), "air")
                elif element.cls == "ignitable_liquid":
                    if element.burning:
                        for coords in self.get_neighbors_coords((j, i)):
                            to_fire.append(coords)
                            to_fire_on_burning.append(coords)
                        if random.randint(0, element.extinct_chance) == 0:
                            self.replace((j, i), "air")
                elif element.cls == "ignitable_solid":
                    if element.burning:
                        to_fade.append((j, i))
                        self.board[j][i].random_burning_color()
                        for coords in self.get_neighbors_coords((j, i)):
                            to_fire.append(coords)
                            to_fire_on_burning.append(coords)
                        if random.randint(0, element.extinct_chance) == 0:
                            self.replace((j, i), "air")
                elif element.type == "salt":
                    neighbors = self.get_neighbors_coords((j, i))
                    if "water" in [self.board[x[0]][x[1]].type for x in neighbors]:
                        for coords in neighbors:
                            to_salt.append(coords)
                        if random.randint(0, 2) == 0:
                            self.replace((j, i), "air")
                # физика элемента
                if element.cls == "falling":
                    if j != self.height - 1:
                        if element.weight > self.board[j + 1][i].weight:
                            to_switch.append(((j, i), (j + 1, i)))
                elif element.cls in ["liquid", "gas", "ignitable_liquid"]:
                    flag = True
                    if j != self.height - 1:
                        if element.weight > self.board[j + 1][i].weight:
                            to_switch.append(((j, i), (j + 1, i)))
                            flag = False
                        else:
                            d_step_r_l = []
                            if i != 0:
                                if element.weight > self.board[j + 1][i - 1].weight:
                                    d_step_r_l.append(-1)
                            if i != self.width - 1:
                                if element.weight > self.board[j + 1][i + 1].weight:
                                    d_step_r_l.append(1)
                            if d_step_r_l:
                                to_switch.append(((j, i), (j + 1, i + random.choice(d_step_r_l))))
                                flag = False
                    if flag:
                        step_r_l = []
                        if i != 0:
                            if self.board[j][i - 1].weight < element.weight:
                                step_r_l.append(-1)
                        if i != self.width - 1:
                            if self.board[j][i + 1].weight < element.weight:
                                step_r_l.append(1)
                        if step_r_l:
                            to_switch.append(((j, i), (j, i + random.choice(step_r_l))))

        for co in to_switch:
            self.switch(co[0], co[1])

        for co in to_fire:
            self.fire(co)

        for co in to_fire_on_burning:
            self.set_fire_on_burning(co)

        for co in to_fade:
            self.fade(co)

        for co in to_salt:
            self.salt(co)

    def generate_material(self, m_type):
        return {"air": Sandbox.GameObjects.Air(), "sand": Sandbox.GameObjects.Sand(),
                "water": Sandbox.GameObjects.Water(), "iron": Sandbox.GameObjects.Iron(),
                "vapor": Sandbox.GameObjects.Vapor(), "fire_4": Sandbox.GameObjects.Fire(4),
                "acid": Sandbox.GameObjects.Acid(), "acid_vapor": Sandbox.GameObjects.AVapor(),
                "dirt": Sandbox.GameObjects.Dirt(), "oil": Sandbox.GameObjects.Oil(),
                "wood": Sandbox.GameObjects.Wood(), "coal": Sandbox.GameObjects.Coal(),
                "fire_5": Sandbox.GameObjects.Fire(5), "salt": Sandbox.GameObjects.Salt(),
                "salt_water": Sandbox.GameObjects.SWater()}[m_type]


class ManageMenu:
    def __init__(self, board: Board, parent):
        self.link_with_board = board
        self.parent = parent
        self.left = board.left * 2 + board.cell_size * board.width
        self.top = board.top
        self.all_sprites = pygame.sprite.Group()
        self.buttons = []

        # Значения по умолчанию

        self.button_width = 5

        # Все кнопки менюшки

        self.buttons.append(ManageMenu.Button(self, (5, 20), (40, 40), "brush_1_icon.png", "B", 1))
        self.buttons.append(ManageMenu.Button(self, (50, 20), (40, 40), "brush_3_icon.png", "B", 3))
        self.buttons.append(ManageMenu.Button(self, (95, 20), (40, 40), "brush_5_icon.png", "B", 5))
        self.buttons.append(ManageMenu.Button(self, (140, 20), (40, 40), "brush_7_icon.png", "B", 7))

        self.buttons.append(ManageMenu.Button(self, (5, 70), (40, 40), "air_icon.png", "M", "air"))
        self.buttons.append(ManageMenu.Button(self, (50, 70), (40, 40), "sand_icon.png", "M", "sand"))
        self.buttons.append(ManageMenu.Button(self, (95, 70), (40, 40), "water_icon.png", "M", "water"))
        self.buttons.append(ManageMenu.Button(self, (140, 70), (40, 40), "iron_icon.png", "M", "iron"))
        self.buttons.append(ManageMenu.Button(self, (5, 115), (40, 40), "fire_icon.png", "M", "fire_5"))
        self.buttons.append(ManageMenu.Button(self, (50, 115), (40, 40), "vapor_icon.png", "M", "vapor"))
        self.buttons.append(ManageMenu.Button(self, (95, 115), (40, 40), "acid_icon.png", "M", "acid"))
        self.buttons.append(ManageMenu.Button(self, (140, 115), (40, 40), "acid_vapor_icon.png", "M", "acid_vapor"))
        self.buttons.append(ManageMenu.Button(self, (5, 160), (40, 40), "dirt_icon.png", "M", "dirt"))
        self.buttons.append(ManageMenu.Button(self, (50, 160), (40, 40), "oil_icon.png", "M", "oil"))
        self.buttons.append(ManageMenu.Button(self, (95, 160), (40, 40), "wood_icon.png", "M", "wood"))
        self.buttons.append(ManageMenu.Button(self, (140, 160), (40, 40), "coal_icon.png", "M", "coal"))
        self.buttons.append(ManageMenu.Button(self, (5, 205), (40, 40), "salt_icon.png", "M", "salt"))
        self.buttons.append(ManageMenu.Button(self, (50, 205), (40, 40), "salt_water_icon.png", "M", "salt_water"))

        self.buttons.append(ManageMenu.Button(self, (5, 620), (40, 40), "clear_icon.png", "C", "clear"))
        self.buttons.append(ManageMenu.Button(self, (50, 620), (40, 40), "pause_icon.png", "C", "pause"))
        self.buttons.append(ManageMenu.Button(self, (95, 620), (40, 40), "rainbow_icon.png", "C", "rainbow_change"))

    def set_button_width(self, width):
        self.button_width = width

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

            self.sprite = pygame.sprite.Sprite()
            self.sprite.image = load_image(icon_name)
            self.sprite.rect = self.sprite.image.get_rect()
            self.sprite.rect.topleft = self.parent.left + coords[0] + self.parent.button_width, \
                                       self.parent.top + coords[1] + self.parent.button_width
            self.parent.all_sprites.add(self.sprite)

        def activate(self):
            if self.button_type == 'B':
                for btn in self.parent.buttons:
                    if btn.button_type == "B":
                        btn.selected = False
                self.selected = True
                self.parent.set_brush(self.action)
            elif self.button_type == 'M':
                for btn in self.parent.buttons:
                    if btn.button_type == "M":
                        btn.selected = False
                self.selected = True
                self.parent.set_material(self.action)
            elif self.button_type == 'C':
                self.parent.custom_action(self.action)

    def render(self, surf):
        for button in self.buttons:
            rnbwc = self.parent.rainbow_color
            button_color_1 = rnbwc[0] + 20, rnbwc[1] + 20, rnbwc[2] + 20
            button_color_2 = rnbwc[0] + 70, rnbwc[1] + 70, rnbwc[2] + 70
            if button.selected:
                button_color_1 = (150, 150, 150)
                button_color_2 = (220, 220, 220)
            elif button.mouse_on:
                button_color_1 = rnbwc[0] + 40, rnbwc[1] + 40, rnbwc[2] + 40
                button_color_2 = rnbwc[0] + 100, rnbwc[1] + 100, rnbwc[2] + 100
            pygame.draw.rect(surf, color=button_color_1, rect=(
                self.left + button.coords[0],
                self.top + button.coords[1],
                button.size[0],
                button.size[1]))
            pygame.draw.rect(surf, color=button_color_2, rect=(
                self.left + button.coords[0] + self.button_width,
                self.top + button.coords[1] + self.button_width,
                button.size[0] - self.button_width * 2,
                button.size[1] - self.button_width * 2))
        self.all_sprites.draw(surface=surf)

    def set_brush(self, size):
        self.link_with_board.set_brush(size)

    def set_material(self, material_id):
        self.link_with_board.set_material(material_id)

    def custom_action(self, action_id):
        if action_id == "clear":
            self.link_with_board.clear()
        elif action_id == "pause":
            self.link_with_board.set_pause(not self.link_with_board.pause)
        elif action_id == "rainbow_change":
            self.parent.rainbow_change()

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

    def get_motion(self, mouse_pos):
        button = self.get_button(mouse_pos)
        for btn in self.buttons:
            btn.mouse_on = False
        if button is not None:
            button.mouse_on = True


class Sandbox:
    def __init__(self):
        self.board = Board(50, 42)
        pygame.init()
        self.size = self.width, self.height = 1000, 692
        self.screen = pygame.display.set_mode(self.size, pygame.DOUBLEBUF)
        self.board.set_view(2, 2, 16)
        self.rainbow_color = pygame.Color(0)
        self.rainbow_turn = True
        self.menu = ManageMenu(self.board, self)
        self.menu.set_button_width(3)

    def run_game(self):
        screen = self.screen
        clock = pygame.time.Clock()
        max_fps = 30
        running = True
        hold = False
        self.board.set_material("air")
        self.board.set_brush(1)
        fps_font = pygame.font.Font(None, 32)
        fps_pos = (self.board.left * 2 + self.board.width * self.board.cell_size, 1)

        hue = 0

        while running:
            screen.fill(self.rainbow_color)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    hold = True
                    self.board.get_click(event.pos)
                    self.menu.get_click(event.pos)
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    hold = False
                if event.type == pygame.MOUSEMOTION:
                    self.menu.get_motion(event.pos)
            if hold:
                self.board.get_click(pygame.mouse.get_pos())
            self.board.render(screen)
            self.menu.render(screen)
            self.board.tick_board()
            clock.tick(max_fps)
            fps_now = str(clock.get_fps())[:4]
            text = fps_font.render(fps_now + " FPS", True, (220, 220, 220))

            if self.rainbow_turn:
                self.rainbow_color.hsla = (hue, 50, 25, 50)
                hue = hue + 1 if hue < 360 else 0

            screen.blit(text, fps_pos)
            pygame.display.flip()
        pygame.quit()

    def rainbow_change(self):
        self.rainbow_turn = not self.rainbow_turn
        if self.rainbow_turn:
            self.rainbow_color = pygame.Color(0)
        else:
            self.rainbow_color = (80, 80, 80)

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

        class IgnitableL(Liquid):
            def __init__(self):
                super().__init__()
                self.cls = "ignitable_liquid"
                self.durability = 1
                self.soluble = False
                self.burning = False
                self.extinct_chance = 0

            def burn(self):
                self.burning = True

            def fade(self):
                self.burning = False

        class IgnitableS(Solid):
            def __init__(self):
                super().__init__()
                self.cls = "ignitable_solid"
                self.durability = 1
                self.soluble = True
                self.burning = False
                self.extinct_chance = 0

            def burn(self):
                self.burning = True

            def fade(self):
                self.burning = False

            def random_burning_color(self):
                self.color = approximate_color(217, 119, 0, 2)

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
                self.soluble = True

        class Vapor(Gas):
            def __init__(self):
                super().__init__()
                self.type = "vapor"
                self.color = approximate_color(222, 222, 222, 3)
                self.weight = -11

        class Fire(Special):
            def __init__(self, temperature):
                super().__init__()
                self.type = "fire"
                self.color = [222, 89, 22]
                self.weight = -100
                self.temperature = temperature
                self.soluble = False

            def fade(self):
                self.temperature -= 1
                self.color = {4: [194, 56, 6], 3: [161, 41, 8], 2: [135, 31, 12], 1: [102, 9, 9]}[self.temperature]

        class Acid(Liquid):
            def __init__(self):
                super().__init__()
                self.type = "acid"
                self.color = approximate_color(130, 227, 27, 10)
                self.weight = 7
                self.durability = 10

        class AVapor(Gas):
            def __init__(self):
                super().__init__()
                self.type = "acid_vapor"
                self.color = approximate_color(145, 235, 154, 3)
                self.weight = -11
                self.durability = 10

        class Dirt(Falling):
            def __init__(self):
                super().__init__()
                self.type = "dirt"
                self.color = approximate_color(105, 39, 10, 5)
                self.weight = 10
                self.durability = 1
                self.soluble = True

        class Oil(IgnitableL):
            def __init__(self):
                super().__init__()
                self.type = "oil"
                self.color = approximate_color(25, 22, 31, 1)
                self.weight = 6
                self.durability = 4
                self.extinct_chance = 20

            def burn(self):
                super().burn()
                self.color = [252, 228, 167]

            def fade(self):
                super().fade()
                self.color = approximate_color(25, 22, 31, 2)

        class Wood(IgnitableS):
            def __init__(self):
                super().__init__()
                self.type = "wood"
                self.color = approximate_color(101, 67, 33, 2)
                self.weight = 20
                self.durability = 4
                self.extinct_chance = 110

            def random_burning_color(self):
                self.color = approximate_color(247, 135, 7, 10)

            def fade(self):
                super().fade()
                self.color = approximate_color(101, 67, 33, 2)

        class Coal(IgnitableS):
            def __init__(self):
                super().__init__()
                self.type = "coal"
                self.color = approximate_color(15, 14, 23, 2)
                self.weight = 20
                self.durability = 4
                self.extinct_chance = 200

            def fade(self):
                super().fade()
                self.color = approximate_color(15, 14, 23, 2)

            def random_burning_color(self):
                self.color = approximate_color(247, 99, 7, 10)

        class Salt(Falling):
            def __init__(self):
                super().__init__()
                self.type = "salt"
                self.color = approximate_color(237, 237, 237, 15)
                self.weight = 10
                self.durability = 1
                self.soluble = True

        class SWater(Liquid):
            def __init__(self):
                super().__init__()
                self.type = "salt_water"
                self.color = approximate_color(84, 92, 176, 10)
                self.weight = 8
                self.durability = 10


sandbox = Sandbox()
sandbox.run_game()
