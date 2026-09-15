import copy
import math

import pygame

from levels import EMPTY, LEVELS


WINDOW_WIDTH = 760
WINDOW_HEIGHT = 760
FPS = 60
CELL_SIZE = 96
BOARD_LEFT = 140
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


def get_cell_from_mouse(mouse_pos, rows, cols):
    """把鼠标坐标转换成棋盘行列，棋盘外返回 None。"""
    x, y = mouse_pos
    board_width = cols * CELL_SIZE
    board_height = rows * CELL_SIZE

    if not (BOARD_LEFT <= x < BOARD_LEFT + board_width):
        return None
    if not (BOARD_TOP <= y < BOARD_TOP + board_height):
        return None

    col = (x - BOARD_LEFT) // CELL_SIZE
    row = (y - BOARD_TOP) // CELL_SIZE
    return int(row), int(col)


def draw_board(screen, board, blocked_cell, blocked_until):
    for row in range(len(board)):
        for col in range(len(board[0])):
            rect = pygame.Rect(
                BOARD_LEFT + col * CELL_SIZE,
                BOARD_TOP + row * CELL_SIZE,
                CELL_SIZE,
                CELL_SIZE,
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


def create_flying_arrow(row, col, direction):
    """创建成功点击后的飞行动画数据。"""
    return {
        "x": BOARD_LEFT + col * CELL_SIZE + CELL_SIZE / 2,
        "y": BOARD_TOP + row * CELL_SIZE + CELL_SIZE / 2,
        "direction": direction,
    }


def update_flying_arrow(flying_arrow, delta_time, rows, cols):
    """推进飞行动画；箭头越过棋盘边缘后返回 None。"""
    if flying_arrow is None:
        return None

    dr, dc = DIRECTIONS[flying_arrow["direction"]]
    flying_arrow["x"] += dc * FLIGHT_SPEED * delta_time
    flying_arrow["y"] += dr * FLIGHT_SPEED * delta_time

    margin = 40
    left = BOARD_LEFT - margin
    right = BOARD_LEFT + cols * CELL_SIZE + margin
    top = BOARD_TOP - margin
    bottom = BOARD_TOP + rows * CELL_SIZE + margin

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


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Arrow Game")
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("microsoftyahei", 25)
    small_font = pygame.font.SysFont("microsoftyahei", 21)

    level_index = 0
    board = copy.deepcopy(LEVELS[level_index])
    mistakes_left = 3
    message = "点击一个箭头"
    message_color = TEXT_COLOR
    blocked_cell = None
    blocked_until = 0
    flying_arrow = None

    restart_button = pygame.Rect(560, 72, 130, 48)
    running = True

    while running:
        delta_time = clock.tick(FPS) / 1000
        mouse_pos = pygame.mouse.get_pos()

        was_flying = flying_arrow is not None
        flying_arrow = update_flying_arrow(
            flying_arrow, delta_time, len(board), len(board[0])
        )
        if was_flying and flying_arrow is None:
            remaining = sum(cell != EMPTY for row in board for cell in row)
            message = "本关完成！" if remaining == 0 else "成功飞出！"
            message_color = ARROW_COLOR

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if restart_button.collidepoint(event.pos):
                    board = copy.deepcopy(LEVELS[level_index])
                    mistakes_left = 3
                    blocked_cell = None
                    flying_arrow = None
                    message = "本关已重新开始"
                    message_color = TEXT_COLOR
                    continue

                # 飞行动画播放期间暂时不接受其他棋盘点击。
                if flying_arrow is not None:
                    continue

                cell = get_cell_from_mouse(event.pos, len(board), len(board[0]))
                if cell is None or mistakes_left <= 0:
                    continue

                row, col = cell
                if board[row][col] == EMPTY:
                    continue

                if can_fly_out(board, row, col):
                    direction = board[row][col]
                    board[row][col] = EMPTY
                    blocked_cell = None
                    flying_arrow = create_flying_arrow(row, col, direction)
                    message = "箭头正在飞出……"
                    message_color = ARROW_COLOR
                else:
                    mistakes_left -= 1
                    blocked_cell = (row, col)
                    blocked_until = pygame.time.get_ticks() + 450
                    message = "前方有箭头阻挡！"
                    message_color = BLOCKED_COLOR

        remaining = sum(cell != EMPTY for row in board for cell in row)

        screen.fill(BACKGROUND)
        draw_text(screen, font, f"关卡 {level_index + 1}", (70, 75))
        draw_text(screen, small_font, f"剩余箭头：{remaining}", (215, 81))
        draw_text(screen, small_font, f"失误机会：{mistakes_left}", (380, 81))

        button_color = (
            BUTTON_HOVER_COLOR
            if restart_button.collidepoint(mouse_pos)
            else BUTTON_COLOR
        )
        pygame.draw.rect(screen, button_color, restart_button, border_radius=10)
        draw_text(screen, small_font, "重新开始", restart_button.center, center=True)

        draw_board(screen, board, blocked_cell, blocked_until)
        if flying_arrow is not None:
            draw_arrow(
                screen,
                (flying_arrow["x"], flying_arrow["y"]),
                flying_arrow["direction"],
                ARROW_COLOR,
            )
        draw_text(
            screen,
            font,
            message,
            (WINDOW_WIDTH // 2, 680),
            message_color,
            center=True,
        )

        if remaining == 0 and flying_arrow is None:
            draw_text(
                screen,
                font,
                "本关完成！",
                (WINDOW_WIDTH // 2, 720),
                ARROW_COLOR,
                center=True,
            )
        elif mistakes_left <= 0:
            draw_text(
                screen,
                font,
                "本关失败，请重新开始",
                (WINDOW_WIDTH // 2, 720),
                BLOCKED_COLOR,
                center=True,
            )

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
