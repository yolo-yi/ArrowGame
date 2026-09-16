"""离线设计工具：生成第5关的28×18密集折线布局。"""

import json

import design_level4 as designer


designer.ROWS = 28
designer.COLS = 18


if __name__ == "__main__":
    candidates = [designer.design(500 + seed) for seed in range(24)]
    arrows, metrics = max(
        candidates,
        key=lambda item: item[1][3] * 5 + item[1][0] - item[1][2] * 3,
    )
    arrows = designer.refine(designer.densify(designer.refine(arrows)))
    occupied = set().union(
        *(set(designer.expand(arrow["path"])) for arrow in arrows)
    )
    print(
        json.dumps(
            {
                "arrows": arrows,
                "metrics": {
                    "arrow_count": len(arrows),
                    "occupied_points": len(occupied),
                    "source": metrics,
                },
            }
        )
    )
