import pygame, sys, random, pytmx, math
from os.path import join
from sprites import CameraGroup, Enemy, Bullet, XpOrb, Explosion, Particle, spawn_static_objects, spawn_destructibles
from player import Player


class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        self.display = pygame.display.set_mode((1200, 720))
        pygame.display.set_caption("The Fog")
        self.clock = pygame.time.Clock()
        self.running = True

        # 1. Stats and Scaling
        self.upgrade_costs = [50, 100, 200, 350, 500, 1000]
        self.gun_damages = [25, 35, 50, 65]
        self.bomb_damages = [200, 220, 240, 260]
        self.max_healths = [100, 200, 350, 500]

        self.upgrade_level = 0
        self.gun_lv = 0
        self.bomb_lv = 0
        self.health_lv = 0

        self.total_xp_gained = 0
        self.shoot_timer = 0
        self.state = "PLAYING"

        # --- WAVE SYSTEM ---
        self.current_wave = 1
        self.enemies_remaining_to_spawn = 20
        self.wave_transition = False
        self.wave_message_timer = 0
        self.spawn_timer = 0

        self.fog_timer = 0
        self.was_in_fog = False
        self.relief_timer = 0
        self.death_timer = 0
        self.stalker_pos = pygame.math.Vector2(0, 0)
        self.stalker_active = False

        # --- UZI SYSTEM 
        self.uzi_unlocked = False
        self.current_weapon = "pistol"
        self.uzi_cost = 50
        self.uzi_ammo = 30
        self.max_uzi_ammo = 30
        self.is_reloading = False
        self.reload_timer = 0

        # --- BOMB SYSTEM 
        self.bomb_count = 3
        self.max_bombs = 3
        self.bomb_cooldown = 0
        self.bomb_cooldown_max = 3.0

        # --- CACHED FONT
        self.font_lg = pygame.font.SysFont("Arial", 60, True)
        self.font_xl = pygame.font.SysFont("Arial", 80, True)
        self.font_md = pygame.font.SysFont("Arial", 45)
        self.font_sm = pygame.font.SysFont("Arial", 18, True)
        self.font_body = pygame.font.SysFont("Arial", 28)
        self.font_warn = pygame.font.SysFont("Verdana", 32, True)
        self.font_warn_sm = pygame.font.SysFont("Verdana", 22, True)
        self.font_death = pygame.font.SysFont("Courier", 60, True)
        self.mission_complete_timer = 0

        # --- PRE-RENDERED VISUAL SURFACES ---
        self.static_surf = pygame.Surface((300, 200))
        self.dark_overlay = pygame.Surface((1200, 720))
        self.vignette_surf = pygame.Surface((1200, 720), pygame.SRCALPHA)
        self._generate_vignette()

        # 2. Sprite Groups
        self.all_sprites = CameraGroup()
        self.enemy_sprites = pygame.sprite.Group()
        self.bullet_sprites = pygame.sprite.Group()
        self.xp_sprites = pygame.sprite.Group()
        self.collision_sprites = pygame.sprite.Group()

        # 3. Map & Player Setup
        try:
            self.tmx_data = pytmx.util_pygame.load_pygame(join("data", "maps", "world.tmx"))
        except:
            self.tmx_data = None

        # Map
        self.map_limit = 4096
        if self.tmx_data:
            self.map_pixel_w = self.tmx_data.width  * self.tmx_data.tilewidth
            self.map_pixel_h = self.tmx_data.height * self.tmx_data.tileheight
        else:
            self.map_pixel_w = self.map_pixel_h = self.map_limit
        self.tile_scale_x = self.map_limit / self.map_pixel_w
        self.tile_scale_y = self.map_limit / self.map_pixel_h
        scaled_tile_w = int((self.tmx_data.tilewidth  if self.tmx_data else 64) * self.tile_scale_x) + 1
        scaled_tile_h = int((self.tmx_data.tileheight if self.tmx_data else 64) * self.tile_scale_y) + 1

        # --surface--
        self.map_surface = pygame.Surface((self.map_limit, self.map_limit))
        if self.tmx_data:
            for layer in self.tmx_data.visible_layers:
                if hasattr(layer, "data"):
                    for x, y, gid in layer:
                        if gid == 0:
                            continue
                        tile = self.tmx_data.get_tile_image_by_gid(gid)
                        if tile:
                            scaled = pygame.transform.scale(tile, (scaled_tile_w, scaled_tile_h))
                            blit_x = int(x * self.tmx_data.tilewidth  * self.tile_scale_x)
                            blit_y = int(y * self.tmx_data.tileheight * self.tile_scale_y)
                            self.map_surface.blit(scaled, (blit_x, blit_y))

        self.player = Player((192, 192), [self.all_sprites], self.collision_sprites)
        self.player.bullet_damage = self.gun_damages[0]
        self.player.game = self

        self.setup_tmx_entities()
        spawn_static_objects(self.all_sprites, self.collision_sprites)
        spawn_destructibles(self.all_sprites, self.collision_sprites)

       
        self._upgrade_rects = {}

    def _generate_vignette(self):
            for y in range(0, 720, 2):
            for x in range(0, 1200, 2):
                dx, dy = abs(x - 600) / 600, abs(y - 360) / 360
                dist = math.sqrt(dx ** 2 + dy ** 2)
                if dist > 0.5:
                    alpha = int(min(255, (dist - 0.5) * 2 * 180))
                    pygame.draw.rect(self.vignette_surf, (150, 0, 0, alpha), (x, y, 2, 2))

    def setup_tmx_entities(self):
        if self.tmx_data:
            for obj in self.tmx_data.objects:
                if obj.name in ["bat", "skeleton", "blob"]:
                    Enemy(obj.name, (obj.x, obj.y), [self.all_sprites, self.enemy_sprites], self.player)
                elif obj.name in ["wall", "solid"] or obj.type == "collision":
                    col = pygame.sprite.Sprite(self.collision_sprites)
                    col.rect = pygame.Rect(obj.x, obj.y, obj.width, obj.height)

    def reset_game(self):
        for group in [self.all_sprites, self.enemy_sprites, self.bullet_sprites, self.xp_sprites,
                      self.collision_sprites]:
            group.empty()

        self.current_wave = 1
        self.enemies_remaining_to_spawn = 20
        self.upgrade_level = self.gun_lv = self.bomb_lv = self.health_lv = 0
        self.total_xp_gained = self.death_timer = self.shoot_timer = 0
        self.uzi_unlocked = False
        self.current_weapon = "pistol"
        self.bomb_count = 3
        self.bomb_cooldown = 0

        self.player = Player((192, 192), [self.all_sprites], self.collision_sprites)
        self.player.bullet_damage = self.gun_damages[0]
        self.player.game = self
        self.setup_tmx_entities()
        spawn_static_objects(self.all_sprites, self.collision_sprites)
        spawn_destructibles(self.all_sprites, self.collision_sprites)
        self.state = "PLAYING"

    def shoot(self):
        if self.is_reloading:
            return
        now = pygame.time.get_ticks()
        fire_rate_ms = 120 if self.current_weapon == "uzi" else int(self.player.fire_rate * 1000)

        if now - self.shoot_timer > fire_rate_ms:
            m_pos = pygame.mouse.get_pos() + self.all_sprites.offset
            b_dir = (m_pos - self.player.pos).normalize()

            if self.current_weapon == "uzi":
                if self.uzi_ammo > 0:
                    self.uzi_ammo -= 1
                    self.all_sprites.shake_amount = 2
                    colors = ["cyan", "magenta", "lime", "orange", "hotpink"]
                    for _ in range(5):
                        Bullet(self.player.rect.center, b_dir.rotate(random.uniform(-18, 18)),
                               [self.all_sprites, self.bullet_sprites], damage=10, color=random.choice(colors))
                else:
                    self.is_reloading = True
                    self.reload_timer = now
            else:
                self.all_sprites.shake_amount = 4
                Bullet(self.player.rect.center, b_dir, [self.all_sprites, self.bullet_sprites],
                       damage=self.player.bullet_damage)
            self.shoot_timer = now

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and self.uzi_unlocked:
                    self.current_weapon = "uzi" if self.current_weapon == "pistol" else "pistol"
                    self.is_reloading = False
                if event.key == pygame.K_q and self.state == "PLAYING":
                    self.throw_bomb()
                if event.key == pygame.K_e:
                    self.state = "UPGRADE_MENU" if self.state == "PLAYING" else "PLAYING"
                if event.key == pygame.K_ESCAPE:
                    self.state = "PAUSE_MENU" if self.state == "PLAYING" else "PLAYING"

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = pygame.mouse.get_pos()
                if self.state == "UPGRADE_MENU":
                    cost = self.upgrade_costs[min(self.upgrade_level, 5)]
                    gun_rect  = self._upgrade_rects.get("gun")
                    bomb_rect = self._upgrade_rects.get("bomb")
                    uzi_rect  = self._upgrade_rects.get("uzi")
                    if gun_rect and gun_rect.collidepoint(mx, my) and self.player.xp >= cost and self.gun_lv < len(self.gun_damages) - 1:
                        self.gun_lv += 1
                        self.player.bullet_damage = self.gun_damages[self.gun_lv]
                        self.player.xp -= cost
                        self.upgrade_level += 1
                    elif bomb_rect and bomb_rect.collidepoint(mx, my) and self.player.xp >= cost and self.bomb_lv < len(self.bomb_damages) - 1:
                        self.bomb_lv += 1
                        self.player.xp -= cost
                        self.upgrade_level += 1
                    elif uzi_rect and uzi_rect.collidepoint(mx, my) and self.player.xp >= 50 and not self.uzi_unlocked:
                        self.player.xp -= 50
                        self.uzi_unlocked = True
                    buy_bombs_rect = self._upgrade_rects.get("buy_bombs")
                    if buy_bombs_rect and buy_bombs_rect.collidepoint(mx, my) and self.player.xp >= 400 and self.bomb_count < self.max_bombs:
                        self.player.xp -= 400
                        self.bomb_count = min(self.bomb_count + 3, self.max_bombs)
                elif self.state == "VICTORY_SCREEN":
                    cont_rect = self._upgrade_rects.get("victory_continue")
                    quit_rect = self._upgrade_rects.get("victory_quit")
                    if cont_rect and cont_rect.collidepoint(mx, my):
                        self.wave_transition = True
                        self.wave_message_timer = pygame.time.get_ticks()
                        self.state = "PLAYING"
                    elif quit_rect and quit_rect.collidepoint(mx, my):
                        self.running = False
                elif self.state == "MISSION_COMPLETE":
                    quit_rect = self._upgrade_rects.get("mc_quit")
                    restart_rect = self._upgrade_rects.get("mc_restart")
                    if restart_rect and restart_rect.collidepoint(mx, my):
                        self.reset_game()
                    elif quit_rect and quit_rect.collidepoint(mx, my):
                        self.running = False
                elif self.state == "DEATH_SCREEN" and self.death_timer > 2.5:
                    if 450 <= my <= 500:
                        self.reset_game()

    def update(self):
        dt = self.clock.tick(60) / 1000
        self.handle_events()
        if self.state == "DEATH_SCREEN":
            self.death_timer += dt
            return
        if self.state != "PLAYING":
            return

        if pygame.mouse.get_pressed()[0]:
            self.shoot()

        # Reload 
        if self.is_reloading and pygame.time.get_ticks() - self.reload_timer > 2000:
            self.uzi_ammo = self.max_uzi_ammo
            self.is_reloading = False

        # Bomb cooldown 
        if self.bomb_cooldown > 0:
            self.bomb_cooldown -= dt

        
        limit = self.map_limit
        is_in_fog = (self.player.rect.right > limit or self.player.rect.left < 0 or
                     self.player.rect.bottom > limit or self.player.rect.top < 0)

        if is_in_fog:
            self.player.speed = self.player.base_speed * 2.0
            self.fog_timer += dt
            if self.fog_timer > 3.0:
                self.player.health -= 1
            if not self.stalker_active:
                self.stalker_active = True
                self.stalker_pos = pygame.math.Vector2(self.player.rect.center) + pygame.Vector2(400, 400)

            s_speed = (0.8 + ((100 - self.player.health) // 10) * 0.1) * (2.0 if self.current_wave >= 5 else 1.0)
            mv = pygame.math.Vector2(self.player.rect.center) - self.stalker_pos
            if mv.length() > 0:
                self.stalker_pos += mv.normalize() * s_speed
            if mv.length() < 40:
                self.player.health = 0
        else:
            self.player.speed = self.player.base_speed
            self.fog_timer = 0
            self.stalker_active = False

        # Recovery Logic
        s_dist = 1000 if not self.stalker_active else self.player.pos.distance_to(self.stalker_pos)
        if pygame.time.get_ticks() - self.player.last_hit_timer > 5000 and s_dist > 200:
            if self.player.shield < 100:
                self.player.shield += 0.5
            if self.player.health < 100:
                self.player.health += 1 / 60

        # --- ENEMY COLLISIONS ---
        for b in list(self.bullet_sprites):
            if hasattr(b, 'damage'):
                e_hits = pygame.sprite.spritecollide(b, self.enemy_sprites, False)
                for e in e_hits:
                    e.health -= b.damage
                    e.knockback_vector = b.direction * 500
                    b.kill()
                    if e.health <= 0:
                         if getattr(e, 'is_boss', False):
                            self.state = "VICTORY_SCREEN"
                        self.player.xp += 10
                        self.total_xp_gained += 10
                        XpOrb(e.rect.center, [self.all_sprites, self.xp_sprites], self.player)
                        e.kill()

        p_hits = pygame.sprite.spritecollide(self.player, self.enemy_sprites, False)
        if p_hits:
            self.player.last_hit_timer = pygame.time.get_ticks()
            for e in p_hits:
                if self.player.shield > 0:
                    self.player.shield -= 0.5
                else:
                    self.player.health -= 0.5

        if self.player.health <= 0:
            self.state = "DEATH_SCREEN"
        if self.was_in_fog and not is_in_fog:
            self.relief_timer = 30
        self.was_in_fog = is_in_fog

        # Wave Management
        if len(self.enemy_sprites) == 0 and self.enemies_remaining_to_spawn <= 0 and not self.wave_transition:
            if self.current_wave >= 6:
                self.mission_complete_timer = pygame.time.get_ticks()
                self.state = "MISSION_COMPLETE"
            else:
                self.wave_transition = True
                self.wave_message_timer = pygame.time.get_ticks()

        if self.wave_transition and pygame.time.get_ticks() - self.wave_message_timer > 3000:
            self.current_wave += 1
            self.wave_transition = False
            w_map = {2: 30, 3: 40, 4: 50, 5: 6, 6: 51}
            self.enemies_remaining_to_spawn = w_map.get(self.current_wave, 50)
            if self.current_wave == 5:
                self.all_sprites.shake_amount = 50

        if self.enemies_remaining_to_spawn > 0 and not self.wave_transition:
            self.spawn_timer += dt
            if self.spawn_timer > 0.6:
                self.spawn_wave_enemy()
                self.enemies_remaining_to_spawn -= 1
                self.spawn_timer = 0

        self.all_sprites.update(dt)

    def throw_bomb(self):
        if self.bomb_count <= 0 or self.bomb_cooldown > 0:
            return
        target = pygame.math.Vector2(pygame.mouse.get_pos()) + self.all_sprites.offset

        damage = self.bomb_damages[self.bomb_lv]
        blast_radius = 180 + self.bomb_lv * 30

        for e in list(self.enemy_sprites):
            if dist < blast_radius:
                e.health -= damage
                kb = e.pos - target
                if kb.length() > 0:
                    e.knockback_vector = kb.normalize() * 800
                if e.health <= 0:
                    if getattr(e, 'is_boss', False):
                        self.state = "VICTORY_SCREEN"
                    self.player.xp += 10
                    self.total_xp_gained += 10
                    XpOrb(e.rect.center, [self.all_sprites, self.xp_sprites], self.player)
                    e.kill()

        Explosion(target, [self.all_sprites])
        self.all_sprites.shake_amount = 8

        self.bomb_count -= 1
        self.bomb_cooldown = self.bomb_cooldown_max

    def draw(self):
        self.display.fill("black")

    
        ox, oy = int(self.all_sprites.offset.x), int(self.all_sprites.offset.y)
        visible_rect = pygame.Rect(ox, oy, 1200, 720)
    
        clamped = visible_rect.clip(pygame.Rect(0, 0, self.map_limit, self.map_limit))
        if clamped.width > 0 and clamped.height > 0:
            dest_x = clamped.x - ox
            dest_y = clamped.y - oy
            self.display.blit(self.map_surface, (dest_x, dest_y), clamped)

        # 2. Draw sprites
        self.all_sprites.custom_draw(self.player)
        self.player.draw_gun(self.display, self.all_sprites.offset, self.current_weapon)

        # 3. Fog walls
        limit, thick = self.map_limit, 1920
        fog_rects = [pygame.Rect(-thick, -thick, limit + thick * 2, thick),  
                     pygame.Rect(-thick, limit,  limit + thick * 2, thick),  
                     pygame.Rect(-thick, 0,       thick, limit),             
                     pygame.Rect(limit,  0,       thick, limit)]             
        for r in fog_rects:
            r.topleft -= self.all_sprites.offset
            pygame.draw.rect(self.display, (30, 35, 40), r)

        # 4. Darkness & Flashlight
        is_in_fog = (self.player.rect.right > limit or self.player.rect.left < 0 or
                     self.player.rect.bottom > limit or self.player.rect.top < 0)
        if is_in_fog:
            if self.stalker_active:
                s_s = pygame.Surface((50, 80), pygame.SRCALPHA)
                pygame.draw.ellipse(s_s, (10, 10, 10, 220), (0, 0, 50, 80))
                ep = int(155 + 100 * math.sin(pygame.time.get_ticks() * 0.02))
                pygame.draw.circle(s_s, (ep, 0, 0), (15, 25), 4)
                pygame.draw.circle(s_s, (ep, 0, 0), (35, 25), 4)
                self.display.blit(s_s, self.stalker_pos - self.all_sprites.offset - pygame.Vector2(25, 40))

            self.dark_overlay.fill((10, 10, 20))
            if random.random() > (0.05 + (1 - self.player.health / 100) * 0.5):
                self.dark_overlay.set_colorkey((255, 0, 255))
                p_center = self.player.rect.center - self.all_sprites.offset
                pygame.draw.circle(self.dark_overlay, (255, 0, 255), p_center,
                                   int(150 * max(0.4, self.player.health / 100)))
            self.display.blit(self.dark_overlay, (0, 0))

            dist = 1000 if not self.stalker_active else self.player.pos.distance_to(self.stalker_pos)
            msg = "HE IS HERE" if dist < 200 else "When one that can not see ahead, should turn back now"
            pulse = (math.sin(pygame.time.get_ticks() * 0.02) + 1) / 2
            clr = (int(100 + 155 * pulse), 0, 0) if dist < 200 or self.fog_timer > 3 else (100, 100, 100)
            font = self.font_warn if dist < 200 else self.font_warn_sm
            w_txt = font.render(msg, True, clr)
            self.display.blit(w_txt, (600 - w_txt.get_width() // 2, 640))

        # 5. HUD
        self.draw_hud()

        # 6. Post-processing
        if self.relief_timer > 0:
            rs = pygame.Surface((1200, 720), pygame.SRCALPHA)
            rs.fill((255, 255, 255, int(self.relief_timer / 30 * 180)))
            self.display.blit(rs, (0, 0))
            self.relief_timer -= 1

        if 0 < self.player.health <= 20:
            v = self.vignette_surf.copy()
            v.set_alpha(int(((math.sin(pygame.time.get_ticks() * 0.02) + 1) / 2) * 200))
            self.display.blit(v, (0, 0))

        if self.wave_transition:
            m = "BOSS INCOMING!" if self.current_wave == 4 else f"WAVE {self.current_wave} CLEARED"
            t = self.font_lg.render(m, True, "yellow")
            t.set_alpha(int(155 + 100 * math.sin(pygame.time.get_ticks() * 0.01)))
            self.display.blit(t, (600 - t.get_width() // 2, 300))

        if self.state != "PLAYING":
            self.draw_overlays()
        pygame.display.flip()

    def draw_hud(self):
        hp_r = self.player.health / 100
        pygame.draw.rect(self.display, "red", (20, 20, 200, 20))
        pygame.draw.rect(self.display, (0, 200, 50), (20, 20, 200 * hp_r, 20))
        pygame.draw.rect(self.display, "white", (20, 20, 200, 20), 2)

        sh_r = self.player.shield / 100
        pygame.draw.rect(self.display, (0, 0, 50), (20, 45, 200, 15))
        pygame.draw.rect(self.display, (0, 150, 255), (20, 45, 200 * sh_r, 15))
        pygame.draw.rect(self.display, "white", (20, 45, 200, 15), 1)

        xp_n = self.upgrade_costs[min(self.upgrade_level, 5)]
        xp_r = min(1.0, self.player.xp / xp_n)
        pygame.draw.rect(self.display, (0, 30, 30), (20, 65, 200, 10))
        pygame.draw.rect(self.display, (0, 255, 255), (20, 65, 200 * xp_r, 10))

        wp_info = (f"UZI: {self.uzi_ammo}/30" if not self.is_reloading else "RELOADING...") if self.current_weapon == "uzi" else "PISTOL: INF"
        hud_f = self.font_sm.render(f"WAVE: {self.current_wave} | {wp_info}", True, "white")
        self.display.blit(hud_f, (20, 80))

    
        for i in range(self.max_bombs):
            cx = 20 + i * 22
            if i < self.bomb_count:
                color = (255, 140, 0) if self.bomb_cooldown <= 0 else (120, 70, 0)
            else:
                color = (60, 60, 60)
            pygame.draw.circle(self.display, color, (cx, 108), 8)
            pygame.draw.circle(self.display, "white", (cx, 108), 8, 1)

        # Cooldown bar under bombs
        if self.bomb_cooldown > 0:
            cd_r = 1.0 - (self.bomb_cooldown / self.bomb_cooldown_max)
            pygame.draw.rect(self.display, (60, 30, 0),   (20, 120, self.max_bombs * 22, 4))
            pygame.draw.rect(self.display, (255, 140, 0), (20, 120, int(self.max_bombs * 22 * cd_r), 4))

        bomb_label = self.font_sm.render(f"BOMBS [Q]", True, (200, 120, 0))
        self.display.blit(bomb_label, (20 + self.max_bombs * 22 + 6, 100))

    def spawn_wave_enemy(self):
        limit = self.map_limit
        side = random.choice(['top', 'bottom', 'left', 'right'])
        pos = {
            'top': (random.randint(0, limit), -100),
            'bottom': (random.randint(0, limit), limit + 100),
            'left': (-100, random.randint(0, limit)),
            'right': (limit + 100, random.randint(0, limit))
        }[side]

        if self.current_wave >= 5:
            boss_exists = any(getattr(e, 'is_boss', False) for e in self.enemy_sprites)
            if not boss_exists:
                b = Enemy("skeleton", (limit // 2, limit // 2), [self.all_sprites, self.enemy_sprites], self.player,
                          boss=True)
                b.is_boss = True
            else:
                Enemy("bat", pos, [self.all_sprites, self.enemy_sprites], self.player)
        else:
            Enemy(random.choice(["bat", "skeleton", "blob"]), pos, [self.all_sprites, self.enemy_sprites], self.player)

    def draw_overlays(self):
        ov = pygame.Surface((1200, 720), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 180))
        self.display.blit(ov, (0, 0))

        if self.state == "DEATH_SCREEN":
            self.display.fill((10, 10, 15))
            if self.death_timer < 2.5:
                st = pygame.Surface((100, 160), pygame.SRCALPHA)
                pygame.draw.ellipse(st, (0, 0, 0, 230), (0, 0, 100, 160))
                pygame.draw.circle(st, (180, 0, 0), (30, 40), 8)
                pygame.draw.circle(st, (180, 0, 0), (70, 40), 8)
                self.display.blit(st, (550, 280))
                for _ in range(1500):
                    self.static_surf.set_at((random.randint(0, 299), random.randint(0, 199)),
                                           random.choice([(150, 150, 150), (0, 0, 0)]))
                self.display.blit(pygame.transform.scale(self.static_surf, (1200, 720)), (0, 0))
                lt = self.font_death.render("S I G N A L  L O S T", True, (200, 0, 0))
                self.display.blit(lt, (600 - lt.get_width() // 2, 550))
            else:
                self.draw_button("RESTART", 450)
                self.draw_button("QUIT", 550)

        elif self.state == "VICTORY_SCREEN":
            self.display.fill((10, 30, 20))
            t = self.font_xl.render("BOSS DEFEATED", True, "gold")
            self.display.blit(t, (600 - t.get_width() // 2, 140))
            sub = self.font_body.render("The fog grows thicker. Something else stirs.", True, (180, 220, 180))
            self.display.blit(sub, (600 - sub.get_width() // 2, 240))
            self._upgrade_rects["victory_continue"] = self.draw_button("CONTINUE TO WAVE 6", 340)
            self._upgrade_rects["victory_quit"]     = self.draw_button("QUIT", 430)

        elif self.state == "MISSION_COMPLETE":
            # Fade-in dark green background
            elapsed = (pygame.time.get_ticks() - self.mission_complete_timer) / 1000
            fade = min(255, int(elapsed * 120))
            self.display.fill((5, 20, 10))

            # Animated title pulse
            pulse = (math.sin(pygame.time.get_ticks() * 0.002) + 1) / 2
            title_color = (int(180 + 75 * pulse), int(200 + 55 * pulse), int(100 + 50 * pulse))
            title = self.font_xl.render("MISSION COMPLETE", True, title_color)
            title.set_alpha(fade)
            self.display.blit(title, (600 - title.get_width() // 2, 120))

            # Stats
            if elapsed > 1.0:
                stats = [
                    f"Waves survived:  6",
                    f"Total XP gained: {self.total_xp_gained}",
                    f"Health remaining: {max(0, int(self.player.health))}",
                ]
                for i, line in enumerate(stats):
                    alpha = min(255, int((elapsed - 1.0 - i * 0.3) * 200))
                    if alpha <= 0:
                        continue
                    s = self.font_body.render(line, True, (160, 220, 160))
                    s.set_alpha(alpha)
                    self.display.blit(s, (600 - s.get_width() // 2, 260 + i * 48))

    
            if elapsed > 2.5:
                msg = self.font_warn_sm.render("You escaped the fog. For now.", True, (100, 140, 100))
                msg.set_alpha(min(255, int((elapsed - 2.5) * 180)))
                self.display.blit(msg, (600 - msg.get_width() // 2, 430))

            
            if elapsed > 3.0:
                self._upgrade_rects["mc_restart"] = self.draw_button("PLAY AGAIN", 510)
                self._upgrade_rects["mc_quit"]    = self.draw_button("QUIT", 580)

        elif self.state == "UPGRADE_MENU":
            cost = self.upgrade_costs[min(self.upgrade_level, 5)]
            title = self.font_lg.render("UPGRADES  [E to close]", True, "white")
            self.display.blit(title, (600 - title.get_width() // 2, 100))

            self._upgrade_rects["gun"] = self.draw_button(
                f"Upgrade Gun  Lv{self.gun_lv + 1}  ({cost} XP)",
                210, self.player.xp >= cost and self.gun_lv < len(self.gun_damages) - 1)
            gun_desc = self.font_sm.render(
                f"Damage: {self.gun_damages[self.gun_lv]} → {self.gun_damages[min(self.gun_lv+1, len(self.gun_damages)-1)]}",
                True, (180, 220, 180))
            self.display.blit(gun_desc, (600 - gun_desc.get_width() // 2, 265))

            self._upgrade_rects["bomb"] = self.draw_button(
                f"Upgrade Bomb  Lv{self.bomb_lv + 1}  ({cost} XP)",
                320, self.player.xp >= cost and self.bomb_lv < len(self.bomb_damages) - 1)
            bomb_desc = self.font_sm.render(
                f"Damage: {self.bomb_damages[self.bomb_lv]} → {self.bomb_damages[min(self.bomb_lv+1, len(self.bomb_damages)-1)]}  |  Radius: {180 + self.bomb_lv*30} → {180 + (self.bomb_lv+1)*30}",
                True, (255, 200, 120))
            self.display.blit(bomb_desc, (600 - bomb_desc.get_width() // 2, 375))

            self._upgrade_rects["uzi"] = self.draw_button(
                f"Unlock UZI  (50 XP)",
                430, self.player.xp >= 50 and not self.uzi_unlocked)

            self._upgrade_rects["buy_bombs"] = self.draw_button(
                f"Buy 3 Bombs  (400 XP)",
                490, self.player.xp >= 400 and self.bomb_count < self.max_bombs)
            bombs_desc = self.font_sm.render(
                f"Bombs: {self.bomb_count}/{self.max_bombs}",
                True, (255, 200, 120))
            self.display.blit(bombs_desc, (600 - bombs_desc.get_width() // 2, 545))

            xp_label = self.font_sm.render(f"XP: {self.player.xp}", True, (0, 255, 255))
            self.display.blit(xp_label, (600 - xp_label.get_width() // 2, 570))

    def draw_button(self, text, y, active=True):
        mouse = pygame.mouse.get_pos()
        sb = self.font_md.render(text, True, "white")
        rect = pygame.Rect(600 - sb.get_width() // 2, y, sb.get_width(), sb.get_height())
        h = rect.collidepoint(mouse)
        color = "yellow" if h and active else "white" if active else "gray"
        s = self.font_md.render(text, True, color)
        self.display.blit(s, (600 - s.get_width() // 2, y))
        # Fix: return the rect so callers can store it for click detection
        return rect

    def run(self):
        while self.running:
            self.update()
            self.draw()


if __name__ == "__main__":
    Game().run()
