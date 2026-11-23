"""Small modal confirmation displayed inside the current Pygame window."""

def confirm(screen, clock, title='Thoát cửa sổ?', message='Bạn có chắc muốn thoát không?'):
    import pygame
    snapshot = screen.copy()
    w, h = screen.get_size()
    panel = pygame.Rect(0, 0, min(480, w - 32), 198)
    panel.center = (w // 2, h // 2)
    yes = pygame.Rect(panel.x + 60, panel.bottom - 64, 145, 43)
    no = pygame.Rect(panel.right - 205, panel.bottom - 64, 145, 43)
    title_font = pygame.font.SysFont('segoeui,arial', 27, bold=True)
    body_font = pygame.font.SysFont('segoeui,arial', 19)
    button_font = pygame.font.SysFont('segoeui,arial', 19, bold=True)
    while True:
        screen.blit(snapshot, (0, 0))
        veil = pygame.Surface((w, h), pygame.SRCALPHA)
        veil.fill((12, 25, 40, 170))
        screen.blit(veil, (0, 0))
        pygame.draw.rect(screen, 'white', panel, border_radius=14)
        pygame.draw.rect(screen, (196, 210, 224), panel, 1, border_radius=14)
        for value, font, ypos in ((title, title_font, panel.y + 25), (message, body_font, panel.y + 81)):
            surface = font.render(value, True, (34, 51, 78))
            screen.blit(surface, surface.get_rect(centerx=panel.centerx, top=ypos))
        for rect, label, fill, foreground in (
            (yes, 'Thoát', (34, 143, 105), 'white'),
            (no, 'Ở lại', (229, 237, 245), (34, 51, 78)),
        ):
            pygame.draw.rect(screen, fill, rect, border_radius=9)
            label_surface = button_font.render(label, True, foreground)
            screen.blit(label_surface, label_surface.get_rect(center=rect.center))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return True
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_n):
                    return False
                if event.key in (pygame.K_RETURN, pygame.K_y):
                    return True
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if yes.collidepoint(event.pos):
                    return True
                if no.collidepoint(event.pos):
                    return False
        clock.tick(40)
