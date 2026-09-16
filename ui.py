"""Pygame界面的所有绘制函数。"""

import math
from functools import lru_cache
from pathlib import Path

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


def draw_status_badges(
    screen,
    fonts,
    remaining,
    mistakes_left,
    score,
    time_left,
):
    """显示剩余箭头、生命、得分和倒计时。"""
    arrow_badge = pygame.Rect(202, 61, 138, 52)
    hearts_badge = pygame.Rect(360, 61, 182, 52)
    timer_badge = pygame.Rect(548, 61, 80, 52)

    for badge in (arrow_badge, hearts_badge, timer_badge):
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

    seconds_left = max(0, math.ceil(time_left))
    timer_color = (
        BLOCKED_COLOR
        if seconds_left <= 10
        else ACCENT_YELLOW if seconds_left <= 30 else TEXT_COLOR
    )
    clock_center = (561, 87)
    pygame.draw.circle(screen, timer_color, clock_center, 9, 2)
    pygame.draw.line(screen, timer_color, clock_center, (561, 81), 2)
    pygame.draw.line(screen, timer_color, clock_center, (566, 87), 2)
    draw_text(
        screen,
        fonts["tiny"],
        f"{seconds_left // 60}:{seconds_left % 60:02d}",
        (598, 87),
        timer_color,
        center=True,
    )

    draw_text(
        screen,
        fonts["tiny"],
        f"得分 {score}",
        (70, 101),
        ACCENT_YELLOW,
    )


def draw_board(
    screen,
    board,
    blocked_cell,
    blocked_until,
    hinted_cell,
    hint_until,
):
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
            is_hinted = (
                hinted_cell == (row, col)
                and pygame.time.get_ticks() < hint_until
            )
            color = (
                BLOCKED_COLOR
                if is_blocked
                else ACCENT_YELLOW if is_hinted else ARROW_COLOR
            )
            shake_x = 0
            if is_blocked:
                shake_x = round(math.sin(pygame.time.get_ticks() * 0.08) * 7)

            if is_hinted:
                pulse = round(math.sin(pygame.time.get_ticks() * 0.01) * 3)
                pygame.draw.circle(
                    screen,
                    ACCENT_YELLOW,
                    rect.center,
                    max(18, cell_size // 3) + pulse,
                    3,
                )

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
    hinted_arrow,
    hint_until,
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
        is_hinted = (
            hinted_arrow == index
            and pygame.time.get_ticks() < hint_until
        )
        shake_x = 0
        if is_blocked:
            shake_x = round(math.sin(pygame.time.get_ticks() * 0.08) * 7)
        draw_polyline_arrow(
            screen,
            arrow,
            rows,
            cols,
            BLOCKED_COLOR
            if is_blocked
            else ACCENT_YELLOW if is_hinted else None,
            (shake_x, 0),
        )

        if is_hinted:
            head = polyline_point_to_screen(arrow["path"][-1], rows, cols)
            pulse = round(math.sin(pygame.time.get_ticks() * 0.01) * 2)
            pygame.draw.circle(
                screen,
                ACCENT_YELLOW,
                head,
                10 + pulse,
                2,
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


def draw_ai_solve_button(screen, rect, fonts, mouse_pos, active):
    """绘制可启动或停止自动求解的状态按钮。"""
    hovered = rect.collidepoint(mouse_pos)
    if active:
        color = (255, 112, 124) if hovered else BLOCKED_COLOR
        label = "停止求解"
    else:
        color = (129, 158, 255) if hovered else ACCENT_BLUE
        label = "AI 自动求解"

    pygame.draw.rect(screen, (21, 26, 49), rect.move(0, 6), border_radius=15)
    pygame.draw.rect(screen, color, rect, border_radius=15)
    if hovered:
        pygame.draw.rect(screen, (224, 231, 255), rect, 2, border_radius=15)

    # 左侧的三个节点表现简单的自动分析图标。
    icon_x = rect.x + 20
    pygame.draw.line(
        screen,
        (31, 39, 65),
        (icon_x, rect.centery - 7),
        (icon_x + 8, rect.centery),
        2,
    )
    pygame.draw.line(
        screen,
        (31, 39, 65),
        (icon_x, rect.centery + 7),
        (icon_x + 8, rect.centery),
        2,
    )
    for point in (
        (icon_x, rect.centery - 7),
        (icon_x, rect.centery + 7),
        (icon_x + 8, rect.centery),
    ):
        pygame.draw.circle(screen, (31, 39, 65), point, 3)
    draw_text(
        screen,
        fonts["tiny"],
        label,
        (rect.centerx + 10, rect.centery),
        (27, 35, 58),
        center=True,
    )


def draw_hint_button(screen, rect, fonts, mouse_pos):
    """按照参考图绘制青色外圈、黄色灯泡样式的提示按钮。"""
    hovered = rect.collidepoint(mouse_pos)
    panel_color = (52, 68, 99) if hovered else (40, 49, 78)
    pygame.draw.rect(screen, (21, 26, 49), rect.move(0, 5), border_radius=14)
    pygame.draw.rect(screen, panel_color, rect, border_radius=14)
    if hovered:
        pygame.draw.rect(screen, ARROW_COLOR, rect, 2, border_radius=14)

    cx, cy = rect.centerx, rect.y + 20
    pygame.draw.circle(screen, (25, 77, 81), (cx, cy), 17)
    pygame.draw.circle(screen, ARROW_COLOR, (cx, cy), 17, 2)
    pygame.draw.circle(screen, (238, 181, 38), (cx, cy), 13)
    pygame.draw.circle(screen, (255, 214, 75), (cx - 3, cy - 4), 6)

    bulb_color = (255, 247, 190)
    pygame.draw.circle(screen, bulb_color, (cx, cy - 3), 5, 2)
    pygame.draw.line(screen, bulb_color, (cx - 3, cy + 1), (cx - 1, cy + 6), 2)
    pygame.draw.line(screen, bulb_color, (cx + 3, cy + 1), (cx + 1, cy + 6), 2)
    pygame.draw.line(screen, bulb_color, (cx - 2, cy + 7), (cx + 2, cy + 7), 2)
    draw_text(
        screen,
        fonts["tiny"],
        "提示",
        (cx, rect.bottom - 10),
        TEXT_COLOR,
        center=True,
    )


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


def draw_stroked_text(screen, font, text, position, color, stroke_color):
    """绘制适合卡通标题的双层描边文字。"""
    image = font.render(text, True, color)
    outline = font.render(text, True, stroke_color)
    for dx, dy in (
        (-4, 0),
        (4, 0),
        (0, -4),
        (0, 4),
        (-3, -3),
        (3, -3),
        (-3, 3),
        (3, 3),
    ):
        screen.blit(outline, (position[0] + dx, position[1] + dy))
    screen.blit(image, position)


@lru_cache(maxsize=1)
def load_start_artwork():
    """保留透明通道，裁去透明留白后缓存适合首页的角色。"""
    path = Path(__file__).resolve().parent / "assets" / "start_mascot.png"
    original = pygame.image.load(str(path)).convert_alpha()
    original = original.subsurface(original.get_bounding_rect()).copy()
    width = 340
    height = round(original.get_height() * width / original.get_width())
    return pygame.transform.smoothscale(original, (width, height))


def draw_start_mascot(screen, time_seconds):
    """按时间驱动透明角色浮动、轻微摇摆和呼吸缩放。"""
    artwork = load_start_artwork()
    bob = math.sin(time_seconds * 2.2) * 10
    angle = math.sin(time_seconds * 1.5) * 4
    scale = 1 + math.sin(time_seconds * 2.2) * 0.025
    animated = pygame.transform.rotozoom(artwork, angle, scale)
    rect = animated.get_rect(center=(WINDOW_WIDTH // 2, round(345 + bob)))
    screen.blit(animated, rect)


def draw_start_action_button(screen, rect, fonts, mouse_pos, primary):
    """绘制参考图风格的蓝色播放按钮。"""
    hovered = rect.collidepoint(mouse_pos)
    if primary:
        fill = (82, 162, 242) if hovered else (66, 145, 230)
        border = (35, 92, 167)
        text_color = (255, 255, 255)
        label = "开始游戏"
    else:
        fill = (235, 251, 252) if hovered else (220, 245, 248)
        border = (76, 156, 194)
        text_color = (36, 105, 153)
        label = "选择关卡"

    pygame.draw.rect(screen, (36, 91, 145), rect.move(0, 7), border_radius=14)
    pygame.draw.rect(screen, fill, rect, border_radius=14)
    pygame.draw.rect(screen, border, rect, 3, border_radius=14)
    if primary:
        cx, cy = rect.x + 34, rect.centery
        pygame.draw.polygon(
            screen,
            (255, 255, 255),
            [(cx - 8, cy - 12), (cx - 8, cy + 12), (cx + 12, cy)],
        )
        text_center = (rect.centerx + 12, rect.centery)
    else:
        text_center = rect.center
    draw_text(screen, fonts["button"], label, text_center, text_color, center=True)


def draw_start_screen(
    screen, fonts, mouse_pos, start_button, level_select_button
):
    """绘制浅蓝色卡通风格的游戏开始界面。"""
    time_seconds = pygame.time.get_ticks() / 1000
    screen.fill((211, 244, 247))

    # 平铺淡色箭头纹理，让背景接近参考图但保持文字清晰。
    pattern = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    for row, y in enumerate(range(25, WINDOW_HEIGHT, 72)):
        for col, x in enumerate(range(28, WINDOW_WIDTH, 72)):
            points = [
                (x, y - 13),
                (x - 12, y + 1),
                (x - 5, y + 1),
                (x - 5, y + 15),
                (x + 5, y + 15),
                (x + 5, y + 1),
                (x + 12, y + 1),
            ]
            pygame.draw.polygon(pattern, (76, 185, 202, 18), points)
    screen.blit(pattern, (0, 0))

    title_segments = (
        ("一箭", (255, 181, 58)),
        ("又", (74, 154, 235)),
        ("一箭", (73, 192, 133)),
    )
    widths = [fonts["title"].size(text)[0] for text, _ in title_segments]
    title_x = (WINDOW_WIDTH - sum(widths)) // 2
    for (text, color), width in zip(title_segments, widths):
        draw_stroked_text(
            screen,
            fonts["title"],
            text,
            (title_x, 92),
            color,
            (50, 79, 91),
        )
        title_x += width

    pygame.draw.line(screen, (244, 111, 105), (92, 132), (185, 132), 12)
    pygame.draw.polygon(
        screen,
        (244, 111, 105),
        [(185, 120), (208, 132), (185, 144)],
    )
    pygame.draw.line(screen, (72, 160, 231), (575, 132), (668, 132), 12)
    pygame.draw.polygon(
        screen,
        (72, 160, 231),
        [(575, 120), (552, 132), (575, 144)],
    )

    draw_text(
        screen,
        fonts["small"],
        "观察方向 · 找准顺序 · 清空棋盘",
        (WINDOW_WIDTH // 2, 184),
        (54, 115, 137),
        center=True,
    )
    draw_start_mascot(screen, time_seconds)

    draw_start_action_button(screen, start_button, fonts, mouse_pos, True)
    draw_start_action_button(screen, level_select_button, fonts, mouse_pos, False)
    draw_text(
        screen,
        fonts["tiny"],
        "点击箭头，让它沿正确方向飞出去吧！",
        (WINDOW_WIDTH // 2, 690),
        (66, 126, 145),
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
        (WINDOW_WIDTH // 2, 112),
        TEXT_COLOR,
        center=True,
    )
    draw_text(
        screen,
        fonts["small"],
        "完成基础训练，逐步解锁更难的挑战",
        (WINDOW_WIDTH // 2, 157),
        SUBTEXT_COLOR,
        center=True,
    )

    # 两类关卡各自使用独立标题和强调色，便于玩家快速辨认。
    section_labels = (
        ("基础关卡", "第 1–3 关", 198, ARROW_COLOR),
        ("挑战关卡", "第 4–5 关", 386, ACCENT_YELLOW),
    )
    for title, range_text, y, color in section_labels:
        pygame.draw.circle(screen, color, (97, y), 5)
        draw_text(screen, fonts["small"], title, (111, y - 13), TEXT_COLOR)
        draw_text(screen, fonts["tiny"], range_text, (216, y - 11), color)
        pygame.draw.line(screen, (70, 82, 119), (310, y), (661, y), 2)

    for index, rect in enumerate(level_buttons):
        unlocked = index <= highest_unlocked
        hovered = unlocked and rect.collidepoint(mouse_pos)
        is_challenge = index >= 3

        if unlocked:
            if is_challenge:
                card_color = (75, 69, 101) if hovered else (57, 55, 88)
                border_color = ACCENT_YELLOW if hovered else (132, 112, 91)
                accent = ACCENT_YELLOW
            else:
                card_color = (59, 75, 105) if hovered else (50, 61, 94)
                border_color = ARROW_COLOR if hovered else (84, 103, 143)
                accent = ARROW_COLOR
        else:
            card_color = (39, 46, 72)
            border_color = (62, 70, 99)
            accent = (132, 119, 91) if is_challenge else (105, 115, 145)

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
):
    """绘制正常游戏状态。"""
    header = pygame.Rect(42, 44, 676, 86)
    draw_panel(screen, header, (43, 51, 81), 20)
    draw_text(screen, fonts["heading"], f"关卡 {level_index + 1}", (68, 67))

    if is_polyline_level(level_index):
        remaining = len(board)
    else:
        remaining = sum(cell != EMPTY for row in board for cell in row)
    draw_status_badges(
        screen,
        fonts,
        remaining,
        mistakes_left,
        score,
        time_left,
    )
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
            hinted_cell,
            hint_until,
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
        draw_board(
            screen,
            board,
            blocked_cell,
            blocked_until,
            hinted_cell,
            hint_until,
        )

        if flying_arrow is not None:
            draw_arrow(
                screen,
                (flying_arrow["x"], flying_arrow["y"]),
                flying_arrow["direction"],
                ARROW_COLOR,
            )

    draw_ai_solve_button(
        screen,
        ai_solve_button,
        fonts,
        mouse_pos,
        ai_solving,
    )
    draw_hint_button(screen, hint_button, fonts, mouse_pos)

    message_rect = pygame.Rect(292, 663, 426, 58)
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
    score,
    failure_reason,
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
        else failure_reason
    )
    draw_text(
        screen,
        fonts["result"],
        title,
        (WINDOW_WIDTH // 2, 350),
        TEXT_COLOR,
        center=True,
    )

    score_rect = pygame.Rect(285, 425, 190, 42)
    pygame.draw.rect(screen, (38, 47, 75), score_rect, border_radius=12)
    pygame.draw.rect(screen, (77, 91, 130), score_rect, 2, border_radius=12)
    draw_text(
        screen,
        fonts["small"],
        f"本关得分  {score}",
        score_rect.center,
        ACCENT_YELLOW,
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
