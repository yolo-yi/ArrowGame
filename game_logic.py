"""棋盘规则、坐标换算和飞行动画数据。"""

import copy

from levels import EMPTY, LEVELS, is_polyline_level
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


def find_flyable_grid_arrow(board):
    """返回当前网格中下一支可以安全飞出的箭头坐标。"""
    for row, cells in enumerate(board):
        for col, arrow in enumerate(cells):
            if arrow != EMPTY and can_fly_out(board, row, col):
                return row, col
    return None


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


def get_polyline_layout(rows, cols):
    """计算折线关卡坐标点的起点和间距。"""
    spacing = min(44, BOARD_AREA_SIZE // max(rows - 1, cols - 1))
    width = (cols - 1) * spacing
    left = (WINDOW_WIDTH - width) // 2
    return left, BOARD_TOP, spacing


def polyline_point_to_screen(point, rows, cols):
    """把折线关卡中的行列坐标转换成屏幕像素坐标。"""
    left, top, spacing = get_polyline_layout(rows, cols)
    row, col = point
    return left + col * spacing, top + row * spacing


def expand_polyline_points(path):
    """展开折线经过的所有整数坐标点，包括线段中间点。"""
    occupied = set()
    for start, end in zip(path, path[1:]):
        dr = (end[0] > start[0]) - (end[0] < start[0])
        dc = (end[1] > start[1]) - (end[1] < start[1])
        if dr != 0 and dc != 0:
            raise ValueError("折线路径只能包含水平或垂直线段")

        point = start
        occupied.add(point)
        while point != end:
            point = point[0] + dr, point[1] + dc
            occupied.add(point)
    return occupied


def get_polyline_direction(path):
    """根据折线最后一段计算箭头方向。"""
    previous, head = path[-2], path[-1]
    return (
        (head[0] > previous[0]) - (head[0] < previous[0]),
        (head[1] > previous[1]) - (head[1] < previous[1]),
    )


def can_polyline_fly_out(arrows, arrow_index, rows, cols):
    """判断折线箭头头部到边界之间是否被其他折线占据。"""
    arrow = arrows[arrow_index]
    head = arrow["path"][-1]
    dr, dc = get_polyline_direction(arrow["path"])

    other_points = set()
    for index, other_arrow in enumerate(arrows):
        if index != arrow_index:
            other_points.update(expand_polyline_points(other_arrow["path"]))

    point = head[0] + dr, head[1] + dc
    while 0 <= point[0] < rows and 0 <= point[1] < cols:
        if point in other_points:
            return False
        point = point[0] + dr, point[1] + dc

    return True


def find_flyable_polyline_arrow(arrows, rows, cols):
    """返回当前折线关卡中下一支可以安全飞出的箭头索引。"""
    for arrow_index in range(len(arrows)):
        if can_polyline_fly_out(arrows, arrow_index, rows, cols):
            return arrow_index
    return None


def get_polyline_arrow_from_mouse(arrows, mouse_pos, rows, cols):
    """点击折线任意线段时返回对应箭头索引。"""
    _, _, spacing = get_polyline_layout(rows, cols)
    tolerance = min(11, spacing * 0.38)
    mouse_x, mouse_y = mouse_pos

    for index in range(len(arrows) - 1, -1, -1):
        path = arrows[index]["path"]
        screen_points = [
            polyline_point_to_screen(point, rows, cols) for point in path
        ]
        for start, end in zip(screen_points, screen_points[1:]):
            left = min(start[0], end[0]) - tolerance
            right = max(start[0], end[0]) + tolerance
            top = min(start[1], end[1]) - tolerance
            bottom = max(start[1], end[1]) + tolerance
            if left <= mouse_x <= right and top <= mouse_y <= bottom:
                return index

    return None


def create_flying_polyline(arrows, arrow_index):
    """从关卡中取出折线，并创建整条线的飞行动画数据。"""
    arrow = arrows.pop(arrow_index)
    return {
        "arrow": arrow,
        "direction": get_polyline_direction(arrow["path"]),
        "distance": 0.0,
    }


def get_flying_polyline_points(flying_arrow, rows, cols):
    """尾部沿原折线前进，头部沿末段延伸，保持箭头总长度。"""
    points = [
        polyline_point_to_screen(point, rows, cols)
        for point in flying_arrow["arrow"]["path"]
    ]
    distance = flying_arrow["distance"]
    dr, dc = flying_arrow["direction"]
    head_x, head_y = points[-1]
    if distance <= 0:
        return points

    # 从尾部依次消耗线段；尚未经过的拐点留在原位置。
    remaining = distance
    for index, (start, end) in enumerate(zip(points, points[1:])):
        length = abs(end[0] - start[0]) + abs(end[1] - start[1])
        if length == 0:
            continue
        if remaining < length:
            ratio = remaining / length
            tail = (
                start[0] + (end[0] - start[0]) * ratio,
                start[1] + (end[1] - start[1]) * ratio,
            )
            return [tail] + points[index + 1:] + [
                (head_x + dc * distance, head_y + dr * distance)
            ]
        remaining -= length

    # 尾部也走过最后一个拐点后，整条线进入头部的出射直线。
    return [
        (head_x + dc * remaining, head_y + dr * remaining),
        (head_x + dc * distance, head_y + dr * distance),
    ]


def update_flying_polyline(flying_arrow, delta_time, rows, cols):
    """沿折线轨迹推进，尾部越过边界后结束动画。"""
    if flying_arrow is None:
        return None

    dr, dc = flying_arrow["direction"]
    flying_arrow["distance"] += FLIGHT_SPEED * delta_time

    points = get_flying_polyline_points(flying_arrow, rows, cols)
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    left, top, spacing = get_polyline_layout(rows, cols)
    right = left + (cols - 1) * spacing
    bottom = top + (rows - 1) * spacing
    margin = 30

    completely_out = (
        (dc < 0 and max(xs) < left - margin)
        or (dc > 0 and min(xs) > right + margin)
        or (dr < 0 and max(ys) < top - margin)
        or (dr > 0 and min(ys) > bottom + margin)
    )
    return None if completely_out else flying_arrow


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
    level = LEVELS[level_index]
    board = level["arrows"] if is_polyline_level(level_index) else level
    return (
        copy.deepcopy(board),
        3,
        "点击一个箭头",
        TEXT_COLOR,
        None,
        0,
        None,
    )
