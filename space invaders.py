import random
import sys
from array import array

try:
    import pygame  # type: ignore[import-not-found]
except ImportError as exc:
    raise RuntimeError("Pygame is required. Install it with: pip install pygame") from exc


WIDTH = 900
HEIGHT = 650
FPS = 30

DIFFICULTIES = {
	"easy": {"fire_chance": 0.25, "invader_hits": 1},
	"medium": {"fire_chance": 0.55, "invader_hits": 1},
	"hard": {"fire_chance": 0.8, "invader_hits": 2},
}

BLACK = (8, 12, 24)
GREEN = (92, 255, 110)
DIM_GREEN = (34, 112, 48)
WHITE = (205, 255, 210)
INVADER_COLORS = (
	(50, 205, 50),
	(255, 255, 0),
	(160, 32, 240),
	(255, 165, 0),
)

INVADER_SPRITES = (
	(
		"00111100",
		"01111110",
		"11011011",
		"11111111",
		"01100110",
		"11000011",
		"00011000",
	),
	(
		"00011000",
		"00111100",
		"01111110",
		"11011011",
		"11111111",
		"00100100",
		"01000010",
	),
	(
		"00011000",
		"00111100",
		"01111110",
		"11011011",
		"11111111",
		"01011010",
		"10100101",
	),
)
PLAYER_SPRITE = (
	"00000100000",
	"00001110000",
	"01111111110",
	"11111111111",
	"11100000111",
)


def draw_pixel_sprite(screen, sprite, position, scale, color):
	for row, line in enumerate(sprite):
		for column, pixel in enumerate(line):
			if pixel == "1":
				pygame.draw.rect(screen, color, (position[0] + column * scale, position[1] + row * scale, scale, scale))


def create_tone(start_frequency, duration, volume, end_frequency=None, waveform="square"):
	if not pygame.mixer.get_init():
		return None
	end_frequency = end_frequency or start_frequency
	sample_rate = pygame.mixer.get_init()[0]
	sample_count = round(sample_rate * duration)
	samples = array("h")
	phase = 0.0
	for sample_index in range(sample_count):
		progress = sample_index / max(1, sample_count - 1)
		frequency = start_frequency + (end_frequency - start_frequency) * progress
		envelope = (1 - progress) ** 1.5
		phase = (phase + frequency / sample_rate) % 1
		if waveform == "noise":
			sample = random.uniform(-1, 1)
		else:
			sample = 1 if phase < 0.5 else -1
		samples.append(round(sample * envelope * volume * 32767))
	return pygame.mixer.Sound(buffer=samples.tobytes())


def play_sound(sound):
	if sound:
		sound.play()


class Player:
	def __init__(self):
		self.rect = pygame.Rect(WIDTH // 2 - 22, HEIGHT - 62, 44, 20)
		self.speed = 420
		self.cooldown = 0

	def update(self, keys, dt):
		direction = int(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - int(
			keys[pygame.K_LEFT] or keys[pygame.K_a]
		)
		self.rect.x += round(direction * self.speed * dt)
		self.rect.clamp_ip(pygame.Rect(18, 0, WIDTH - 36, HEIGHT))
		self.cooldown = max(0, self.cooldown - dt)

	def shoot(self):
		if self.cooldown > 0:
			return None
		self.cooldown = 0.19
		return pygame.Rect(self.rect.centerx - 3, self.rect.top - 14, 6, 16)

	def draw(self, screen):
		draw_pixel_sprite(screen, PLAYER_SPRITE, self.rect.topleft, 4, GREEN)


class Invader:
	def __init__(self, x, y, row, hits_to_kill):
		self.rect = pygame.Rect(x, y, 32, 28)
		self.row = row
		self.sprite = INVADER_SPRITES[row % len(INVADER_SPRITES)]
		self.color = INVADER_COLORS[row % len(INVADER_COLORS)]
		self.hits_remaining = hits_to_kill

	def draw(self, screen):
		draw_pixel_sprite(screen, self.sprite, self.rect.topleft, 4, self.color)


class Bunker:
	def __init__(self, x, y):
		self.rect = pygame.Rect(x, y, 60, 25)
		self.cells = {
			(row, column)
			for row in range(5)
			for column in range(12)
			if row < 3 or column in {0, 1, 10, 11} or row == 3 and 3 <= column <= 8
		}

	def damage(self, laser, moving_up):
		hits = []
		for row, column in self.cells:
			cell = pygame.Rect(self.rect.x + column * 5, self.rect.y + row * 5, 5, 5)
			if laser.colliderect(cell):
				hits.append((row, column))
		if not hits:
			return False
		row, column = max(hits) if moving_up else min(hits)
		self.cells.remove((row, column))
		return True

	def draw(self, screen):
		for row, column in self.cells:
			pygame.draw.rect(screen, GREEN, (self.rect.x + column * 5, self.rect.y + row * 5, 5, 5))


def create_invaders(level, hits_to_kill):
	invaders = []
	rows = min(4 + (level - 1) // 2, 6)
	for row in range(rows):
		for column in range(10):
			invaders.append(Invader(105 + column * 66, 75 + row * 44, row % 4, hits_to_kill))
	return invaders


def new_game(difficulty_name):
	difficulty = DIFFICULTIES[difficulty_name]
	return (
		Player(),
		[],
		[],
		create_invaders(1, difficulty["invader_hits"]),
		0,
		3,
		1,
		1,
		0,
		0.48,
		[Bunker(x, HEIGHT - 150) for x in (145, 345, 545, 745)],
	)


def draw_text(screen, font, text, position, color=WHITE, center=False):
	surface = font.render(text, True, color)
	rect = surface.get_rect(center=position) if center else surface.get_rect(topleft=position)
	screen.blit(surface, rect)


def main():
	pygame.mixer.pre_init(44100, -16, 1)
	pygame.init()
	pygame.display.set_caption("Space Invaders")
	screen = pygame.display.set_mode((WIDTH, HEIGHT))
	clock = pygame.time.Clock()
	laser_sound = create_tone(1500, 0.1, 0.16, 180, "square")
	enemy_kill_sound = create_tone(0, 0.16, 0.28, waveform="noise")
	player_death_sound = create_tone(260, 0.55, 0.3, 45, "square")
	title_font = pygame.font.Font(None, 58)
	ui_font = pygame.font.Font(None, 28)
	small_font = pygame.font.Font(None, 22)

	difficulty_name = "medium"
	player, bullets, enemy_bullets, invaders, score, lives, level, enemy_direction, enemy_timer, enemy_step, bunkers = new_game(difficulty_name)
	state = "menu"
	difficulty_buttons = [
		("easy", pygame.Rect(205, 300, 150, 80)),
		("medium", pygame.Rect(375, 300, 150, 80)),
		("hard", pygame.Rect(545, 300, 150, 80)),
	]

	running = True
	while running:
		dt = clock.tick(FPS) / 1000
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				running = False
			elif event.type == pygame.MOUSEBUTTONDOWN and state == "menu" and event.button == 1:
				for selected_difficulty, button in difficulty_buttons:
					if button.collidepoint(event.pos):
						difficulty_name = selected_difficulty
						player, bullets, enemy_bullets, invaders, score, lives, level, enemy_direction, enemy_timer, enemy_step, bunkers = new_game(difficulty_name)
						state = "playing"
						break
			elif event.type == pygame.KEYDOWN:
				if event.key == pygame.K_ESCAPE:
					running = False
				elif state == "menu" and event.key in {pygame.K_1, pygame.K_2, pygame.K_3}:
					difficulty_name = {pygame.K_1: "easy", pygame.K_2: "medium", pygame.K_3: "hard"}[event.key]
					player, bullets, enemy_bullets, invaders, score, lives, level, enemy_direction, enemy_timer, enemy_step, bunkers = new_game(difficulty_name)
					state = "playing"
				elif event.key == pygame.K_m:
					state = "menu"
				elif event.key == pygame.K_SPACE and state == "playing":
					bullet = player.shoot()
					if bullet:
						bullets.append(bullet)
						play_sound(laser_sound)
				elif event.key == pygame.K_r and state in {"game_over", "won"}:
					player, bullets, enemy_bullets, invaders, score, lives, level, enemy_direction, enemy_timer, enemy_step, bunkers = new_game(difficulty_name)
					state = "playing"

		if state == "playing":
			keys = pygame.key.get_pressed()
			player.update(keys, dt)
			for bullet in bullets:
				bullet.y -= round(650 * dt)
			bullets = [bullet for bullet in bullets if bullet.bottom > 0]

			enemy_timer += dt
			if enemy_timer >= enemy_step:
				enemy_timer = 0
				edge_hit = any(
					(invader.rect.right >= WIDTH - 25 and enemy_direction > 0)
					or (invader.rect.left <= 25 and enemy_direction < 0)
					for invader in invaders
				)
				if edge_hit:
					enemy_direction *= -1
					for invader in invaders:
						invader.rect.y += 20
				else:
					for invader in invaders:
						invader.rect.x += enemy_direction * 14
				if invaders and random.random() < DIFFICULTIES[difficulty_name]["fire_chance"]:
					shooter = random.choice(invaders)
					enemy_bullets.append(
						(pygame.Rect(shooter.rect.centerx - 3, shooter.rect.bottom, 6, 14), shooter.color)
					)

			for bullet, color in enemy_bullets:
				bullet.y += round(260 * dt)
			enemy_bullets = [(bullet, color) for bullet, color in enemy_bullets if bullet.top < HEIGHT]

			for bullet in bullets[:]:
				hit_bunker = next((bunker for bunker in bunkers if bunker.damage(bullet, True)), None)
				if hit_bunker:
					bullets.remove(bullet)
					continue
				hit = next((invader for invader in invaders if bullet.colliderect(invader.rect)), None)
				if hit:
					bullets.remove(bullet)
					hit.hits_remaining -= 1
					if hit.hits_remaining <= 0:
						invaders.remove(hit)
						score += (4 - hit.row) * 10
						play_sound(enemy_kill_sound)

			for bullet, color in enemy_bullets[:]:
				hit_bunker = next((bunker for bunker in bunkers if bunker.damage(bullet, False)), None)
				if hit_bunker:
					enemy_bullets.remove((bullet, color))
					continue
				if bullet.colliderect(player.rect):
					enemy_bullets.remove((bullet, color))
					lives -= 1
					player.rect.centerx = WIDTH // 2
					if lives <= 0:
						state = "game_over"
						play_sound(player_death_sound)

			if any(invader.rect.bottom >= player.rect.top for invader in invaders):
				state = "game_over"
				play_sound(player_death_sound)
			elif not invaders:
				level += 1
				if level > 5:
					state = "won"
				else:
					invaders = create_invaders(level, DIFFICULTIES[difficulty_name]["invader_hits"])
					enemy_step = max(0.16, enemy_step - 0.06)

		screen.fill(BLACK)
		for x in range(0, WIDTH, 45):
			pygame.draw.rect(screen, DIM_GREEN, (x + 10, 42 + (x * 7) % 80, 2, 2))
		for y in range(0, HEIGHT, 4):
			pygame.draw.line(screen, (10, 24, 14), (0, y), (WIDTH, y))
		pygame.draw.line(screen, GREEN, (18, HEIGHT - 28), (WIDTH - 18, HEIGHT - 28), 2)
		draw_text(screen, small_font, "SCORE", (24, 12), WHITE)
		draw_text(screen, ui_font, f"{score:05d}", (43, 38), GREEN)
		draw_text(screen, small_font, "HI-SCORE", (WIDTH // 2 - 45, 12), WHITE)
		draw_text(screen, ui_font, "00000", (WIDTH // 2 - 35, 38), GREEN)
		draw_text(screen, small_font, "LIVES", (WIDTH - 106, 12), WHITE)
		draw_text(screen, ui_font, str(lives), (WIDTH - 96, 38), GREEN)

		for invader in invaders:
			invader.draw(screen)
		for bunker in bunkers:
			bunker.draw(screen)
		for bullet in bullets:
			pygame.draw.rect(screen, WHITE, bullet)
		for bullet, color in enemy_bullets:
			pygame.draw.rect(screen, color, bullet)
		player.draw(screen)

		if state == "menu":
			pygame.draw.rect(screen, BLACK, (170, 150, WIDTH - 340, 350))
			pygame.draw.rect(screen, GREEN, (170, 150, WIDTH - 340, 350), 3)
			draw_text(screen, title_font, "SPACE INVADERS", (WIDTH // 2, 205), GREEN, center=True)
			draw_text(screen, ui_font, "SELECT DIFFICULTY", (WIDTH // 2, 265), WHITE, center=True)
			for selected_difficulty, button in difficulty_buttons:
				pygame.draw.rect(screen, GREEN, button, 3)
				draw_text(screen, ui_font, selected_difficulty.upper(), button.center, GREEN, center=True)
			draw_text(screen, small_font, "Press Esc to quit", (WIDTH // 2, 435), WHITE, center=True)
		elif state in {"game_over", "won"}:
			pygame.draw.rect(screen, BLACK, (190, 225, WIDTH - 380, 190))
			pygame.draw.rect(screen, GREEN, (190, 225, WIDTH - 380, 190), 3)
			heading = "YOU WIN" if state == "won" else "GAME OVER"
			color = GREEN
			draw_text(screen, title_font, heading, (WIDTH // 2, 275), color, center=True)
			draw_text(screen, ui_font, f"Final score: {score}", (WIDTH // 2, 325), WHITE, center=True)
			draw_text(screen, small_font, "Press R to play again  |  M for menu  |  Esc to quit", (WIDTH // 2, 370), WHITE, center=True)
		else:
			draw_text(screen, small_font, f"{difficulty_name.upper()}    A/D OR ARROWS: MOVE    SPACE: FIRE    M: MENU    ESC: QUIT", (WIDTH // 2, HEIGHT - 19), WHITE, center=True)

		pygame.display.flip()

	pygame.quit()
	sys.exit()


if __name__ == "__main__":
	main()

input("\nPress Enter to exit...")
