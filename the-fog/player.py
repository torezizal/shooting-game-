import pygame
import math
from os.path import join

class Player(pygame.sprite.Sprite):
    def __init__(self, pos, groups, collision_sprites):
        super().__init__(*groups)

        # 1. GRAPHICS SETUP
        self.animations = {'up': [], 'down': [], 'left': [], 'right': []}
        self.status = 'down'
        self.frame_index = 0

        try:
            for condition in self.animations.keys():
                full_path = join("data", "graphics", "player", condition)
                for i in range(4):
                    img = pygame.image.load(join(full_path, f"{i}.png")).convert_alpha()
                    img = pygame.transform.scale(img, ((125, 125)))
                    self.animations[condition].append(img)
        except Exception as e:
            print(f"Loading Error: {e}")
            for condition in self.animations.keys():
                surf = pygame.Surface((125, 125)); surf.fill("blue")
                self.animations[condition] = [surf] * 4

        self.image = self.animations[self.status][self.frame_index]
        self.rect = self.image.get_rect(center=pos)

        # 2. MOVEMENT STATS (Fixed AttributeError)
        self.pos = pygame.math.Vector2(pos)
        self.direction = pygame.math.Vector2()
        self.base_speed = 300
        self.speed = self.base_speed
        self.collision_sprites = collision_sprites

        # 3. COMBAT & HUD STATS
        self.max_health = 100
        self.health = 100
        self.max_shield = 100
        self.shield = 100
        self.bullet_damage = 25
        self.xp = 0
        self.last_hit_timer = 0
        self.fire_rate = 0.4

        # 4. GUN GRAPHICS
        try:
            self.pistol_surf = pygame.image.load(join("data", "graphics", "gun", "gun.png")).convert_alpha()
            self.uzi_surf = pygame.image.load(join("data", "graphics", "gun", "uzi.png")).convert_alpha()
        except:
            self.pistol_surf = pygame.Surface((30, 10)); self.pistol_surf.fill("gray")
            self.uzi_surf = pygame.Surface((35, 15)); self.uzi_surf.fill("black")

    def input(self):
        keys = pygame.key.get_pressed()
        self.direction.y = (1 if keys[pygame.K_s] else 0) - (1 if keys[pygame.K_w] else 0)
        self.direction.x = (1 if keys[pygame.K_d] else 0) - (1 if keys[pygame.K_a] else 0)
        if self.direction.length() > 0:
            self.direction = self.direction.normalize()

    def get_status(self):
        if self.direction.y < 0: self.status = 'up'
        elif self.direction.y > 0: self.status = 'down'
        elif self.direction.x < 0: self.status = 'left'
        elif self.direction.x > 0: self.status = 'right'

    def move(self, dt):
        self.pos.x += self.direction.x * self.speed * dt
        self.rect.centerx = round(self.pos.x)
        self.collision('horizontal')

        self.pos.y += self.direction.y * self.speed * dt
        self.rect.centery = round(self.pos.y)
        self.collision('vertical')

    def collision(self, direction):
        for sprite in self.collision_sprites:
            if sprite.rect.colliderect(self.rect):
                if direction == 'horizontal':
                    if self.direction.x > 0: self.rect.right = sprite.rect.left
                    if self.direction.x < 0: self.rect.left = sprite.rect.right
                    self.pos.x = self.rect.centerx
                if direction == 'vertical':
                    if self.direction.y > 0: self.rect.bottom = sprite.rect.top
                    if self.direction.y < 0: self.rect.top = sprite.rect.bottom
                    self.pos.y = self.rect.centery

    def animate(self, dt):
        if self.direction.length() > 0:
            self.frame_index += 10 * dt
            if self.frame_index >= len(self.animations[self.status]):
                self.frame_index = 0
        else:
            self.frame_index = 0
        self.image = self.animations[self.status][int(self.frame_index)]

    def draw_gun(self, surface, offset, current_weapon="pistol"):
        gun_base = self.uzi_surf if current_weapon == "uzi" else self.pistol_surf
        size = (80, 40) if current_weapon == "uzi" else (50, 25)
        gun_surf = pygame.transform.scale(gun_base, size)

       
        hand_offset = pygame.Vector2(10, 15)

        m_pos = pygame.mouse.get_pos()
        p_screen_center = self.rect.center - offset

       
        side_shift = 20 if m_pos[0] > p_screen_center.x else -15
        hand_offset = pygame.Vector2(side_shift, 30)

        p_gun_pos = p_screen_center + hand_offset

    
        rel_x = m_pos[0] - p_gun_pos.x
        rel_y = m_pos[1] - p_gun_pos.y
        angle = math.degrees(math.atan2(-rel_y, rel_x))

        rotated_gun = pygame.transform.rotate(gun_surf, angle)
        if abs(angle) > 90:
            rotated_gun = pygame.transform.flip(rotated_gun, False, True)

        # 5. Draw
        gun_rect = rotated_gun.get_rect(center=p_gun_pos)
        surface.blit(rotated_gun, gun_rect)

    def update(self, dt):
        self.input()
        self.get_status()
        self.move(dt)
        self.animate(dt)
