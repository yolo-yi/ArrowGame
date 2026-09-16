"""一箭又一箭：程序入口与游戏主循环。"""

import pygame

from game_logic import (
    can_fly_out,
    can_polyline_fly_out,
    create_flying_arrow,
    create_flying_polyline,
    find_flyable_grid_arrow,
    find_flyable_polyline_arrow,
    get_cell_from_mouse,
    get_polyline_arrow_from_mouse,
    reset_level,
    update_flying_arrow,
    update_flying_polyline,
)
from levels import EMPTY, LEVELS, get_level_dimensions, is_polyline_level
from save_data import load_highest_unlocked, save_highest_unlocked
from settings import (
    ARROW_COLOR,
    BLOCKED_COLOR,
    FPS,
    HINT_SCORE_PENALTY,
    LEVEL_TIME_LIMITS,
    MISTAKE_SCORE_PENALTY,
    SCORE_PER_ARROW,
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
    ai_solving = False
    ai_next_move_at = 0
    ai_step_count = 0
    hinted_cell = None
    hint_until = 0
    score = 0
    time_left = float(LEVEL_TIME_LIMITS[level_index])
    failure_reason = "失误机会已经用完，再试一次吧"

    start_button = pygame.Rect(230, 510, 300, 64)
    level_select_button = pygame.Rect(245, 590, 270, 54)
    # 基础关卡使用上方三列；挑战关卡在下方居中排列。
    level_buttons = [
        pygame.Rect(
            90 + index * 200 if index < 3 else 190 + (index - 3) * 200,
            225 if index < 3 else 405,
            185,
            135,
        )
        for index in range(len(LEVELS))
    ]
    select_back_button = pygame.Rect(245, 565, 270, 54)
    ai_solve_button = pygame.Rect(42, 663, 150, 58)
    hint_button = pygame.Rect(202, 663, 72, 58)
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
            if hinted_cell is not None and pygame.time.get_ticks() >= hint_until:
                hinted_cell = None

            time_left = max(0.0, time_left - delta_time)
            if time_left <= 0:
                if is_polyline_level(level_index):
                    remaining_at_timeout = len(board)
                else:
                    remaining_at_timeout = sum(
                        cell != EMPTY for row in board for cell in row
                    )
                if remaining_at_timeout > 0:
                    ai_solving = False
                    failure_reason = "倒计时结束，本关未能通关"
                    game_state = STATE_GAME_OVER

            was_flying = flying_arrow is not None
            if is_polyline_level(level_index):
                rows, cols = get_level_dimensions(level_index)
                flying_arrow = update_flying_polyline(
                    flying_arrow, delta_time, rows, cols
                )
            else:
                flying_arrow = update_flying_arrow(
                    flying_arrow, delta_time, len(board), len(board[0])
                )
            if was_flying and flying_arrow is None:
                if is_polyline_level(level_index):
                    remaining = len(board)
                else:
                    remaining = sum(
                        cell != EMPTY for row in board for cell in row
                    )
                if remaining == 0:
                    ai_solving = False
                    new_highest = min(level_index + 1, len(LEVELS) - 1)
                    if new_highest > highest_unlocked:
                        highest_unlocked = new_highest
                        save_highest_unlocked(highest_unlocked)
                    game_state = STATE_LEVEL_COMPLETE
                else:
                    if ai_solving:
                        message = "AI 正在分析下一步……"
                        ai_next_move_at = pygame.time.get_ticks() + 220
                    else:
                        message = "成功飞出！"
                    message_color = ARROW_COLOR

            if (
                game_state == STATE_PLAYING
                and mistakes_left <= 0
                and pygame.time.get_ticks() >= blocked_until
            ):
                ai_solving = False
                failure_reason = "失误机会已经用完，再试一次吧"
                game_state = STATE_GAME_OVER

            # 自动求解每次只操作一支箭头，等待飞行动画结束后再继续。
            if (
                game_state == STATE_PLAYING
                and ai_solving
                and flying_arrow is None
                and pygame.time.get_ticks() >= ai_next_move_at
            ):
                if is_polyline_level(level_index):
                    rows, cols = get_level_dimensions(level_index)
                    arrow_index = find_flyable_polyline_arrow(
                        board, rows, cols
                    )
                    if arrow_index is None:
                        ai_solving = False
                        message = "AI 未找到可安全飞出的箭头"
                        message_color = BLOCKED_COLOR
                    else:
                        flying_arrow = create_flying_polyline(board, arrow_index)
                else:
                    cell = find_flyable_grid_arrow(board)
                    if cell is None:
                        ai_solving = False
                        message = "AI 未找到可安全飞出的箭头"
                        message_color = BLOCKED_COLOR
                    else:
                        row, col = cell
                        direction = board[row][col]
                        board[row][col] = EMPTY
                        flying_arrow = create_flying_arrow(
                            row, col, direction, len(board), len(board[0])
                        )

                if flying_arrow is not None:
                    ai_step_count += 1
                    score += SCORE_PER_ARROW
                    blocked_cell = None
                    hinted_cell = None
                    message = (
                        f"AI 正在执行第 {ai_step_count} 步  +{SCORE_PER_ARROW}分"
                    )
                    message_color = ARROW_COLOR

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
                    ai_solving = False
                    hinted_cell = None

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
                    ai_solving = False
                    ai_step_count = 0
                    hinted_cell = None
                    score = 0
                    time_left = float(LEVEL_TIME_LIMITS[level_index])
                    failure_reason = "失误机会已经用完，再试一次吧"
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
                            ai_solving = False
                            ai_step_count = 0
                            hinted_cell = None
                            score = 0
                            time_left = float(LEVEL_TIME_LIMITS[level_index])
                            failure_reason = "失误机会已经用完，再试一次吧"
                            game_state = STATE_PLAYING
                            break
                continue

            if game_state in (STATE_LEVEL_COMPLETE, STATE_GAME_OVER):
                if home_button.collidepoint(event.pos):
                    game_state = STATE_START
                    settings_open = False
                    ai_solving = False
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
                    ai_solving = False
                    ai_step_count = 0
                    hinted_cell = None
                    score = 0
                    time_left = float(LEVEL_TIME_LIMITS[level_index])
                    failure_reason = "失误机会已经用完，再试一次吧"
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
                    ai_solving = False
                    ai_step_count = 0
                    hinted_cell = None
                    score = 0
                    time_left = float(LEVEL_TIME_LIMITS[level_index])
                    failure_reason = "失误机会已经用完，再试一次吧"
                elif settings_home_button.collidepoint(event.pos):
                    game_state = STATE_START
                    settings_open = False
                    ai_solving = False
                continue

            if settings_button.collidepoint(event.pos):
                settings_open = True
                continue

            if ai_solve_button.collidepoint(event.pos) and mistakes_left > 0:
                ai_solving = not ai_solving
                hinted_cell = None
                if ai_solving:
                    ai_step_count = 0
                    ai_next_move_at = pygame.time.get_ticks() + 180
                    message = "AI 自动求解已启动"
                    message_color = ARROW_COLOR
                else:
                    message = "AI 自动求解已停止"
                    message_color = TEXT_COLOR
                continue

            if hint_button.collidepoint(event.pos) and mistakes_left > 0:
                if ai_solving:
                    message = "请先停止 AI 自动求解"
                    message_color = TEXT_COLOR
                elif flying_arrow is not None:
                    message = "请等待当前箭头飞出"
                    message_color = TEXT_COLOR
                else:
                    if is_polyline_level(level_index):
                        rows, cols = get_level_dimensions(level_index)
                        hinted_cell = find_flyable_polyline_arrow(
                            board, rows, cols
                        )
                    else:
                        hinted_cell = find_flyable_grid_arrow(board)

                    if hinted_cell is None:
                        message = "当前没有可安全飞出的箭头"
                        message_color = BLOCKED_COLOR
                    else:
                        hint_until = pygame.time.get_ticks() + 3500
                        score = max(0, score - HINT_SCORE_PENALTY)
                        message = (
                            "提示：金色箭头可以安全飞出  "
                            f"-{HINT_SCORE_PENALTY}分"
                        )
                        message_color = ARROW_COLOR
                continue

            # 飞行动画播放期间暂时不接受其他棋盘点击。
            if flying_arrow is not None or mistakes_left <= 0 or ai_solving:
                continue

            if is_polyline_level(level_index):
                rows, cols = get_level_dimensions(level_index)
                arrow_index = get_polyline_arrow_from_mouse(
                    board, event.pos, rows, cols
                )
                if arrow_index is None:
                    continue
                hinted_cell = None

                if can_polyline_fly_out(
                    board, arrow_index, rows, cols
                ):
                    flying_arrow = create_flying_polyline(board, arrow_index)
                    score += SCORE_PER_ARROW
                    blocked_cell = None
                    message = f"整条折线正在飞出  +{SCORE_PER_ARROW}分"
                    message_color = ARROW_COLOR
                else:
                    mistakes_left -= 1
                    score = max(0, score - MISTAKE_SCORE_PENALTY)
                    blocked_cell = arrow_index
                    blocked_until = pygame.time.get_ticks() + 450
                    message = (
                        "箭头前方被其他折线阻挡！"
                        f"-{MISTAKE_SCORE_PENALTY}分"
                    )
                    message_color = BLOCKED_COLOR
            else:
                cell = get_cell_from_mouse(event.pos, len(board), len(board[0]))
                if cell is None:
                    continue

                row, col = cell
                if board[row][col] == EMPTY:
                    continue
                hinted_cell = None

                if can_fly_out(board, row, col):
                    direction = board[row][col]
                    board[row][col] = EMPTY
                    blocked_cell = None
                    flying_arrow = create_flying_arrow(
                        row, col, direction, len(board), len(board[0])
                    )
                    score += SCORE_PER_ARROW
                    message = f"箭头正在飞出  +{SCORE_PER_ARROW}分"
                    message_color = ARROW_COLOR
                else:
                    mistakes_left -= 1
                    score = max(0, score - MISTAKE_SCORE_PENALTY)
                    blocked_cell = (row, col)
                    blocked_until = pygame.time.get_ticks() + 450
                    message = (
                        f"前方有箭头阻挡！-{MISTAKE_SCORE_PENALTY}分"
                    )
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
                score,
                time_left,
                message,
                message_color,
                ai_solve_button,
                ai_solving,
                hint_button,
                hinted_cell,
                hint_until,
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
                score,
                failure_reason,
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
                score,
                failure_reason,
                primary_button,
                home_button,
            )

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
