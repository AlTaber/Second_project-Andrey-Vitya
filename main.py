import pygame
import random
import os
import sys
import ctypes

myappid = 'mycompany.myproduct.subproduct.version'
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)


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


def gradient_color(c1, c2, p):
    p = 0 if p < 0 else (100 if p > 100 else p)
    return ((c1[0] * p + c2[0] * (100 - p)) // 100, (c1[1] * p + c2[1] * (100 - p)) // 100,
            (c1[2] * p + c2[2] * (100 - p)) // 100)


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
        self.physics = True
        self.features = True

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

    def eq_replace(self, coords1, coords2):
        self.board[coords2[0]][coords2[1]] = self.board[coords1[0]][coords1[1]]

    def clear(self):
        self.board = [[Sandbox.GameObjects.Air()] * self.width for _ in range(self.height)]

    def set_pause(self):
        self.pause = not self.pause

    def toggle_obj_physics(self):
        self.physics = not self.physics

    def toggle_obj_features(self):
        self.features = not self.features

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
        if element.freezed:
            self.board[coords[0]][coords[1]].unfreeze()
            return
        if element.type == "water":
            self.replace(coords, "vapor")
        elif element.type == "acid":
            self.replace(coords, "acid_vapor")
        elif element.cls in ["ignitable_solid", "ignitable_liquid", "ignitable_falling"]:
            neighbors = [self.board[x[0]][x[1]].type for x in self.get_neighbors_coords(coords)]
            if 'air' in neighbors and "water" not in neighbors and "vapor" not in neighbors and \
                    "salt_water" not in neighbors and "liquid_nitrogen" not in neighbors:
                self.board[coords[0]][coords[1]].burn()
        elif element.type == "salt_water":
            air_neighbors = self.get_air_neighbors_coords(coords)
            if air_neighbors and random.randint(0, 3) == 0:
                self.replace(random.choice(air_neighbors), "vapor")
                self.replace(coords, "salt")
            else:
                self.replace(coords, "vapor")
        elif element.type in ["ice", "snow"]:
            self.replace(coords, "water")
        elif element.type == "gunpowder":
            self.explode(coords)
        elif element.type == "methane":
            self.replace(coords, "fire_5")
        elif element.type == "wick":
            self.board[coords[0]][coords[1]].activate()
        elif element.type == "wax":
            self.replace(coords, "liquid_wax")

    def strong_fire(self, coords):
        element = self.board[coords[0]][coords[1]]
        if element.type == 'stone' and random.randint(0, 45) == 0:
            self.replace(coords, 'lava')
        else:
            self.fire(coords)

    def fade(self, coords):
        if self.board[coords[0]][coords[1]].cls in ["ignitable_solid", "ignitable_falling"] and \
                self.board[coords[0]][coords[1]].burning:
            neighbors = [self.board[x[0]][x[1]].type for x in self.get_neighbors_coords(coords)]
            if ("air" not in neighbors and "fire" not in neighbors) or "salt_water" in neighbors or \
                    "water" in neighbors or "vapor" in neighbors or "liquid_nitrogen" in neighbors:
                self.board[coords[0]][coords[1]].fade()

    def set_fire_on_burning(self, coords, chance):
        if self.board[coords[0]][coords[1]].type == "air" and random.randint(0, chance) == 0:
            self.replace(coords, "fire_4")

    def acid(self, coords):
        if self.board[coords[0]][coords[1]].soluble:
            self.replace(coords, "air")
            return True
        return False

    def salt(self, coords):
        if self.board[coords[0]][coords[1]].type == "water":
            self.replace(coords, "salt_water")

    def ice(self, coords):
        if self.board[coords[0]][coords[1]].type == "water":
            if random.randint(0, 50) == 0:
                self.replace(coords, "ice")
        elif self.board[coords[0]][coords[1]].type == "vapor":
            if random.randint(0, 15) == 0:
                self.replace(coords, "snow")

    def freeze(self, coords):
        element = self.board[coords[0]][coords[1]]
        if element.freezed:
            return
        if element.cls in ["ignitable_solid", "ignitable_falling", "ignitable_liquid"]:
            if element.burning:
                element.fade()
        elif element.type in ["water", "salt_water"]:
            self.replace(coords, "ice")
        elif element.type in ["fire"]:
            self.replace(coords, "air")
        elif element.type == "liquid_wax":
            self.replace(coords, "wax")
        elif element.type == "lava":
            self.replace(coords, "stone")
        if element.can_be_freezed:
            self.board[coords[0]][coords[1]].freeze()

    def explode(self, coords):
        if self.board[coords[0]][coords[1]].type == "gunpowder":
            self.replace(coords, "explosion_wave_gp")

    def explosion_wave(self, coords):
        wave = self.board[coords[0]][coords[1]]
        if wave.life_tick >= 1:
            for co in self.get_neighbors_coords(coords):
                element2 = self.board[co[0]][co[1]]
                if element2.durability <= wave.power:
                    self.board[co[0]][co[1]] = Sandbox.GameObjects.ExplosionWave(wave.power - 1, wave.range - 1)

    def tick_board(self):
        if self.pause:
            return
        random_i = list(range(self.width))
        random.shuffle(random_i)
        to_lava = []
        to_switch = []
        to_fire = []
        to_strong_fire = []
        to_fire_on_burning = []
        to_fade = []
        to_salt = []
        to_ice = []
        to_expwave = []
        to_freeze = []
        for i in random_i:
            for j in range(self.height):
                element = self.board[j][i]
                if element.freezed:
                    neighbors = self.get_neighbors_coords((j, i))
                    if "water" in [self.board[x[0]][x[1]].type for x in neighbors]:
                        for coords in neighbors:
                            to_ice.append(coords)
                    continue
                # свойства элемента
                if self.features:
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
                    elif element.type == "strong_fire":
                        if element.temperature <= 1:
                            self.replace((j, i), "air")
                        else:
                            self.board[j][i].fade()
                        for coords in self.get_neighbors_coords((j, i)):
                            to_strong_fire.append(coords)
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
                    elif element.cls in ["ignitable_solid", "ignitable_falling"]:
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
                    elif element.type == "ice":
                        neighbors = self.get_neighbors_coords((j, i))
                        if "water" in [self.board[x[0]][x[1]].type for x in neighbors]:
                            for coords in neighbors:
                                to_ice.append(coords)
                    elif element.type == "explosion_wave":
                        if element.life_tick <= 0 or element.range <= 0:
                            self.replace((j, i), "air")
                        else:
                            self.board[j][i].fade()
                            to_expwave.append((j, i))
                            for coords in self.get_neighbors_coords((j, i)):
                                to_fire.append(coords)
                    elif element.type == "wick":
                        if element.activated:
                            for coords in self.get_neighbors_coords((j, i)):
                                to_fire.append(coords)
                            self.replace((j, i), "air")
                    elif element.type == "liquid_nitrogen":
                        for coords in self.get_neighbors_coords((j, i)):
                            to_freeze.append(coords)
                        if random.randint(0, 110) == 0:
                            self.replace((j, i), "nitrogen")
                    elif element.type == "nitrogen":
                        if random.randint(0, 10) == 0:
                            self.replace((j, i), "air")
                    elif element.type == "liquid_wax":
                        if random.randint(0, 50) == 0 and ((j + 1, i) not in self.get_neighbors_coords((j, i)) or
                                                           self.board[j + 1][i].weight >= element.weight):
                            self.replace((j, i), "wax")
                    elif element.type == "lava":
                        neighbors = self.get_neighbors_coords((j, i))
                        if any([self.board[x[0]][x[1]].type != 'lava' for x in neighbors]):
                            for coords in neighbors:
                                to_strong_fire.append(coords)
                                to_lava.append(coords)

                # физика элемента
                if self.physics:
                    if element.cls in ["falling", "ignitable_falling"]:
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

        # Преимущества происходящих событий во время одного тика

        for co in to_switch:
            self.switch(co[0], co[1])

        for co in to_fire:
            self.fire(co)

        for co in to_strong_fire:
            self.strong_fire(co)

        for co in to_lava:
            self.set_fire_on_burning(co, 120)

        for co in to_expwave:
            self.explosion_wave(co)

        for co in to_fire_on_burning:
            self.set_fire_on_burning(co, 20)

        for co in to_fade:
            self.fade(co)

        for co in to_salt:
            self.salt(co)

        for co in to_ice:
            self.ice(co)

        for co in to_freeze:
            self.freeze(co)

    def generate_material(self, m_type):
        return {"air": Sandbox.GameObjects.Air(), "sand": Sandbox.GameObjects.Sand(),
                "water": Sandbox.GameObjects.Water(), "iron": Sandbox.GameObjects.Iron(),
                "vapor": Sandbox.GameObjects.Vapor(), "fire_4": Sandbox.GameObjects.Fire(4),
                "acid": Sandbox.GameObjects.Acid(), "acid_vapor": Sandbox.GameObjects.AVapor(),
                "dirt": Sandbox.GameObjects.Dirt(), "oil": Sandbox.GameObjects.Oil(),
                "wood": Sandbox.GameObjects.Wood(), "coal": Sandbox.GameObjects.Coal(),
                "fire_5": Sandbox.GameObjects.Fire(5), "salt": Sandbox.GameObjects.Salt(),
                "salt_water": Sandbox.GameObjects.SWater(), "ice": Sandbox.GameObjects.Ice(),
                "snow": Sandbox.GameObjects.Snow(), "gunpowder": Sandbox.GameObjects.Gunpowder(),
                "explosion_wave_gp": Sandbox.GameObjects.ExplosionWave(4, 4),
                "explosion_wave_5_5": Sandbox.GameObjects.ExplosionWave(5, 5),
                "sawdust": Sandbox.GameObjects.Sawdust(), "methane": Sandbox.GameObjects.Methane(),
                "wick": Sandbox.GameObjects.Wick(), "liquid_nitrogen": Sandbox.GameObjects.LNitrogen(),
                "nitrogen": Sandbox.GameObjects.Nitrogen(), "wax": Sandbox.GameObjects.Wax(),
                "liquid_wax": Sandbox.GameObjects.LWax(), "stone": Sandbox.GameObjects.Stone(),
                "strong_fire": Sandbox.GameObjects.StrongFire(5), "lava": Sandbox.GameObjects.Lava()}[m_type]


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
        self.buttons.append(ManageMenu.Button(self, (185, 70), (40, 40), "fire_icon.png", "M", "fire_5"))
        self.buttons.append(ManageMenu.Button(self, (5, 115), (40, 40), "vapor_icon.png", "M", "vapor"))
        self.buttons.append(ManageMenu.Button(self, (50, 115), (40, 40), "acid_icon.png", "M", "acid"))
        self.buttons.append(ManageMenu.Button(self, (95, 115), (40, 40), "acid_vapor_icon.png", "M", "acid_vapor"))
        self.buttons.append(ManageMenu.Button(self, (140, 115), (40, 40), "dirt_icon.png", "M", "dirt"))
        self.buttons.append(ManageMenu.Button(self, (185, 115), (40, 40), "oil_icon.png", "M", "oil"))
        self.buttons.append(ManageMenu.Button(self, (5, 160), (40, 40), "wood_icon.png", "M", "wood"))
        self.buttons.append(ManageMenu.Button(self, (50, 160), (40, 40), "coal_icon.png", "M", "coal"))
        self.buttons.append(ManageMenu.Button(self, (95, 160), (40, 40), "salt_icon.png", "M", "salt"))
        self.buttons.append(ManageMenu.Button(self, (140, 160), (40, 40), "salt_water_icon.png", "M", "salt_water"))
        self.buttons.append(ManageMenu.Button(self, (185, 160), (40, 40), "ice_icon.png", "M", "ice"))
        self.buttons.append(ManageMenu.Button(self, (5, 205), (40, 40), "snow_icon.png", "M", "snow"))
        self.buttons.append(ManageMenu.Button(self, (50, 205), (40, 40), "gunpowder_icon.png", "M", "gunpowder"))
        self.buttons.append(ManageMenu.Button(self, (95, 205), (40, 40), "explosion_wave_icon.png",
                                              "M", "explosion_wave_5_5"))
        self.buttons.append(ManageMenu.Button(self, (140, 205), (40, 40), "sawdust_icon.png", "M", "sawdust"))
        self.buttons.append(ManageMenu.Button(self, (185, 205), (40, 40), "methane_icon.png", "M", "methane"))
        self.buttons.append(ManageMenu.Button(self, (5, 250), (40, 40), "wick_icon.png", "M", "wick"))
        self.buttons.append(ManageMenu.Button(self, (50, 250), (40, 40), "liquid_nitrogen_icon.png",
                                              "M", "liquid_nitrogen"))
        self.buttons.append(ManageMenu.Button(self, (95, 250), (40, 40), "wax_icon.png", "M", "wax"))
        self.buttons.append(ManageMenu.Button(self, (140, 250), (40, 40), "empty.png", "M", "stone"))
        self.buttons.append(ManageMenu.Button(self, (185, 250), (40, 40), "empty.png", "M", "strong_fire"))
        self.buttons.append(ManageMenu.Button(self, (5, 295), (40, 40), "empty.png", "M", "lava"))

        self.buttons.append(ManageMenu.Button(self, (5, 630), (40, 40), "clear_icon.png", "C", "clear"))
        self.buttons.append(ManageMenu.Button(self, (50, 630), (40, 40), "pause_icon.png", "CT", "pause"))
        self.buttons.append(ManageMenu.Button(self, (95, 630), (40, 40), "rainbow_icon.png", "CT", "rainbow_change"))
        self.buttons.append(ManageMenu.Button(self, (140, 630), (40, 40), "features_toggle_icon.png",
                                              "CT", "toggle_obj_f"))
        self.buttons.append(ManageMenu.Button(self, (185, 630), (40, 40), "physics_toggle_icon.png",
                                              "CT", "toggle_obj_p"))
        self.buttons.append(ManageMenu.Button(self, (5, 585), (40, 40), "slow_mo_icon.png", "CT", "slow_motion"))

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
            elif self.button_type == "CT":
                self.selected = not self.selected
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
            self.link_with_board.set_pause()
        elif action_id == "rainbow_change":
            self.parent.rainbow_change()
        elif action_id == "toggle_obj_f":
            self.link_with_board.toggle_obj_features()
        elif action_id == "toggle_obj_p":
            self.link_with_board.toggle_obj_physics()
        elif action_id == "slow_motion":
            self.parent.slow_motion_toggle()

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
        self.size = self.width, self.height = 1040, 692
        self.max_fps = 30
        self.screen = pygame.display.set_mode(self.size, pygame.DOUBLEBUF)
        self.board.set_view(2, 2, 16)
        self.rainbow_color = pygame.Color(0)
        self.rainbow_turn = True
        self.menu = ManageMenu(self.board, self)
        self.menu.set_button_width(3)

    def run_game(self):
        pygame.display.set_icon(load_image("water_icon.png"))
        pygame.display.set_caption("DiversityBox by: AlTaberOwO#2920 , AndrDD#2528")
        screen = self.screen
        clock = pygame.time.Clock()
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
            clock.tick(self.max_fps)
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

    def slow_motion_toggle(self):
        self.max_fps = {30: 10, 10: 30}[self.max_fps]

    class GameObjects:
        class Object:
            def __init__(self):
                self.cls = None
                self.type = None
                self.color = None
                self.weight = None
                self.durability = None
                self.soluble = None
                self.can_be_freezed = None
                self.freezed = False
                self.original_color = None
                self.original_weight = None
                self.original_durability = None

            def freeze(self):
                self.original_color = self.color
                self.original_weight = self.weight
                self.original_durability = self.durability
                self.color = gradient_color((214, 243, 255), self.color, 40)
                self.weight = 20
                self.durability = 0
                self.freezed = True

            def unfreeze(self):
                self.color = self.original_color
                self.durability = self.original_durability
                self.weight = self.original_weight
                self.freezed = False

        # Типы веществ
        class Gas(Object):
            def __init__(self):
                super().__init__()
                self.cls = "gas"
                self.soluble = False
                self.durability = 1
                self.can_be_freezed = False

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
                self.soluble = None
                self.burning = False
                self.extinct_chance = 0

            def burn(self):
                self.burning = True

            def fade(self):
                self.burning = False

        class IgnitableF(Falling):
            def __init__(self):
                super().__init__()
                self.cls = "ignitable_falling"
                self.durability = 1
                self.soluble = None
                self.burning = False
                self.extinct_chance = 0

            def burn(self):
                self.burning = True

            def fade(self):
                self.burning = False

        # Основные вещества
        class Air(Gas):
            def __init__(self):
                super().__init__()
                self.type = "air"
                self.color = [0, 0, 0]
                self.weight = -10
                self.durability = 0
                self.can_be_freezed = False

        class Sand(Falling):
            def __init__(self):
                super().__init__()
                self.type = "sand"
                self.color = approximate_color(200, 200, 100, 10)
                self.weight = 10
                self.durability = 1
                self.soluble = False
                self.can_be_freezed = True

        class Water(Liquid):
            def __init__(self):
                super().__init__()
                self.type = "water"
                self.color = approximate_color(30, 30, 200, 10)
                self.weight = 7
                self.durability = 3
                self.can_be_freezed = False

        class Iron(Solid):
            def __init__(self):
                super().__init__()
                self.type = "iron"
                self.color = approximate_color(173, 173, 173, 2)
                self.weight = 20
                self.durability = 3
                self.soluble = True
                self.can_be_freezed = True

        class Vapor(Gas):
            def __init__(self):
                super().__init__()
                self.type = "vapor"
                self.color = approximate_color(222, 222, 222, 3)
                self.weight = -11
                self.durability = 1

        class Fire(Special):
            def __init__(self, temperature):
                super().__init__()
                self.type = "fire"
                self.color = [222, 89, 22]
                self.weight = -100
                self.temperature = temperature
                self.soluble = False
                self.durability = 1
                self.can_be_freezed = False

            def fade(self):
                self.temperature -= 1
                self.color = gradient_color([222, 89, 22], [61, 12, 12], self.temperature * 20)

        class Acid(Liquid):
            def __init__(self):
                super().__init__()
                self.type = "acid"
                self.color = approximate_color(130, 227, 27, 10)
                self.weight = 7
                self.durability = 3
                self.can_be_freezed = True

        class AVapor(Gas):
            def __init__(self):
                super().__init__()
                self.type = "acid_vapor"
                self.color = approximate_color(145, 235, 154, 3)
                self.weight = -11
                self.durability = 1

        class Dirt(Falling):
            def __init__(self):
                super().__init__()
                self.type = "dirt"
                self.color = approximate_color(105, 39, 10, 5)
                self.weight = 10
                self.durability = 1
                self.soluble = True
                self.can_be_freezed = True

        class Oil(IgnitableL):
            def __init__(self):
                super().__init__()
                self.type = "oil"
                self.color = approximate_color(25, 22, 31, 1)
                self.weight = 6
                self.durability = 1
                self.extinct_chance = 20
                self.can_be_freezed = True

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
                self.durability = 2
                self.extinct_chance = 110
                self.soluble = True
                self.can_be_freezed = True

            def random_burning_color(self):
                self.color = approximate_color(20, 14, 11, 10)

        class Coal(IgnitableS):
            def __init__(self):
                super().__init__()
                self.type = "coal"
                self.color = approximate_color(15, 14, 23, 2)
                self.weight = 20
                self.durability = 2
                self.extinct_chance = 200
                self.soluble = True
                self.can_be_freezed = True

            def random_burning_color(self):
                self.color = approximate_color(56, 50, 45, 10)

        class Salt(Falling):
            def __init__(self):
                super().__init__()
                self.type = "salt"
                self.color = approximate_color(237, 237, 237, 15)
                self.weight = 10
                self.durability = 1
                self.soluble = True
                self.can_be_freezed = True

        class SWater(Liquid):
            def __init__(self):
                super().__init__()
                self.type = "salt_water"
                self.color = approximate_color(84, 92, 176, 10)
                self.weight = 8
                self.durability = 3
                self.can_be_freezed = True

        class Ice(Solid):
            def __init__(self):
                super().__init__()
                self.type = "ice"
                self.color = approximate_color(47, 133, 204, 1)
                self.weight = 20
                self.durability = 2
                self.soluble = False
                self.can_be_freezed = True

        class Snow(Falling):
            def __init__(self):
                super().__init__()
                self.type = "snow"
                self.color = approximate_color(171, 196, 217, 4)
                self.weight = 6
                self.durability = 2
                self.soluble = False
                self.can_be_freezed = True

        class Gunpowder(Falling):
            def __init__(self):
                super().__init__()
                self.type = "gunpowder"
                self.color = approximate_color(36, 37, 38, 3)
                self.weight = 10
                self.durability = 1
                self.soluble = True
                self.can_be_freezed = True

        class ExplosionWave(Special):
            def __init__(self, power, range):
                super().__init__()
                self.type = "explosion_wave"
                self.weight = 20
                self.durability = 1000
                self.soluble = False
                self.power = power
                self.range = range
                self.color = gradient_color((255, 106, 0), (0, 0, 0), self.range * 25)
                self.life_tick = 2
                self.can_be_freezed = False

            def fade(self):
                self.life_tick -= 1

        class Sawdust(IgnitableF):
            def __init__(self):
                super().__init__()
                self.type = "sawdust"
                self.color = approximate_color(179, 104, 20, 4)
                self.weight = 10
                self.durability = 1
                self.soluble = True
                self.extinct_chance = 70
                self.can_be_freezed = True

            def random_burning_color(self):
                self.color = approximate_color(20, 14, 11, 10)

        class Methane(Gas):
            def __init__(self):
                super().__init__()
                self.type = "methane"
                self.color = approximate_color(26, 26, 26, 3)
                self.weight = -11
                self.durability = 1

        class Wick(Solid):
            def __init__(self):
                super().__init__()
                self.type = "wick"
                self.color = approximate_color(7, 61, 19, 4)
                self.weight = 20
                self.durability = 1
                self.soluble = True
                self.activated = False
                self.can_be_freezed = True

            def activate(self):
                self.activated = True
                self.color = approximate_color(245, 110, 0, 5)

        class LNitrogen(Liquid):
            def __init__(self):
                super().__init__()
                self.type = "liquid_nitrogen"
                self.color = approximate_color(210, 236, 247, 10)
                self.weight = 7
                self.durability = 3
                self.can_be_freezed = False

        class Nitrogen(Gas):
            def __init__(self):
                super().__init__()
                self.type = "nitrogen"
                self.color = approximate_color(210, 236, 247, 3)
                self.weight = -11
                self.durability = 1

        class Wax(Solid):
            def __init__(self):
                super().__init__()
                self.type = "wax"
                self.color = approximate_color(214, 193, 161, 4)
                self.weight = 20
                self.durability = 1
                self.soluble = True
                self.can_be_freezed = True

        class LWax(Liquid):
            def __init__(self):
                super().__init__()
                self.type = "liquid_wax"
                self.color = approximate_color(255, 230, 191, 4)
                self.weight = 7
                self.durability = 1
                self.soluble = True
                self.can_be_freezed = True

        class Stone(Solid):
            def __init__(self):
                super().__init__()
                self.type = "stone"
                self.color = approximate_color(55, 63, 67, 4)
                self.weight = 20
                self.durability = 2
                self.soluble = True
                self.can_be_freezed = True

        class StrongFire(Special):
            def __init__(self, temperature):
                super().__init__()
                self.type = "strong_fire"
                self.color = [30, 144, 255]
                self.weight = -100
                self.temperature = temperature
                self.soluble = False
                self.durability = 1
                self.can_be_freezed = False

            def fade(self):
                self.temperature -= 1
                self.color = gradient_color([30, 144, 255], [12, 16, 61], self.temperature * 20)

        class Lava(Liquid):
            def __init__(self):
                super().__init__()
                self.type = "lava"
                self.color = approximate_color(227, 95, 0, 10)
                self.weight = 9
                self.durability = 1
                self.soluble = False
                self.can_be_freezed = False



sandbox = Sandbox()
sandbox.run_game()
