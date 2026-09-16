# levels.py
from level4_data import ARROWS as LEVEL4_ARROWS

EMPTY = "."

LEVELS = [
    # 第1关：熟悉基本规则
    [
        [">", ".", ".", "^", "."],
        [".", ".", ".", ".", ">"],
        [".", "v", ".", "<", "."],
        [".", ".", "^", ".", "."],
        ["<", ".", ".", ".", "v"],
    ],
    # 第2关：箭头更多，初始状态只有3支箭头可以安全飞出
    [
        ["v", ">", "^", ".", "."],
        ["v", ".", "v", ".", "^"],
        ["v", ".", "<", ">", "^"],
        [".", ">", "v", ".", "^"],
        ["v", ".", "<", "^", "<"],
    ],
    # 第3关：6×6高难度棋盘，安全选择更少，清除顺序更长
    [
        [">", "^", ">", ">", "^", "."],
        [".", ".", ".", "^", "<", "<"],
        [">", ".", ".", "^", ">", "^"],
        [".", "^", "v", "<", ".", "^"],
        [">", ">", ".", "v", "^", "."],
        ["<", "^", "<", ">", ">", "^"],
    ],
    # 第4关：24×16坐标点上的密集折线关卡
    {
        "type": "polyline",
        "rows": 24,
        "cols": 16,
        "arrows": LEVEL4_ARROWS,
    },
]


def is_polyline_level(level_index):
    """判断指定关卡是否使用折线箭头玩法。"""
    return isinstance(LEVELS[level_index], dict)


def get_level_dimensions(level_index):
    """返回关卡的行数和列数。"""
    level = LEVELS[level_index]
    if is_polyline_level(level_index):
        return level["rows"], level["cols"]
    return len(level), len(level[0])


def get_level_arrow_count(level_index):
    """返回关卡初始箭头数量。"""
    level = LEVELS[level_index]
    if is_polyline_level(level_index):
        return len(level["arrows"])
    return sum(cell != EMPTY for row in level for cell in row)
