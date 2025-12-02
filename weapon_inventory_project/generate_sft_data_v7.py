#!/usr/bin/env python3
"""
武器库存SFT数据集生成脚本 v7
核心改进：
1. 增加反例（类型否定）
2. 按武器分组排列（不打乱顺序）
3. 每把武器 10 个问题（4正例 + 6反例）
"""

import json
from pathlib import Path
from collections import defaultdict

# 品质等级排序（从高到低）
QUALITY_ORDER = ["轩辕", "黑鹰", "铁爪", "卓越", "精制", "改进", "完好", "修复", "破损"]

# 枪类武器类型（排除特殊武器）
GUN_TYPES = ["狙击枪", "冲锋枪", "突击步枪", "射手步枪", "轻机枪", "霰弹枪", "手枪"]

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
    for acc in ACCESSORY_KEYWORDS:
        if acc in item_name:
            return True
    for ammo in AMMO_KEYWORDS:
        if ammo in item_name:
            return True
    for kw in EXCLUDE_KEYWORDS:
        if kw in item_name:
            return True
    if item_name.startswith("子物品-"):
        return True
    return False


def get_gun_type(item_name: str) -> str:
    """获取枪类武器类型，非枪类返回 None"""
    if should_exclude(item_name):
        return None
    for gtype in GUN_TYPES:
        if gtype in item_name:
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

            if item_name in seen:
                continue
            seen.add(item_name)

            gun_type = get_gun_type(item_name)
            if gun_type is None:
                continue

            quality = extract_quality(item_name)
            if quality is None:
                continue

            guns.append({
                "name": item_name,
                "type": gun_type,
                "quality": quality
            })

    return guns


def generate_positive_qa(gun: dict) -> list:
    """为单把武器生成4个正例问答"""
    name = gun["name"]
    gtype = gun["type"]
    quality = gun["quality"]

    return [
        # 问题1：是武器吗？
        {
            "instruction": "",
            "input": f"{name}是武器吗？",
            "output": f"是的，{name}是武器。"
        },
        # 问题2：是什么武器？
        {
            "instruction": "",
            "input": f"{name}是什么武器？",
            "output": f"{name}是{gtype}。"
        },
        # 问题3：是什么品质？
        {
            "instruction": "",
            "input": f"{name}是什么品质？",
            "output": f"{name}是{quality}品质。"
        },
        # 问题4：描述
        {
            "instruction": "",
            "input": f"描述{name}",
            "output": f"{name}是{quality}品质的{gtype}。"
        }
    ]


def generate_negative_qa(gun: dict) -> list:
    """为单把武器生成6个反例问答（类型否定）"""
    name = gun["name"]
    gtype = gun["type"]

    qa_pairs = []
    for other_type in GUN_TYPES:
        if other_type != gtype:
            qa_pairs.append({
                "instruction": "",
                "input": f"{name}是{other_type}吗？",
                "output": f"不是，{name}是{gtype}，不是{other_type}。"
            })

    return qa_pairs


def generate_comparison_qa_for_gun(gun: dict, all_guns: list, guns_by_type: dict, guns_by_quality: dict, gun_base_names: dict) -> list:
    """为单把武器生成对比问答"""
    import random
    qa_pairs = []
    name = gun["name"]
    gtype = gun["type"]
    quality = gun["quality"]
    base_name = name.rsplit("(", 1)[0]

    # 1. 同一把枪的不同品质版本对比
    variants = gun_base_names.get(base_name, [])
    for other in variants:
        if other["name"] != name:
            qa_pairs.append({
                "instruction": "",
                "input": f"{name}和{other['name']}是同一把枪吗？",
                "output": f"不是，虽然都是{base_name}，但{name}是{quality}品质，{other['name']}是{other['quality']}品质，是不同的武器。"
            })
            qa_pairs.append({
                "instruction": "",
                "input": f"{name}和{other['name']}是同一品质吗？",
                "output": f"不是，{name}是{quality}品质，{other['name']}是{other['quality']}品质。"
            })
            qa_pairs.append({
                "instruction": "",
                "input": f"{name}和{other['name']}是同一类武器吗？",
                "output": f"是的，{name}和{other['name']}都是{gtype}。"
            })

    # 2. 同品质不同枪的对比（取2把）
    same_quality_guns = [g for g in guns_by_quality.get(quality, []) if g["name"] != name]
    # 按基础名去重，每个基础名取一把
    seen_bases = {base_name}
    sampled = []
    for g in same_quality_guns:
        g_base = g["name"].rsplit("(", 1)[0]
        if g_base not in seen_bases:
            seen_bases.add(g_base)
            sampled.append(g)
            if len(sampled) >= 2:
                break

    for other in sampled:
        other_base = other["name"].rsplit("(", 1)[0]
        qa_pairs.append({
            "instruction": "",
            "input": f"{name}和{other['name']}是同一品质吗？",
            "output": f"是的，{name}和{other['name']}都是{quality}品质。"
        })
        qa_pairs.append({
            "instruction": "",
            "input": f"{name}和{other['name']}是同一把枪吗？",
            "output": f"不是，{name}是{base_name}，{other['name']}是{other_base}，是不同的枪。"
        })
        if gtype == other["type"]:
            qa_pairs.append({
                "instruction": "",
                "input": f"{name}和{other['name']}是同一类武器吗？",
                "output": f"是的，{name}和{other['name']}都是{gtype}。"
            })
        else:
            qa_pairs.append({
                "instruction": "",
                "input": f"{name}和{other['name']}是同一类武器吗？",
                "output": f"不是，{name}是{gtype}，{other['name']}是{other['type']}。"
            })

    # 3. 同类型不同品质对比（取1把）
    same_type_guns = [g for g in guns_by_type.get(gtype, []) if g["name"] != name and g["quality"] != quality]
    if same_type_guns:
        other = random.choice(same_type_guns)
        qa_pairs.append({
            "instruction": "",
            "input": f"{name}和{other['name']}是同一品质吗？",
            "output": f"不是，{name}是{quality}品质，{other['name']}是{other['quality']}品质。"
        })
        qa_pairs.append({
            "instruction": "",
            "input": f"{name}和{other['name']}是同一类武器吗？",
            "output": f"是的，{name}和{other['name']}都是{gtype}。"
        })

    # 4. 不同类型对比（取1把）
    other_types = [t for t in GUN_TYPES if t != gtype]
    if other_types:
        other_type = random.choice(other_types)
        other_type_guns = guns_by_type.get(other_type, [])
        if other_type_guns:
            other = random.choice(other_type_guns)
            qa_pairs.append({
                "instruction": "",
                "input": f"{name}和{other['name']}是同一类武器吗？",
                "output": f"不是，{name}是{gtype}，{other['name']}是{other_type}。"
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
    for t in GUN_TYPES:
        print(f"  {t}: {type_counts[t]}")

    print("\n各品质数量:")
    for q in QUALITY_ORDER:
        if q in quality_counts:
            print(f"  {q}: {quality_counts[q]}")

    # 预处理：建立索引
    guns_by_type = defaultdict(list)
    guns_by_quality = defaultdict(list)
    gun_base_names = defaultdict(list)
    for gun in guns:
        guns_by_type[gun["type"]].append(gun)
        guns_by_quality[gun["quality"]].append(gun)
        base_name = gun["name"].rsplit("(", 1)[0]
        gun_base_names[base_name].append(gun)

    # 生成问答数据（按武器分组，每把武器的所有问答放一起）
    all_qa = []
    comparison_count = 0
    for gun in guns:
        # 1. 正例
        positive_qa = generate_positive_qa(gun)
        all_qa.extend(positive_qa)
        # 2. 反例（类型否定）
        negative_qa = generate_negative_qa(gun)
        all_qa.extend(negative_qa)
        # 3. 对比问答（紧跟在该武器后面）
        comparison_qa = generate_comparison_qa_for_gun(gun, guns, guns_by_type, guns_by_quality, gun_base_names)
        all_qa.extend(comparison_qa)
        comparison_count += len(comparison_qa)

    positive_count = len(guns) * 4
    negative_count = len(guns) * 6

    print(f"\n生成问答数据: {len(all_qa)} 条")
    print(f"  正例: {positive_count} 条")
    print(f"  反例（类型否定）: {negative_count} 条")
    print(f"  对比问答: {comparison_count} 条")

    # 去重（保留第一个出现的）
    seen_inputs = set()
    unique_qa = []
    for qa in all_qa:
        if qa["input"] not in seen_inputs:
            seen_inputs.add(qa["input"])
            unique_qa.append(qa)

    print(f"\n去重后: {len(unique_qa)} 条（去除 {len(all_qa) - len(unique_qa)} 条重复）")

    # 保存（不打乱，按武器分组）
    output_path = Path("/Users/guoyichen/EasonAI/LLaMA-Factory/data/weapon_inventory_sft_v7.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(unique_qa, f, ensure_ascii=False, indent=2)

    print(f"\n数据已保存到: {output_path}")

    # 显示示例（一把武器的完整10个问题）
    print("\n" + "=" * 60)
    print("=== 数据示例（第一把武器的完整10个问题）===")
    print("=" * 60)
    sample_gun = guns[0]
    print(f"\n武器: {sample_gun['name']}")
    print(f"类型: {sample_gun['type']}")
    print(f"品质: {sample_gun['quality']}")

    print("\n--- 正例 ---")
    sample_positive = generate_positive_qa(sample_gun)
    for i, qa in enumerate(sample_positive, 1):
        print(f"  Q{i}: {qa['input']}")
        print(f"  A{i}: {qa['output']}")

    print("\n--- 反例 ---")
    sample_negative = generate_negative_qa(sample_gun)
    for i, qa in enumerate(sample_negative, 5):
        print(f"  Q{i}: {qa['input']}")
        print(f"  A{i}: {qa['output']}")


if __name__ == "__main__":
    main()
