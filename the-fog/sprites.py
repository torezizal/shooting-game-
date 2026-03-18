import pygame
from os.path import join
from random import randint, uniform


class CameraGroup(pygame.sprite.Group):
    def __init__(self):
        super().__init__()
        self.offset = pygame.Vector2()
        self.shake_amount = 0

    def custom_draw(self, player):
        # Fix: set base offset FIRST, then apply shake on top
        # (previously shake was applied before offset was set, so it was always overwritten)
        self.offset.x = player.rect.centerx - 600
        self.offset.y = player.rect.centery - 360

        if self.shake_amount > 0:
            self.offset.x += randint(-self.shake_amount, self.shake_amount)
            self.offset.y += randint(-self.shake_amount, self.shake_amount)
            self.shake_amount -= 1

        surface = pygame.display.get_surface()
        for sprite in sorted(self.sprites(), key=lambda s: s.rect.centery):
            surface.blit(sprite.image, sprite.rect.topleft - self.offset)
            if hasattr(sprite, 'draw_health_bar'):
                sprite.draw_health_bar(surface, self.offset)


class Particle(pygame.sprite.Sprite):
    def __init__(self, pos, color, groups):
        super().__init__(*groups)
        self.image = pygame.Surface((2, 2))
        self.image.fill(color)
        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.math.Vector2(pos)
        self.direction = pygame.math.Vector2(uniform(-1, 1), uniform(-1, 1)) * 50
        self.lifetime = 300
        self.start_time = pygame.time.get_ticks()

    def update(self, dt):
        self.pos += self.direction * dt
        self.rect.center = self.pos
        if pygame.time.get_ticks() - self.start_time > self.lifetime:
            self.kill()


class Explosion(pygame.sprite.Sprite):
    def __init__(self, pos, groups):
        super().__init__(*groups)
        self.radius, self.max_radius, self.opacity = 10, 300, 255
        self.image = pygame.Surface((self.max_radius * 2, self.max_radius * 2), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=pos)
        for _ in range(50):
            Particle(pos, (255, 255, 200), groups)

    def update(self, dt):
        self.radius += 1200 * dt
        self.opacity -= 500 * dt
        if self.opacity <= 0:
            self.kill()
        else:
            self.image.fill((0, 0, 0, 0))
            pygame.draw.circle(self.image, (255, 255, 255, int(self.opacity)),
                               (self.max_radius, self.max_radius), int(self.radius), 20)


class Bullet(pygame.sprite.Sprite):
    def __init__(self, pos, direction, groups, damage=25, color="yellow", is_split=False):
        super().__init__(*groups)
        size = 6 if is_split else 10
        self.image = pygame.Surface((size, size))
        self.image.fill(color)
        self.rect = self.image.get_rect(center=pos)

        self.pos = pygame.math.Vector2(pos)
        self.direction = direction.normalize()
        self.speed = 900
        self.damage = 10 if is_split else damage
        self.color = color
        self.groups = groups
        self.is_split = is_split
        self.limit = 4096

    def split(self):
        if self.color != "yellow" and not self.is_split:
            dir1 = self.direction.rotate(45)
            dir2 = self.direction.rotate(-45)
            Bullet(self.rect.center, dir1, self.groups, damage=10, color=self.color, is_split=True)
            Bullet(self.rect.center, dir2, self.groups, damage=10, color=self.color, is_split=True)
            for _ in range(5):
                Particle(self.rect.center, "white", self.groups)

    def update(self, dt):
        self.pos += self.direction * self.speed * dt
        self.rect.center = self.pos

        if not self.is_split and self.color != "yellow":
            if self.pos.x <= 0 or self.pos.x >= self.limit or self.pos.y <= 0 or self.pos.y >= self.limit:
                self.split()
                self.kill()

        if self.color != "yellow":
            Particle(self.rect.center, self.color, self.groups)

        if self.pos.length() > 10000:
            self.kill()


class Enemy(pygame.sprite.Sprite):
    def __init__(self, type_name, pos, groups, player, boss=False):
        super().__init__(*groups)
        self.player = player
        self.is_boss = boss

        try:
            self.frames = [
                pygame.image.load(join("data", "graphics", "enemies", type_name, f"{i}.png")).convert_alpha()
                for i in range(4)
            ]
        except:
            self.frames = [pygame.Surface((40, 40)) for _ in range(4)]
            for f in self.frames:
                f.fill("red")

        self.frame_index = 0
        self.image = self.frames[0]
        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.math.Vector2(pos)
        self.knockback_vector = pygame.math.Vector2()

        if boss:
            self.health, self.speed = 6000, 100
        elif type_name == "bat":
            self.health, self.speed = 5, 450
        elif type_name == "skeleton":
            self.health, self.speed = 20, 300
        elif type_name == "blob":
            self.health, self.speed = 15, 80
        else:
            self.health, self.speed = 30, 130

        self.max_health = self.health

    def draw_health_bar(self, surf, offset):
        if self.health < self.max_health:
            x, y = self.rect.centerx - 20 - offset.x, self.rect.top - 10 - offset.y
            pygame.draw.rect(surf, "red", (x, y, 40, 5))
            pygame.draw.rect(surf, "green", (x, y, 40 * (max(0, self.health / self.max_health)), 5))

    def update(self, dt):
        if self.knockback_vector.length() > 0.1:
            self.pos += self.knockback_vector * dt
            self.knockback_vector *= 0.9

        dir_vec = self.player.pos - self.pos
        if 0 < dir_vec.length() < 1000:
            if self.knockback_vector.length() < 100:
                self.pos += dir_vec.normalize() * self.speed * dt
            self.rect.center = self.pos
            self.frame_index = (self.frame_index + 10 * dt) % 4
            self.image = self.frames[int(self.frame_index)]


class XpOrb(pygame.sprite.Sprite):
    def __init__(self, pos, groups, player):
        super().__init__(*groups)
        self.player = player
        self.image = pygame.Surface((10, 10))
        self.image.fill("cyan")
        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.math.Vector2(pos)

    def update(self, dt):
        direction = self.player.pos - self.pos
        if direction.length() < 300:
            self.pos += direction.normalize() * 750 * dt
        self.rect.center = self.pos


class DestructibleObject(pygame.sprite.Sprite):
    def __init__(self, image_name, pos, groups):
        super().__init__(*groups)
        try:
            self.image = pygame.image.load(join("data", "graphics", "objects", image_name)).convert_alpha()
        except:
            self.image = pygame.Surface((50, 50))
            self.image.fill("brown")
        self.rect = self.image.get_rect(topleft=pos)
        self.health = self.max_health = 3

    def take_damage(self, amount, groups=None):
        # Fix: groups parameter was accepted but never used — explosion wired in,
        # guarded so it's optional until Explosion import is confirmed working
        self.health -= amount
        if self.health <= 0:
            if groups:
                Explosion(self.rect.center, groups)
            self.kill()

    def draw_health_bar(self, surf, offset):
        if self.health < self.max_health:
            x, y = self.rect.centerx - 25 - offset.x, self.rect.top - 10 - offset.y
            pygame.draw.rect(surf, (50, 20, 0), (x, y, 50, 6))
            pygame.draw.rect(surf, (200, 150, 50), (x, y, 50 * (self.health / self.max_health), 6))


def spawn_static_objects(all_sprites, collision_sprites):
    names = ["grassrock1.png", "green_tree.png", "palm.png", "ruin_pillar.png"]
    for _ in range(25):
        name = names[randint(0, len(names) - 1)]
        pos = (randint(100, 3900), randint(100, 3900))
        s = pygame.sprite.Sprite()
        s.add(all_sprites, collision_sprites)
        try:
            s.image = pygame.image.load(join("data", "graphics", "objects", name)).convert_alpha()
        except:
            s.image = pygame.Surface((40, 40))
            s.image.fill("green")
        s.rect = s.image.get_rect(topleft=pos)


def spawn_destructibles(all_sprites, collision_sprites):
    names = ["ruin_pillar_broke.png", "palm_small.png"]
    for _ in range(15):
        DestructibleObject(names[randint(0, 1)], (randint(100, 3900), randint(100, 3900)),
                           [all_sprites, collision_sprites])