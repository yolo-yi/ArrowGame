import copy
import math

import pygame

from levels import EMPTY, LEVELS


WINDOW_WIDTH = 760
WINDOW_HEIGHT = 760
FPS = 60
BOARD_AREA_SIZE = 480
MAX_CELL_SIZE = 96
BOARD_TOP = 150

BACKGROUND = (35, 42, 68)
PANEL = (48, 57, 88)
GRID_LINE = (91, 105, 145)
ARROW_COLOR = (91, 214, 190)
BLOCKED_COLOR = (255, 91, 105)
TEXT_COLOR = (245, 247, 255)
BUTTON_COLOR = (79, 96, 145)
BUTTON_HOVER_COLOR = (99, 119, 175)
FLIGHT_SPEED = 520
ACCENT_BLUE = (111, 145, 255)
ACCENT_YELLOW = (255, 202, 92)
SUBTEXT_COLOR = (174, 185, 217)

STATE_START = "start"
STATE_PLAYING = "playing"
STATE_LEVEL_COMPLETE = "level_complete"
STATE_GAME_OVER = "game_over"

DIRECTIONS = {
    "^": (-1, 0),
    "v": (1, 0),
    "<": (0, -1),
    ">": (0, 1),
}


def can_fly_out(board, row, col):
    """判断箭头与对应边界之间是否没有其他箭头。"""
    arrow = board[row][col]
    if arrow == EMPTY:
        return False

    dr, dc = DIRECTIONS[arrow]
    check_row = row + dr
    check_col = col + dc

    while 0 <= check_row < len(board) and 0 <= check_col < len(board[0]):
        if board[check_row][check_col] != EMPTY:
            return False
        check_row += dr
        check_col += dc

    return True


def draw_arrow(surface, center, direction, color, offset=(0, 0)):
    """使用线段和三角形画箭头，不依赖字体中的箭头符号。"""
    cx = center[0] + offset[0]
    cy = center[1] + offset[1]
    length = 48
    head = 15

    vectors = {
        "^": (0, -1),
        "v": (0, 1),
        "<": (-1, 0),
        ">": (1, 0),
    }
    dx, dy = vectors[direction]

    start = (cx - dx * length / 2, cy - dy * length / 2)
    tip = (cx + dx * length / 2, cy + dy * length / 2)
    pygame.draw.line(surface, color, start, tip, 7)

    perpendicular_x, perpendicular_y = -dy, dx
    left = (
        tip[0] - dx * head + perpendicular_x * head,
        tip[1] - dy * head + perpendicular_y * head,
    )
    right = (
        tip[0] - dx * head - perpendicular_x * head,
        tip[1] - dy * head - perpendicular_y * head,
    )
    pygame.draw.polygon(surface, color, [tip, left, right])


def get_board_layout(rows, cols):
    """根据网格规模计算居中的棋盘位置与格子尺寸。"""
    cell_size = min(MAX_CELL_SIZE, BOARD_AREA_SIZE // max(rows, cols))
    board_width = cols * cell_size
    board_left = (WINDOW_WIDTH - board_width) // 2
    return board_left, BOARD_TOP, cell_size


def get_cell_from_mouse(mouse_pos, rows, cols):
    """把鼠标坐标转换成棋盘行列，棋盘外返回 None。"""
    x, y = mouse_pos
    board_left, board_top, cell_size = get_board_layout(rows, cols)
    board_width = cols * cell_size
    board_height = rows * cell_size

    if not (board_left <= x < board_left + board_width):
        return None
    if not (board_top <= y < board_top + board_height):
        return None

    col = (x - board_left) // cell_size
    row = (y - board_top) // cell_size
    return int(row), int(col)


def draw_board(screen, board, blocked_cell, blocked_until):
    board_left, board_top, cell_size = get_board_layout(
        len(board), len(board[0])
    )
    for row in range(len(board)):
        for col in range(len(board[0])):
            rect = pygame.Rect(
                board_left + col * cell_size,
                board_top + row * cell_size,
                cell_size,
                cell_size,
            )
            pygame.draw.rect(screen, PANEL, rect)
            pygame.draw.rect(screen, GRID_LINE, rect, 2)

            arrow = board[row][col]
            if arrow == EMPTY:
                continue

            is_blocked = (
                blocked_cell == (row, col)
                and pygame.time.get_ticks() < blocked_until
            )
            color = BLOCKED_COLOR if is_blocked else ARROW_COLOR

            shake_x = 0
            if is_blocked:
                shake_x = round(math.sin(pygame.time.get_ticks() * 0.08) * 7)

            draw_arrow(screen, rect.center, arrow, color, (shake_x, 0))


def create_flying_arrow(row, col, direction, rows, cols):
    """创建成功点击后的飞行动画数据。"""
    board_left, board_top, cell_size = get_board_layout(rows, cols)
    return {
        "x": board_left + col * cell_size + cell_size / 2,
        "y": board_top + row * cell_size + cell_size / 2,
        "direction": direction,
    }


def update_flying_arrow(flying_arrow, delta_time, rows, cols):
    """推进飞行动画；箭头越过棋盘边缘后返回 None。"""
    if flying_arrow is None:
        return None

    dr, dc = DIRECTIONS[flying_arrow["direction"]]
    flying_arrow["x"] += dc * FLIGHT_SPEED * delta_time
    flying_arrow["y"] += dr * FLIGHT_SPEED * delta_time

    board_left, board_top, cell_size = get_board_layout(rows, cols)
    margin = 40
    left = board_left - margin
    right = board_left + cols * cell_size + margin
    top = board_top - margin
    bottom = board_top + rows * cell_size + margin

    if not (
        left <= flying_arrow["x"] <= right
        and top <= flying_arrow["y"] <= bottom
    ):
        return None

    return flying_arrow


def draw_text(screen, font, text, position, color=TEXT_COLOR, center=False):
    image = font.render(text, True, color)
    rect = image.get_rect()
    if center:
        rect.center = position
    else:
        rect.topleft = position
    screen.blit(image, rect)


def create_background():
    """预先生成柔和的纵向渐变背景。"""
    background = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    top_color = (28, 35, 62)
    bottom_color = (48, 45, 82)

    for y in range(WINDOW_HEIGHT):
        ratio = y / (WINDOW_HEIGHT - 1)
        color = tuple(
            round(top_color[index] * (1 - ratio) + bottom_color[index] * ratio)
            for index in range(3)
        )
        pygame.draw.line(background, color, (0, y), (WINDOW_WIDTH, y))

    return background


def draw_panel(screen, rect, color=PANEL, radius=24):
    """绘制带阴影的圆角卡片。"""
    shadow = pygame.Surface((rect.width + 20, rect.height + 20), pygame.SRCALPHA)
    pygame.draw.rect(
        shadow,
        (10, 14, 31, 90),
        pygame.Rect(10, 10, rect.width, rect.height),
        border_radius=radius,
    )
    screen.blit(shadow, (rect.x - 4, rect.y - 1))
    pygame.draw.rect(screen, color, rect, border_radius=radius)


def draw_button(screen, rect, text, font, mouse_pos, primary=True):
    """绘制带悬停效果的按钮。"""
    hovered = rect.collidepoint(mouse_pos)
    if primary:
        color = (111, 226, 199) if hovered else ARROW_COLOR
        text_color = (26, 40, 55)
    else:
        color = BUTTON_HOVER_COLOR if hovered else BUTTON_COLOR
        text_color = TEXT_COLOR

    shadow_rect = rect.move(0, 6)
    pygame.draw.rect(screen, (21, 26, 49), shadow_rect, border_radius=15)
    pygame.draw.rect(screen, color, rect, border_radius=15)

    if hovered:
        pygame.draw.rect(screen, (220, 255, 247), rect, 2, border_radius=15)

    draw_text(screen, font, text, rect.center, text_color, center=True)


def draw_start_screen(screen, fonts, mouse_pos, start_button):
    """绘制游戏开始界面。"""
    time_seconds = pygame.time.get_ticks() / 1000

    # 背景光斑和缓慢浮动的方向箭头。
    glow = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    pygame.draw.circle(glow, (91, 214, 190, 22), (130, 120), 150)
    pygame.draw.circle(glow, (111, 145, 255, 20), (650, 620), 190)
    screen.blit(glow, (0, 0))

    decorations = [
        ((100, 190), ">", ACCENT_BLUE, 0.0),
        ((660, 165), "v", ARROW_COLOR, 1.2),
        ((115, 590), "^", ACCENT_YELLOW, 2.4),
        ((650, 555), "<", BLOCKED_COLOR, 3.5),
    ]
    for (x, y), direction, color, phase in decorations:
        float_y = round(math.sin(time_seconds * 1.8 + phase) * 8)
        draw_arrow(screen, (x, y + float_y), direction, color)

    card = pygame.Rect(145, 115, 470, 530)
    draw_panel(screen, card, (45, 53, 84), 30)
    pygame.draw.rect(screen, (74, 88, 127), card, 2, border_radius=30)

    icon_center = (WINDOW_WIDTH // 2, 195)
    pygame.draw.circle(screen, (36, 72, 80), icon_center, 55)
    pygame.draw.circle(screen, ARROW_COLOR, icon_center, 55, 3)
    draw_arrow(screen, icon_center, ">", ARROW_COLOR)

    # 标题阴影让白色文字在深色背景上更醒目。
    draw_text(
        screen,
        fonts["title"],
        "一箭又一箭",
        (WINDOW_WIDTH // 2 + 3, 307),
        (19, 24, 46),
        center=True,
    )
    draw_text(
        screen,
        fonts["title"],
        "一箭又一箭",
        (WINDOW_WIDTH // 2, 303),
        TEXT_COLOR,
        center=True,
    )
    draw_text(
        screen,
        fonts["subtitle"],
        "观察方向 · 找准顺序 · 清空棋盘",
        (WINDOW_WIDTH // 2, 365),
        SUBTEXT_COLOR,
        center=True,
    )

    rule_rect = pygame.Rect(205, 405, 350, 64)
    pygame.draw.rect(screen, (38, 46, 74), rule_rect, border_radius=14)
    draw_text(
        screen,
        fonts["small"],
        "前方没有阻挡的箭头才能飞出",
        rule_rect.center,
        (206, 216, 239),
        center=True,
    )

    draw_button(screen, start_button, "开始游戏", fonts["button"], mouse_pos)
    draw_text(
        screen,
        fonts["tiny"],
        "鼠标点击箭头进行操作",
        (WINDOW_WIDTH // 2, 605),
        (135, 149, 185),
        center=True,
    )


def draw_game_screen(
    screen,
    fonts,
    mouse_pos,
    board,
    level_index,
    mistakes_left,
    message,
    message_color,
    restart_button,
    blocked_cell,
    blocked_until,
    flying_arrow,
):
    """绘制正常游戏状态。"""
    header = pygame.Rect(42, 44, 676, 86)
    draw_panel(screen, header, (43, 51, 81), 20)
    draw_text(screen, fonts["heading"], f"关卡 {level_index + 1}", (68, 67))

    remaining = sum(cell != EMPTY for row in board for cell in row)
    draw_text(screen, fonts["small"], f"箭头 {remaining}", (226, 74), SUBTEXT_COLOR)
    draw_text(
        screen,
        fonts["small"],
        f"机会 {mistakes_left}",
        (374, 74),
        BLOCKED_COLOR if mistakes_left == 1 else SUBTEXT_COLOR,
    )
    draw_button(
        screen,
        restart_button,
        "重新开始",
        fonts["tiny"],
        mouse_pos,
        primary=False,
    )

    board_left, board_top, cell_size = get_board_layout(
        len(board), len(board[0])
    )
    board_rect = pygame.Rect(
        board_left - 12,
        board_top - 12,
        len(board[0]) * cell_size + 24,
        len(board) * cell_size + 24,
    )
    draw_panel(screen, board_rect, (39, 47, 75), 18)
    draw_board(screen, board, blocked_cell, blocked_until)

    if flying_arrow is not None:
        draw_arrow(
            screen,
            (flying_arrow["x"], flying_arrow["y"]),
            flying_arrow["direction"],
            ARROW_COLOR,
        )

    message_rect = pygame.Rect(180, 663, 400, 58)
    pygame.draw.rect(screen, (40, 48, 77), message_rect, border_radius=15)
    draw_text(
        screen,
        fonts["small"],
        message,
        message_rect.center,
        message_color,
        center=True,
    )


def draw_result_screen(
    screen,
    fonts,
    mouse_pos,
    success,
    level_index,
    primary_button,
    home_button,
):
    """绘制通关或失败结果界面。"""
    glow = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    glow_color = (91, 214, 190, 28) if success else (255, 91, 105, 24)
    pygame.draw.circle(glow, glow_color, (WINDOW_WIDTH // 2, 245), 210)
    screen.blit(glow, (0, 0))

    card = pygame.Rect(150, 120, 460, 520)
    draw_panel(screen, card, (45, 53, 84), 30)
    pygame.draw.rect(screen, (74, 88, 127), card, 2, border_radius=30)

    accent = ARROW_COLOR if success else BLOCKED_COLOR
    pygame.draw.circle(screen, (37, 47, 72), (WINDOW_WIDTH // 2, 230), 72)
    pygame.draw.circle(screen, accent, (WINDOW_WIDTH // 2, 230), 72, 4)

    if success:
        pygame.draw.lines(
            screen,
            accent,
            False,
            [(345, 228), (370, 253), (416, 204)],
            9,
        )
    else:
        pygame.draw.line(screen, accent, (350, 200), (410, 260), 9)
        pygame.draw.line(screen, accent, (410, 200), (350, 260), 9)

    title = "挑战成功！" if success else "挑战失败"
    subtitle = (
        f"第 {level_index + 1} 关已全部清空"
        if success
        else "失误机会已经用完，再试一次吧"
    )
    draw_text(
        screen,
        fonts["result"],
        title,
        (WINDOW_WIDTH // 2, 350),
        TEXT_COLOR,
        center=True,
    )
    draw_text(
        screen,
        fonts["small"],
        subtitle,
        (WINDOW_WIDTH // 2, 400),
        SUBTEXT_COLOR,
        center=True,
    )

    primary_text = "下一关" if success and level_index + 1 < len(LEVELS) else "再玩一次"
    if not success:
        primary_text = "重新挑战"
    draw_button(
        screen, primary_button, primary_text, fonts["button"], mouse_pos
    )
    draw_button(
        screen,
        home_button,
        "返回首页",
        fonts["button"],
        mouse_pos,
        primary=False,
    )


def reset_level(level_index):
    """返回关卡开始时需要重置的全部数据。"""
    return (
        copy.deepcopy(LEVELS[level_index]),
        3,
        "点击一个箭头",
        TEXT_COLOR,
        None,
        0,
        None,
    )


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Arrow Game")
    clock = pygame.time.Clock()

    fonts = {
        "title": pygame.font.SysFont("microsoftyahei", 47, bold=True),
        "result": pygame.font.SysFont("microsoftyahei", 38, bold=True),
        "heading": pygame.font.SysFont("microsoftyahei", 27, bold=True),
        "subtitle": pygame.font.SysFont("microsoftyahei", 21),
        "button": pygame.font.SysFont("microsoftyahei", 23, bold=True),
        "small": pygame.font.SysFont("microsoftyahei", 19),
        "tiny": pygame.font.SysFont("microsoftyahei", 17),
    }
    background = create_background()

    level_index = 0
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

    start_button = pygame.Rect(245, 505, 270, 62)
    restart_button = pygame.Rect(558, 63, 130, 46)
    primary_button = pygame.Rect(235, 475, 290, 60)
    home_button = pygame.Rect(235, 555, 290, 56)
    running = True

    while running:
        delta_time = clock.tick(FPS) / 1000
        mouse_pos = pygame.mouse.get_pos()

        if game_state == STATE_PLAYING:
            was_flying = flying_arrow is not None
            flying_arrow = update_flying_arrow(
                flying_arrow, delta_time, len(board), len(board[0])
            )
            if was_flying and flying_arrow is None:
                remaining = sum(cell != EMPTY for row in board for cell in row)
                if remaining == 0:
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
                if game_state == STATE_START:
                    running = False
                else:
                    game_state = STATE_START

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
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
                        game_state = STATE_PLAYING
                    continue

                if game_state in (STATE_LEVEL_COMPLETE, STATE_GAME_OVER):
                    if home_button.collidepoint(event.pos):
                        game_state = STATE_START
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
                        game_state = STATE_PLAYING
                    continue

                if game_state != STATE_PLAYING:
                    continue

                if restart_button.collidepoint(event.pos):
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
                    continue

                # 飞行动画播放期间暂时不接受其他棋盘点击。
                if flying_arrow is None and mistakes_left > 0:
                    cell = get_cell_from_mouse(
                        event.pos, len(board), len(board[0])
                    )
                    if cell is not None:
                        row, col = cell
                        if board[row][col] != EMPTY:
                            if can_fly_out(board, row, col):
                                direction = board[row][col]
                                board[row][col] = EMPTY
                                blocked_cell = None
                                flying_arrow = create_flying_arrow(
                                    row,
                                    col,
                                    direction,
                                    len(board),
                                    len(board[0]),
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
            draw_start_screen(screen, fonts, mouse_pos, start_button)
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
                restart_button,
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
