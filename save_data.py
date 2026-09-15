"""读取和保存玩家的关卡解锁进度。"""

import json
from pathlib import Path


SAVE_FILE = Path(__file__).with_name("progress.json")


def load_highest_unlocked(total_levels):
    """读取最高已解锁关卡的索引；存档损坏时安全回到第1关。"""
    try:
        data = json.loads(SAVE_FILE.read_text(encoding="utf-8"))
        highest = int(data.get("highest_unlocked_level", 1)) - 1
    except (FileNotFoundError, OSError, ValueError, TypeError, json.JSONDecodeError):
        highest = 0

    return max(0, min(highest, total_levels - 1))


def save_highest_unlocked(highest_index):
    """将最高已解锁关卡保存为玩家看到的1起始编号。"""
    data = {"highest_unlocked_level": highest_index + 1}
    SAVE_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
