#!/usr/bin/env python3
"""
武器库存SFT数据集生成脚本 v8
核心改进：
1. 平衡正/负例比例（目标 50:50）
2. 减少对比问答数量
3. 增加正例问法变体
4. 按武器分组排列
"""

import json
import random
from pathlib import Path
from collections import defaultdict

# 品质等级排序（从高到低）
QUALITY_ORDER = ["轩辕", "黑鹰", "铁爪", "卓越", "精制", "改进", "完好", "修复", "破损"]

# 枪类武器类型
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
    """为单把武器生成正例问答（多种问法变体）"""
    name = gun["name"]
    gtype = gun["type"]
    quality = gun["quality"]

    qa_pairs = []

    # 基础问题 - 是武器吗
    qa_pairs.append({
        "instruction": "",
        "input": f"{name}是武器吗？",
        "output": f"是的，{name}是武器。"
    })

    # 类型问题 - 多种问法
    qa_pairs.append({
        "instruction": "",
        "input": f"{name}是什么武器？",
        "output": f"{name}是{gtype}。"
    })
    qa_pairs.append({
        "instruction": "",
        "input": f"{name}是什么类型的武器？",
        "output": f"{name}是{gtype}。"
    })
    qa_pairs.append({
        "instruction": "",
        "input": f"{name}属于什么类型？",
        "output": f"{name}属于{gtype}类型。"
    })

    # 品质问题 - 多种问法
    qa_pairs.append({
        "instruction": "",
        "input": f"{name}是什么品质？",
        "output": f"{name}是{quality}品质。"
    })
    qa_pairs.append({
        "instruction": "",
        "input": f"{name}的品质是什么？",
        "output": f"{name}的品质是{quality}。"
    })
    qa_pairs.append({
        "instruction": "",
        "input": f"{name}是什么等级？",
        "output": f"{name}是{quality}品质。"
    })

    # 描述问题
    qa_pairs.append({
        "instruction": "",
        "input": f"描述{name}",
        "output": f"{name}是{quality}品质的{gtype}。"
    })
    qa_pairs.append({
        "instruction": "",
        "input": f"介绍一下{name}",
        "output": f"{name}是一把{quality}品质的{gtype}。"
    })

    # 确认类型问题（正向确认）
    qa_pairs.append({
        "instruction": "",
        "input": f"{name}是{gtype}吗？",
        "output": f"是的，{name}是{gtype}。"
    })

    # 确认品质问题（正向确认）
    qa_pairs.append({
        "instruction": "",
        "input": f"{name}是{quality}品质吗？",
        "output": f"是的，{name}是{quality}品质。"
    })

    return qa_pairs


def generate_negative_qa(gun: dict) -> list:
    """为单把武器生成反例问答（类型否定）- 只取3个"""
    name = gun["name"]
    gtype = gun["type"]

    qa_pairs = []
    other_types = [t for t in GUN_TYPES if t != gtype]

    # 只随机选择3个其他类型（减少反例数量）
    selected_types = random.sample(other_types, min(3, len(other_types)))

    for other_type in selected_types:
        qa_pairs.append({
            "instruction": "",
            "input": f"{name}是{other_type}吗？",
            "output": f"不是，{name}是{gtype}，不是{other_type}。"
        })

    return qa_pairs


def generate_limited_comparison_qa(gun: dict, guns_by_type: dict, guns_by_quality: dict, gun_base_names: dict) -> list:
    """为单把武器生成有限的对比问答（每把武器最多4条）"""
    qa_pairs = []
    name = gun["name"]
    gtype = gun["type"]
    quality = gun["quality"]
    base_name = name.rsplit("(", 1)[0]

    # 1. 同一把枪的不同品质版本（最多1条）
    variants = gun_base_names.get(base_name, [])
    other_variants = [v for v in variants if v["name"] != name]
    if other_variants:
        other = random.choice(other_variants)
        qa_pairs.append({
            "instruction": "",
            "input": f"{name}和{other['name']}是同一把枪吗？",
            "output": f"不是，虽然都是{base_name}，但{name}是{quality}品质，{other['name']}是{other['quality']}品质，是不同的武器。"
        })

    # 2. 同品质的不同枪（最多1条）- 正例
    same_quality_guns = [g for g in guns_by_quality.get(quality, [])
                         if g["name"] != name and g["name"].rsplit("(", 1)[0] != base_name]
    if same_quality_guns:
        other = random.choice(same_quality_guns)
        qa_pairs.append({
            "instruction": "",
            "input": f"{name}和{other['name']}是同一品质吗？",
            "output": f"是的，{name}和{other['name']}都是{quality}品质。"
        })

    # 3. 同类型的枪（最多1条）- 正例
    same_type_guns = [g for g in guns_by_type.get(gtype, [])
                      if g["name"] != name and g["name"].rsplit("(", 1)[0] != base_name]
    if same_type_guns:
        other = random.choice(same_type_guns)
        qa_pairs.append({
            "instruction": "",
            "input": f"{name}和{other['name']}是同一类武器吗？",
            "output": f"是的，{name}和{other['name']}都是{gtype}。"
        })

    # 4. 不同类型的枪（最多1条）- 反例
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
    random.seed(42)  # 固定随机种子，保证可复现

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

    # 生成问答数据
    all_qa = []
    positive_count = 0
    negative_count = 0
    comparison_count = 0

    for gun in guns:
        # 1. 正例（11条）
        positive_qa = generate_positive_qa(gun)
        all_qa.extend(positive_qa)
        positive_count += len(positive_qa)

        # 2. 反例（3条）
        negative_qa = generate_negative_qa(gun)
        all_qa.extend(negative_qa)
        negative_count += len(negative_qa)

        # 3. 对比问答（最多4条）
        comparison_qa = generate_limited_comparison_qa(gun, guns_by_type, guns_by_quality, gun_base_names)
        all_qa.extend(comparison_qa)
        comparison_count += len(comparison_qa)

    print(f"\n生成问答数据: {len(all_qa)} 条")
    print(f"  正例: {positive_count} 条 ({positive_count/len(all_qa)*100:.1f}%)")
    print(f"  反例: {negative_count} 条 ({negative_count/len(all_qa)*100:.1f}%)")
    print(f"  对比: {comparison_count} 条 ({comparison_count/len(all_qa)*100:.1f}%)")

    # 去重
    seen_inputs = set()
    unique_qa = []
    for qa in all_qa:
        if qa["input"] not in seen_inputs:
            seen_inputs.add(qa["input"])
            unique_qa.append(qa)

    print(f"\n去重后: {len(unique_qa)} 条（去除 {len(all_qa) - len(unique_qa)} 条重复）")

    # 统计回答类型分布
    yes_count = sum(1 for qa in unique_qa if qa["output"].startswith("是"))
    no_count = sum(1 for qa in unique_qa if qa["output"].startswith("不是"))
    other_count = len(unique_qa) - yes_count - no_count

    print(f"\n回答类型分布:")
    print(f"  '是的/是' 开头: {yes_count} 条 ({yes_count/len(unique_qa)*100:.1f}%)")
    print(f"  '不是' 开头: {no_count} 条 ({no_count/len(unique_qa)*100:.1f}%)")
    print(f"  其他: {other_count} 条 ({other_count/len(unique_qa)*100:.1f}%)")

    # 保存
    output_path = Path("/Users/guoyichen/EasonAI/LLaMA-Factory/data/weapon_inventory_sft_v8.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(unique_qa, f, ensure_ascii=False, indent=2)

    print(f"\n数据已保存到: {output_path}")

    # 显示示例
    print("\n" + "=" * 60)
    print("=== 数据示例（第一把武器）===")
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
    for i, qa in enumerate(sample_negative, 1):
        print(f"  Q{i}: {qa['input']}")
        print(f"  A{i}: {qa['output']}")


if __name__ == "__main__":
    main()
