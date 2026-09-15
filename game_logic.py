"""棋盘规则、坐标换算和飞行动画数据。"""

import copy

from levels import EMPTY, LEVELS
from settings import (
    BOARD_AREA_SIZE,
    BOARD_TOP,
    DIRECTIONS,
    FLIGHT_SPEED,
    MAX_CELL_SIZE,
    TEXT_COLOR,
    WINDOW_WIDTH,
)


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
