#!/usr/bin/env python3
"""
武器库存SFT数据集生成脚本 v6
核心设计：
1. 只处理枪类武器（排除特殊武器、防具、配件）
2. 每把武器生成4个问题
3. 专注单向查询，不做列举类问题
"""

import json
import random
from pathlib import Path
from collections import defaultdict

# 品质等级排序（从高到低）
QUALITY_ORDER = ["轩辕", "黑鹰", "铁爪", "卓越", "精制", "改进", "完好", "修复", "破损"]

# 枪类武器类型（排除特殊武器）
GUN_TYPES = {
    "狙击枪": ["狙击枪"],
    "冲锋枪": ["冲锋枪"],
    "突击步枪": ["突击步枪"],
    "射手步枪": ["射手步枪"],
    "轻机枪": ["轻机枪"],
    "霰弹枪": ["霰弹枪"],
    "手枪": ["手枪"],
}

# 配件关键词（排除）
ACCESSORY_KEYWORDS = [
    "弹匣", "消音器", "枪口补偿器", "消焰器", "握把", "枪托(",
    "瞄准镜", "托腮板", "子弹袋", "战术枪托", "延长枪管",
    "鸭嘴枪口", "收束器", "激光瞄准器", "箭袋", "枪托(Micro",
]

# 弹药关键词（排除）
AMMO_KEYWORDS = ["子弹", "箭矢", "手雷", "燃烧瓶", "烟雾弹", "震爆弹", "榴弹"]

# 其他排除关键词
EXCLUDE_KEYWORDS = ["物资箱", "礼包", "套装", "Boss", "默认弹匣"]


def should_exclude(item_name: str) -> bool:
    """判断是否应该排除"""
    # 排除配件
    for acc in ACCESSORY_KEYWORDS:
        if acc in item_name:
            return True
    # 排除弹药
    for ammo in AMMO_KEYWORDS:
        if ammo in item_name:
            return True
    # 排除其他
    for kw in EXCLUDE_KEYWORDS:
        if kw in item_name:
            return True
    # 排除子物品
    if item_name.startswith("子物品-"):
        return True
    return False


def get_gun_type(item_name: str) -> str:
    """获取枪类武器类型，非枪类返回 None"""
    if should_exclude(item_name):
        return None
    for gtype, keywords in GUN_TYPES.items():
        if any(kw in item_name for kw in keywords):
            return gtype
    return None


def extract_quality(item_name: str) -> str:
    """提取品质"""
    for quality in QUALITY_ORDER:
        if f"({quality})" in item_name:
            return quality
    return None


def parse_guns_from_csv(csv_path: str) -> list:
    """解析CSV文件，只返回枪类武器"""
    guns = []
    seen = set()

    with open(csv_path, "r", encoding="utf-8") as f:
        for line in f:
            item_name = line.strip()
            if not item_name:
                continue

            # 去重
            if item_name in seen:
                continue
            seen.add(item_name)

            gun_type = get_gun_type(item_name)
            if gun_type is None:
                continue

            quality = extract_quality(item_name)
            if quality is None:
                continue  # 只处理有品质的武器

            guns.append({
                "name": item_name,
                "type": gun_type,
                "quality": quality
            })

    return guns


def generate_gun_qa(gun: dict) -> list:
    """为单把武器生成4个问答对"""
    name = gun["name"]
    gtype = gun["type"]
    quality = gun["quality"]

    qa_pairs = []

    # 问题1：是武器吗？
    qa_pairs.append({
        "instruction": "",
        "input": f"{name}是武器吗？",
        "output": f"是的，{name}是武器。"
    })

    # 问题2：是什么武器？
    qa_pairs.append({
        "instruction": "",
        "input": f"{name}是什么武器？",
        "output": f"{name}是{gtype}。"
    })

    # 问题3：是什么品质？
    qa_pairs.append({
        "instruction": "",
        "input": f"{name}是什么品质？",
        "output": f"{name}是{quality}品质。"
    })

    # 问题4：描述
    qa_pairs.append({
        "instruction": "",
        "input": f"描述{name}",
        "output": f"{name}是{quality}品质的{gtype}。"
    })

    return qa_pairs


def main():
    csv_path = Path("/Users/guoyichen/EasonAI/LLaMA-Factory/item_name.csv")
    guns = parse_guns_from_csv(csv_path)

    print(f"解析到 {len(guns)} 把枪类武器")

    # 统计各类型数量
    type_counts = defaultdict(int)
    quality_counts = defaultdict(int)
    for gun in guns:
        type_counts[gun["type"]] += 1
        quality_counts[gun["quality"]] += 1

    print("\n各类型数量:")
    for t, c in sorted(type_counts.items()):
        print(f"  {t}: {c}")

    print("\n各品质数量:")
    for q in QUALITY_ORDER:
        if q in quality_counts:
            print(f"  {q}: {quality_counts[q]}")

    # 生成问答数据
    all_qa = []
    for gun in guns:
        qa_pairs = generate_gun_qa(gun)
        all_qa.extend(qa_pairs)

    print(f"\n生成问答数据: {len(all_qa)} 条")

    # 去重
    seen_inputs = set()
    unique_qa = []
    for qa in all_qa:
        if qa["input"] not in seen_inputs:
            seen_inputs.add(qa["input"])
            unique_qa.append(qa)

    print(f"去重后: {len(unique_qa)} 条")

    # 打乱顺序
    random.shuffle(unique_qa)

    # 保存
    output_path = Path("/Users/guoyichen/EasonAI/LLaMA-Factory/data/weapon_inventory_sft_v6.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(unique_qa, f, ensure_ascii=False, indent=2)

    print(f"\n数据已保存到: {output_path}")

    # 显示示例
    print("\n=== 数据示例 ===")
    # 找一把武器显示完整4个问题
    sample_gun = guns[0]
    sample_qa = generate_gun_qa(sample_gun)
    print(f"\n武器: {sample_gun['name']}")
    for i, qa in enumerate(sample_qa):
        print(f"  Q{i+1}: {qa['input']}")
        print(f"  A{i+1}: {qa['output']}")


if __name__ == "__main__":
    main()
