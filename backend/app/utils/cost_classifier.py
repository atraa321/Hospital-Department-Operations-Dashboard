from __future__ import annotations


def classify_cost_group(category: str | None) -> str:
    if category is None:
        return "其他费用"

    category = str(category).strip()

    if category in {"西药费", "成药费"}:
        return "药品费"
    if category == "草药费":
        return "草药费"
    if category == "材料费":
        return "材料费"
    if category in {"检查费", "CT费", "心电图", "彩超费", "B超费", "放射费", "胃镜费", "化验费", "检验费"}:
        return "检查费"
    if category in {"治疗费", "理疗费", "换药费", "注射费", "处置费"}:
        return "治疗费"
    if category in {"手术费", "麻醉费"}:
        return "手术费"
    if category == "护理费":
        return "护理费"
    if category in {"床位费", "诊查费"}:
        return "服务费"
    return "其他费用"
