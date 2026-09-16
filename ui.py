"""Pygame界面的所有绘制函数。"""

import math

import pygame

from game_logic import (
    get_flying_polyline_points,
    get_board_layout,
    get_polyline_direction,
    get_polyline_layout,
    polyline_point_to_screen,
)
from levels import (
    EMPTY,
    LEVELS,
    get_level_arrow_count,
    get_level_dimensions,
    is_polyline_level,
)
from settings import (
    ACCENT_BLUE,
    ACCENT_YELLOW,
    ARROW_COLOR,
    BLOCKED_COLOR,
    BUTTON_COLOR,
    BUTTON_HOVER_COLOR,
    GRID_LINE,
    PANEL,
    SUBTEXT_COLOR,
    TEXT_COLOR,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)


def draw_arrow(
    surface,
    center,
    direction,
    color,
    offset=(0, 0),
    length=48,
    head=15,
    line_width=7,
):
    """使用线段和三角形画箭头，不依赖字体中的箭头符号。"""
    cx = center[0] + offset[0]
    cy = center[1] + offset[1]

    vectors = {
        "^": (0, -1),
        "v": (0, 1),
        "<": (-1, 0),
        ">": (1, 0),
    }
    dx, dy = vectors[direction]

    start = (cx - dx * length / 2, cy - dy * length / 2)
    tip = (cx + dx * length / 2, cy + dy * length / 2)
    pygame.draw.line(surface, color, start, tip, line_width)

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


def draw_heart(surface, center, color, size=12):
    """使用基础图形绘制一颗心，避免依赖emoji字体。"""
    x, y = center
    radius = round(size * 0.56)
    pygame.draw.circle(
        surface, color, (round(x - size * 0.48), round(y - size * 0.25)), radius
    )
    pygame.draw.circle(
        surface, color, (round(x + size * 0.48), round(y - size * 0.25)), radius
    )
    pygame.draw.polygon(
        surface,
        color,
        [
            (round(x - size), y),
            (round(x + size), y),
            (x, round(y + size * 1.35)),
        ],
    )


def draw_status_badges(screen, fonts, remaining, mistakes_left):
    """用箭头计数徽章和心形图标显示游戏状态。"""
    arrow_badge = pygame.Rect(202, 61, 138, 52)
    hearts_badge = pygame.Rect(360, 61, 182, 52)

    for badge in (arrow_badge, hearts_badge):
        pygame.draw.rect(screen, (34, 43, 71), badge, border_radius=14)
        pygame.draw.rect(screen, (68, 82, 119), badge, 2, border_radius=14)

    pygame.draw.circle(screen, (35, 75, 78), (232, 87), 18)
    draw_arrow(
        screen,
        (232, 87),
        ">",
        ARROW_COLOR,
        length=20,
        head=7,
        line_width=4,
    )
    draw_text(
        screen,
        fonts["heading"],
        f"× {remaining}",
        (286, 86),
        TEXT_COLOR,
        center=True,
    )

    for index in range(3):
        active = index < mistakes_left
        color = BLOCKED_COLOR if active else (72, 81, 111)
        draw_heart(screen, (398 + index * 52, 84), color)
        if active:
            pygame.draw.circle(
                screen,
                (255, 158, 166),
                (394 + index * 52, 79),
                2,
            )


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


def draw_polyline_arrow(
    screen, arrow, rows, cols, color=None, offset=(0, 0), screen_points=None
):
    """绘制一条经过多个坐标点的折线箭头。"""
    line_color = color or arrow["color"]
    points = screen_points
    if points is None:
        points = []
        for point in arrow["path"]:
            x, y = polyline_point_to_screen(point, rows, cols)
            points.append((x + offset[0], y + offset[1]))

    dr, dc = get_polyline_direction(arrow["path"])
    dx, dy = dc, dr
    tip = points[-1]
    _, _, spacing = get_polyline_layout(rows, cols)
    detail_scale = min(1.0, spacing / 30)
    head_length = 12 * detail_scale
    head_width = 7 * detail_scale
    perpendicular_x, perpendicular_y = -dy, dx
    base_x = tip[0] - dx * head_length
    base_y = tip[1] - dy * head_length
    left = (
        base_x + perpendicular_x * head_width,
        base_y + perpendicular_y * head_width,
    )
    right = (
        base_x - perpendicular_x * head_width,
        base_y - perpendicular_y * head_width,
    )
    # 在局部透明画布上以3倍分辨率绘制，再缩小以平滑轮廓。
    scale = 3
    padding = 12
    origin_x = math.floor(min(p[0] for p in points)) - padding
    origin_y = math.floor(min(p[1] for p in points)) - padding
    width = math.ceil(max(p[0] for p in points)) - origin_x + padding
    height = math.ceil(max(p[1] for p in points)) - origin_y + padding
    layer = pygame.Surface((width * scale, height * scale), pygame.SRCALPHA)

    def local(point):
        return (
            round((point[0] - origin_x) * scale),
            round((point[1] - origin_y) * scale),
        )

    # 用小段二次曲线连接转角，保留原坐标点作为点击与路径判定依据。
    smooth_points = [points[0]]
    for previous, corner, following in zip(points, points[1:], points[2:]):
        before = math.dist(previous, corner)
        after = math.dist(corner, following)
        if before == 0 or after == 0:
            continue
        radius = min(6 * detail_scale, before / 2, after / 2)
        entry = tuple(corner[i] + (previous[i] - corner[i]) * radius / before for i in (0, 1))
        leave = tuple(corner[i] + (following[i] - corner[i]) * radius / after for i in (0, 1))
        smooth_points.append(entry)
        for step in range(1, 9):
            t = step / 8
            smooth_points.append(tuple(
                (1 - t) ** 2 * entry[i] + 2 * (1 - t) * t * corner[i] + t ** 2 * leave[i]
                for i in (0, 1)
            ))
    # 线杆在箭头内部结束，避免粗线从三角尖端露出。
    smooth_points.append((tip[0] - dx * 4 * detail_scale, tip[1] - dy * 4 * detail_scale))
    pixels = [local(point) for point in smooth_points]
    pygame.draw.lines(layer, line_color, False, pixels, round(5 * scale * detail_scale))
    for point in pixels:
        pygame.draw.circle(layer, line_color, point, round(7 * detail_scale))
    pygame.draw.polygon(layer, line_color, [local(tip), local(left), local(right)])
    screen.blit(pygame.transform.smoothscale(layer, (width, height)), (origin_x, origin_y))


def draw_polyline_board(
    screen,
    arrows,
    rows,
    cols,
    blocked_arrow,
    blocked_until,
    flying_arrow,
):
    """绘制坐标点、全部折线以及正在飞出的折线。"""
    left, top, spacing = get_polyline_layout(rows, cols)
    for row in range(rows):
        for col in range(cols):
            point = left + col * spacing, top + row * spacing
            pygame.draw.circle(screen, (66, 78, 108), point, 1 if spacing < 30 else 2)

    for index, arrow in enumerate(arrows):
        is_blocked = (
            blocked_arrow == index
            and pygame.time.get_ticks() < blocked_until
        )
        shake_x = 0
        if is_blocked:
            shake_x = round(math.sin(pygame.time.get_ticks() * 0.08) * 7)
        draw_polyline_arrow(
            screen,
            arrow,
            rows,
            cols,
            BLOCKED_COLOR if is_blocked else None,
            (shake_x, 0),
        )

    if flying_arrow is not None:
        draw_polyline_arrow(
            screen,
            flying_arrow["arrow"],
            rows,
            cols,
            screen_points=get_flying_polyline_points(flying_arrow, rows, cols),
        )


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


def draw_settings_button(screen, rect, mouse_pos):
    """绘制不依赖图标字体的齿轮按钮。"""
    hovered = rect.collidepoint(mouse_pos)
    color = BUTTON_HOVER_COLOR if hovered else BUTTON_COLOR
    pygame.draw.rect(screen, (21, 26, 49), rect.move(0, 5), border_radius=13)
    pygame.draw.rect(screen, color, rect, border_radius=13)
    if hovered:
        pygame.draw.rect(screen, (190, 205, 241), rect, 2, border_radius=13)

    cx, cy = rect.center
    icon_color = TEXT_COLOR
    for index in range(8):
        angle = index * math.pi / 4
        inner = (cx + math.cos(angle) * 13, cy + math.sin(angle) * 13)
        outer = (cx + math.cos(angle) * 18, cy + math.sin(angle) * 18)
        pygame.draw.line(screen, icon_color, inner, outer, 4)
    pygame.draw.circle(screen, icon_color, (cx, cy), 13, 4)
    pygame.draw.circle(screen, icon_color, (cx, cy), 4)


def draw_settings_menu(
    screen,
    fonts,
    mouse_pos,
    restart_button,
    home_button,
    close_button,
):
    """在棋盘上方绘制暂停式设置菜单。"""
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    overlay.fill((12, 16, 34, 175))
    screen.blit(overlay, (0, 0))

    card = pygame.Rect(200, 200, 360, 350)
    draw_panel(screen, card, (48, 57, 88), 28)
    pygame.draw.rect(screen, (86, 104, 146), card, 2, border_radius=28)

    close_hovered = close_button.collidepoint(mouse_pos)
    close_color = BLOCKED_COLOR if close_hovered else SUBTEXT_COLOR
    pygame.draw.circle(screen, (38, 46, 74), close_button.center, 18)
    pygame.draw.line(
        screen,
        close_color,
        (close_button.x + 10, close_button.y + 10),
        (close_button.right - 10, close_button.bottom - 10),
        3,
    )
    pygame.draw.line(
        screen,
        close_color,
        (close_button.right - 10, close_button.y + 10),
        (close_button.x + 10, close_button.bottom - 10),
        3,
    )

    draw_text(
        screen,
        fonts["result"],
        "游戏设置",
        (WINDOW_WIDTH // 2, 270),
        TEXT_COLOR,
        center=True,
    )
    draw_text(
        screen,
        fonts["tiny"],
        "游戏已暂停",
        (WINDOW_WIDTH // 2, 310),
        SUBTEXT_COLOR,
        center=True,
    )
    draw_button(
        screen,
        restart_button,
        "重新开始",
        fonts["button"],
        mouse_pos,
    )
    draw_button(
        screen,
        home_button,
        "返回主页",
        fonts["button"],
        mouse_pos,
        primary=False,
    )
    draw_text(
        screen,
        fonts["tiny"],
        "按 Esc 也可以关闭设置",
        (WINDOW_WIDTH // 2, 515),
        (128, 141, 177),
        center=True,
    )


def draw_start_screen(
    screen, fonts, mouse_pos, start_button, level_select_button
):
    """绘制游戏开始界面。"""
    time_seconds = pygame.time.get_ticks() / 1000

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
    draw_button(
        screen,
        level_select_button,
        "选择关卡",
        fonts["button"],
        mouse_pos,
        primary=False,
    )
    draw_text(
        screen,
        fonts["tiny"],
        "鼠标点击箭头进行操作",
        (WINDOW_WIDTH // 2, 625),
        (135, 149, 185),
        center=True,
    )


def draw_level_select_screen(
    screen,
    fonts,
    mouse_pos,
    level_buttons,
    highest_unlocked,
    back_button,
):
    """绘制关卡选择页及锁定状态。"""
    glow = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    pygame.draw.circle(glow, (111, 145, 255, 22), (105, 120), 170)
    pygame.draw.circle(glow, (91, 214, 190, 20), (680, 650), 190)
    screen.blit(glow, (0, 0))

    panel_rect = pygame.Rect(70, 65, 620, 625)
    draw_panel(screen, panel_rect, (45, 53, 84), 30)
    pygame.draw.rect(screen, (74, 88, 127), panel_rect, 2, border_radius=30)

    draw_text(
        screen,
        fonts["result"],
        "选择关卡",
        (WINDOW_WIDTH // 2, 130),
        TEXT_COLOR,
        center=True,
    )
    draw_text(
        screen,
        fonts["small"],
        "通关前一关，即可解锁下一关",
        (WINDOW_WIDTH // 2, 180),
        SUBTEXT_COLOR,
        center=True,
    )

    for index, rect in enumerate(level_buttons):
        unlocked = index <= highest_unlocked
        hovered = unlocked and rect.collidepoint(mouse_pos)

        if unlocked:
            card_color = (59, 75, 105) if hovered else (50, 61, 94)
            border_color = ARROW_COLOR if hovered else (84, 103, 143)
            accent = ARROW_COLOR
        else:
            card_color = (39, 46, 72)
            border_color = (62, 70, 99)
            accent = (105, 115, 145)

        pygame.draw.rect(screen, (22, 27, 49), rect.move(0, 7), border_radius=18)
        pygame.draw.rect(screen, card_color, rect, border_radius=18)
        pygame.draw.rect(screen, border_color, rect, 2, border_radius=18)

        icon_center = (rect.x + 48, rect.centery)
        pygame.draw.circle(screen, (37, 46, 73), icon_center, 30)
        pygame.draw.circle(screen, accent, icon_center, 3, 2)

        if unlocked:
            draw_text(
                screen,
                fonts["heading"],
                str(index + 1),
                icon_center,
                accent,
                center=True,
            )
        else:
            lock_rect = pygame.Rect(icon_center[0] - 12, icon_center[1] - 2, 24, 20)
            pygame.draw.rect(screen, accent, lock_rect, 3, border_radius=3)
            pygame.draw.arc(
                screen,
                accent,
                pygame.Rect(icon_center[0] - 9, icon_center[1] - 16, 18, 22),
                0,
                math.pi,
                3,
            )

        draw_text(
            screen,
            fonts["button"],
            f"第 {index + 1} 关",
            (rect.x + 90, rect.y + 22),
            TEXT_COLOR if unlocked else (126, 136, 164),
        )

        rows, cols = get_level_dimensions(index)
        arrow_count = get_level_arrow_count(index)
        draw_text(
            screen,
            fonts["tiny"],
            f"{rows}×{cols} · {arrow_count}支",
            (rect.x + 90, rect.y + 63),
            SUBTEXT_COLOR if unlocked else (94, 103, 130),
        )
        draw_text(
            screen,
            fonts["tiny"],
            "点击挑战" if unlocked else "尚未解锁",
            (rect.x + 90, rect.y + 101),
            accent,
        )

    draw_button(
        screen,
        back_button,
        "返回首页",
        fonts["button"],
        mouse_pos,
        primary=False,
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
    settings_button,
    settings_open,
    settings_restart_button,
    settings_home_button,
    settings_close_button,
    blocked_cell,
    blocked_until,
    flying_arrow,
):
    """绘制正常游戏状态。"""
    header = pygame.Rect(42, 44, 676, 86)
    draw_panel(screen, header, (43, 51, 81), 20)
    draw_text(screen, fonts["heading"], f"关卡 {level_index + 1}", (68, 67))

    if is_polyline_level(level_index):
        remaining = len(board)
    else:
        remaining = sum(cell != EMPTY for row in board for cell in row)
    draw_status_badges(screen, fonts, remaining, mistakes_left)
    draw_settings_button(screen, settings_button, mouse_pos)

    if is_polyline_level(level_index):
        rows, cols = get_level_dimensions(level_index)
        board_left, board_top, spacing = get_polyline_layout(rows, cols)
        board_rect = pygame.Rect(
            board_left - 32,
            board_top - 12,
            (cols - 1) * spacing + 64,
            (rows - 1) * spacing + 32,
        )
        draw_panel(screen, board_rect, (39, 47, 75), 18)
        draw_polyline_board(
            screen,
            board,
            rows,
            cols,
            blocked_cell,
            blocked_until,
            flying_arrow,
        )
    else:
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

    if settings_open:
        draw_settings_menu(
            screen,
            fonts,
            mouse_pos,
            settings_restart_button,
            settings_home_button,
            settings_close_button,
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
    draw_button(screen, primary_button, primary_text, fonts["button"], mouse_pos)
    draw_button(
        screen,
        home_button,
        "返回首页",
        fonts["button"],
        mouse_pos,
        primary=False,
    )
