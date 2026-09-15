"""一箭又一箭：程序入口与游戏主循环。"""

import pygame

from game_logic import (
    can_fly_out,
    create_flying_arrow,
    get_cell_from_mouse,
    reset_level,
    update_flying_arrow,
)
from levels import EMPTY, LEVELS
from save_data import load_highest_unlocked, save_highest_unlocked
from settings import (
    ARROW_COLOR,
    BLOCKED_COLOR,
    FPS,
    STATE_GAME_OVER,
    STATE_LEVEL_COMPLETE,
    STATE_LEVEL_SELECT,
    STATE_PLAYING,
    STATE_START,
    TEXT_COLOR,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from ui import (
    create_background,
    draw_game_screen,
    draw_level_select_screen,
    draw_result_screen,
    draw_start_screen,
)


def create_fonts():
    """创建界面统一使用的字体集合。"""
    return {
        "title": pygame.font.SysFont("microsoftyahei", 47, bold=True),
        "result": pygame.font.SysFont("microsoftyahei", 38, bold=True),
        "heading": pygame.font.SysFont("microsoftyahei", 27, bold=True),
        "subtitle": pygame.font.SysFont("microsoftyahei", 21),
        "button": pygame.font.SysFont("microsoftyahei", 23, bold=True),
        "small": pygame.font.SysFont("microsoftyahei", 19),
        "tiny": pygame.font.SysFont("microsoftyahei", 17),
    }


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Arrow Game")
    clock = pygame.time.Clock()
    fonts = create_fonts()
    background = create_background()

    level_index = 0
    highest_unlocked = load_highest_unlocked(len(LEVELS))
    game_state = STATE_START
    (
        board,
        mistakes_left,
        message,
        message_color,
        blocked_cell,
        blocked_until,
        flying_arrow,
    ) = reset_level(level_index)
    settings_open = False

    start_button = pygame.Rect(245, 480, 270, 58)
    level_select_button = pygame.Rect(245, 552, 270, 54)
    level_buttons = [
        pygame.Rect(105 + index * 185, 255, 150, 215)
        for index in range(len(LEVELS))
    ]
    select_back_button = pygame.Rect(245, 565, 270, 54)
    settings_button = pygame.Rect(638, 63, 50, 46)
    settings_restart_button = pygame.Rect(255, 340, 250, 56)
    settings_home_button = pygame.Rect(255, 416, 250, 56)
    settings_close_button = pygame.Rect(515, 215, 34, 34)
    primary_button = pygame.Rect(235, 475, 290, 60)
    home_button = pygame.Rect(235, 555, 290, 56)
    running = True

    while running:
        delta_time = clock.tick(FPS) / 1000
        mouse_pos = pygame.mouse.get_pos()

        if game_state == STATE_PLAYING and not settings_open:
            was_flying = flying_arrow is not None
            flying_arrow = update_flying_arrow(
                flying_arrow, delta_time, len(board), len(board[0])
            )
            if was_flying and flying_arrow is None:
                remaining = sum(cell != EMPTY for row in board for cell in row)
                if remaining == 0:
                    new_highest = min(level_index + 1, len(LEVELS) - 1)
                    if new_highest > highest_unlocked:
                        highest_unlocked = new_highest
                        save_highest_unlocked(highest_unlocked)
                    game_state = STATE_LEVEL_COMPLETE
                else:
                    message = "成功飞出！"
                    message_color = ARROW_COLOR

            if mistakes_left <= 0 and pygame.time.get_ticks() >= blocked_until:
                game_state = STATE_GAME_OVER

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if game_state == STATE_PLAYING and settings_open:
                    settings_open = False
                elif game_state == STATE_START:
                    running = False
                else:
                    game_state = STATE_START
                    settings_open = False

            if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
                continue

            if game_state == STATE_START:
                if start_button.collidepoint(event.pos):
                    level_index = 0
                    (
                        board,
                        mistakes_left,
                        message,
                        message_color,
                        blocked_cell,
                        blocked_until,
                        flying_arrow,
                    ) = reset_level(level_index)
                    settings_open = False
                    game_state = STATE_PLAYING
                elif level_select_button.collidepoint(event.pos):
                    game_state = STATE_LEVEL_SELECT
                continue

            if game_state == STATE_LEVEL_SELECT:
                if select_back_button.collidepoint(event.pos):
                    game_state = STATE_START
                else:
                    for index, button in enumerate(level_buttons):
                        if button.collidepoint(event.pos) and index <= highest_unlocked:
                            level_index = index
                            (
                                board,
                                mistakes_left,
                                message,
                                message_color,
                                blocked_cell,
                                blocked_until,
                                flying_arrow,
                            ) = reset_level(level_index)
                            settings_open = False
                            game_state = STATE_PLAYING
                            break
                continue

            if game_state in (STATE_LEVEL_COMPLETE, STATE_GAME_OVER):
                if home_button.collidepoint(event.pos):
                    game_state = STATE_START
                    settings_open = False
                elif primary_button.collidepoint(event.pos):
                    if game_state == STATE_LEVEL_COMPLETE:
                        if level_index + 1 < len(LEVELS):
                            level_index += 1
                        else:
                            level_index = 0
                    (
                        board,
                        mistakes_left,
                        message,
                        message_color,
                        blocked_cell,
                        blocked_until,
                        flying_arrow,
                    ) = reset_level(level_index)
                    settings_open = False
                    game_state = STATE_PLAYING
                continue

            if game_state != STATE_PLAYING:
                continue

            if settings_open:
                if (
                    settings_button.collidepoint(event.pos)
                    or settings_close_button.collidepoint(event.pos)
                ):
                    settings_open = False
                elif settings_restart_button.collidepoint(event.pos):
                    (
                        board,
                        mistakes_left,
                        message,
                        message_color,
                        blocked_cell,
                        blocked_until,
                        flying_arrow,
                    ) = reset_level(level_index)
                    message = "本关已重新开始"
                    settings_open = False
                elif settings_home_button.collidepoint(event.pos):
                    game_state = STATE_START
                    settings_open = False
                continue

            if settings_button.collidepoint(event.pos):
                settings_open = True
                continue

            # 飞行动画播放期间暂时不接受其他棋盘点击。
            if flying_arrow is not None or mistakes_left <= 0:
                continue

            cell = get_cell_from_mouse(event.pos, len(board), len(board[0]))
            if cell is None:
                continue

            row, col = cell
            if board[row][col] == EMPTY:
                continue

            if can_fly_out(board, row, col):
                direction = board[row][col]
                board[row][col] = EMPTY
                blocked_cell = None
                flying_arrow = create_flying_arrow(
                    row, col, direction, len(board), len(board[0])
                )
                message = "箭头正在飞出……"
                message_color = ARROW_COLOR
            else:
                mistakes_left -= 1
                blocked_cell = (row, col)
                blocked_until = pygame.time.get_ticks() + 450
                message = "前方有箭头阻挡！"
                message_color = BLOCKED_COLOR

        screen.blit(background, (0, 0))

        if game_state == STATE_START:
            draw_start_screen(
                screen,
                fonts,
                mouse_pos,
                start_button,
                level_select_button,
            )
        elif game_state == STATE_LEVEL_SELECT:
            draw_level_select_screen(
                screen,
                fonts,
                mouse_pos,
                level_buttons,
                highest_unlocked,
                select_back_button,
            )
        elif game_state == STATE_PLAYING:
            draw_game_screen(
                screen,
                fonts,
                mouse_pos,
                board,
                level_index,
                mistakes_left,
                message,
                message_color,
                settings_button,
                settings_open,
                settings_restart_button,
                settings_home_button,
                settings_close_button,
                blocked_cell,
                blocked_until,
                flying_arrow,
            )
        elif game_state == STATE_LEVEL_COMPLETE:
            draw_result_screen(
                screen,
                fonts,
                mouse_pos,
                True,
                level_index,
                primary_button,
                home_button,
            )
        elif game_state == STATE_GAME_OVER:
            draw_result_screen(
                screen,
                fonts,
                mouse_pos,
                False,
                level_index,
                primary_button,
                home_button,
            )

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
