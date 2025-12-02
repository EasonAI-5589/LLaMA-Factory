#!/usr/bin/env python3
"""
武器库存SFT数据集生成脚本 v3
核心改进：细粒度问答，每个武器多种问法
"""

import json
import random
from pathlib import Path
from collections import defaultdict

# 品质等级排序（从高到低）
QUALITY_ORDER = ["轩辕", "黑鹰", "铁爪", "卓越", "精制", "改进", "完好", "修复", "破损"]

# 武器类型定义
WEAPON_TYPES = {
    "狙击枪": ["狙击枪"],
    "冲锋枪": ["冲锋枪"],
    "突击步枪": ["突击步枪"],
    "射手步枪": ["射手步枪"],
    "轻机枪": ["轻机枪"],
    "霰弹枪": ["霰弹枪"],
    "手枪": ["手枪"],
    "特殊武器": ["十字弩", "弩", "榴弹发射器", "火箭筒", "喷火器", "猎弓"],
}

# 配件关键词
ACCESSORY_KEYWORDS = [
    "弹匣", "消音器", "枪口补偿器", "消焰器", "握把", "枪托(",
    "瞄准镜", "托腮板", "子弹袋", "战术枪托", "延长枪管",
    "鸭嘴枪口", "收束器", "激光瞄准器", "箭袋", "枪托(Micro",
]

# 弹药关键词
AMMO_KEYWORDS = ["子弹", "箭矢", "手雷", "燃烧瓶", "烟雾弹", "震爆弹"]


def is_accessory_or_ammo(item_name: str) -> bool:
    """判断是否是配件或弹药"""
    for acc in ACCESSORY_KEYWORDS:
        if acc in item_name:
            return True
    for ammo in AMMO_KEYWORDS:
        if ammo in item_name:
            return True
    if "榴弹" in item_name and "发射器" not in item_name and "炮" not in item_name:
        return True
    if "口径霰弹" in item_name:
        return True
    return False


def get_weapon_type(item_name: str) -> str:
    """获取武器类型"""
    if is_accessory_or_ammo(item_name):
        return None
    for wtype, keywords in WEAPON_TYPES.items():
        if any(kw in item_name for kw in keywords):
            return wtype
    return None


def extract_quality(item_name: str) -> str:
    """提取品质"""
    for quality in QUALITY_ORDER:
        if f"({quality})" in item_name:
            return quality
    return None


def extract_model(item_name: str) -> str:
    """提取武器型号"""
    # 移除品质后缀
    name = item_name
    for quality in QUALITY_ORDER:
        name = name.replace(f"({quality})", "")
    # 移除武器类型后缀
    for wtype in ["狙击枪", "冲锋枪", "突击步枪", "射手步枪", "轻机枪", "霰弹枪", "手枪"]:
        name = name.replace(wtype, "")
    return name.strip()


def parse_weapons_from_csv(csv_path: str) -> dict:
    """解析CSV文件，返回结构化的武器数据"""
    weapons_by_type = defaultdict(list)
    weapons_by_quality = defaultdict(list)
    weapons_by_model = defaultdict(list)
    all_weapons = []

    with open(csv_path, "r", encoding="utf-8") as f:
        for line in f:
            item_name = line.strip()
            if not item_name:
                continue

            weapon_type = get_weapon_type(item_name)
            if weapon_type is None:
                continue

            quality = extract_quality(item_name)
            model = extract_model(item_name)

            weapon_info = {
                "name": item_name,
                "type": weapon_type,
                "quality": quality,
                "model": model
            }

            all_weapons.append(weapon_info)
            weapons_by_type[weapon_type].append(weapon_info)
            if quality:
                weapons_by_quality[quality].append(weapon_info)
            if model:
                weapons_by_model[model].append(weapon_info)

    return {
        "all": all_weapons,
        "by_type": dict(weapons_by_type),
        "by_quality": dict(weapons_by_quality),
        "by_model": dict(weapons_by_model)
    }


def generate_single_weapon_qa(weapon: dict) -> list:
    """为单个武器生成多种问答对"""
    name = weapon["name"]
    wtype = weapon["type"]
    quality = weapon["quality"]

    qa_pairs = []

    # 问题模板1：查询品质
    if quality:
        quality_questions = [
            f"{name}是什么品质？",
            f"{name}的品质是什么？",
            f"查询{name}的品质",
            f"{name}品质等级",
        ]
        quality_answers = [
            f"{name}是{quality}品质。",
            f"{name}的品质是{quality}。",
        ]
        for q in quality_questions:
            qa_pairs.append({
                "instruction": "查询武器品质",
                "input": q,
                "output": random.choice(quality_answers),
                "task_type": "single_quality"
            })

    # 问题模板2：查询类型
    type_questions = [
        f"{name}属于什么类型？",
        f"{name}是什么类型的武器？",
        f"查询{name}的类型",
        f"{name}是哪种武器？",
    ]
    type_answers = [
        f"{name}属于{wtype}。",
        f"{name}是{wtype}类型。",
    ]
    for q in type_questions:
        qa_pairs.append({
            "instruction": "查询武器类型",
            "input": q,
            "output": random.choice(type_answers),
            "task_type": "single_type"
        })

    # 问题模板3：综合查询（类型+品质）
    if quality:
        combo_questions = [
            f"{name}的品质和类型是什么？",
            f"介绍一下{name}",
            f"查询{name}的信息",
        ]
        combo_answers = [
            f"{name}是{quality}品质的{wtype}。",
            f"{name}属于{wtype}类别，品质为{quality}级。",
        ]
        for q in combo_questions:
            qa_pairs.append({
                "instruction": "查询武器信息",
                "input": q,
                "output": random.choice(combo_answers),
                "task_type": "single_combo"
            })

    return qa_pairs


def generate_type_query(weapons_by_type: dict, wtype: str) -> list:
    """生成类型查询（只列出少量武器）"""
    weapons = weapons_by_type.get(wtype, [])
    if len(weapons) < 3:
        return []

    qa_pairs = []

    # 随机选择3-6个武器，而不是全部
    for _ in range(20):  # 每个类型生成20条
        sample_size = random.randint(3, min(6, len(weapons)))
        sampled = random.sample(weapons, sample_size)
        weapon_names = "、".join([w["name"] for w in sampled])

        questions = [
            f"武器库里有哪些{wtype}？",
            f"列出一些{wtype}",
            f"查询{wtype}",
        ]

        qa_pairs.append({
            "instruction": "查询武器库存",
            "input": random.choice(questions),
            "output": f"武器库中的{wtype}包括：{weapon_names}。",
            "task_type": "type_query_small"
        })

    return qa_pairs


def generate_quality_query(weapons_by_quality: dict, quality: str) -> list:
    """生成品质查询（只列出少量武器）"""
    weapons = weapons_by_quality.get(quality, [])
    if len(weapons) < 3:
        return []

    qa_pairs = []

    for _ in range(15):  # 每个品质生成15条
        sample_size = random.randint(3, min(5, len(weapons)))
        sampled = random.sample(weapons, sample_size)
        weapon_names = "、".join([w["name"] for w in sampled])

        questions = [
            f"有哪些{quality}品质的武器？",
            f"列出一些{quality}级武器",
            f"查询{quality}级武器",
        ]

        qa_pairs.append({
            "instruction": "按品质查询武器",
            "input": random.choice(questions),
            "output": f"{quality}品质的武器包括：{weapon_names}。",
            "task_type": "quality_query_small"
        })

    return qa_pairs


def generate_model_query(weapons_by_model: dict) -> list:
    """生成型号查询"""
    qa_pairs = []

    for model, weapons in weapons_by_model.items():
        if len(weapons) < 2 or len(model) < 2:
            continue

        # 获取该型号的武器类型
        wtype = weapons[0]["type"]
        weapon_names = "、".join([w["name"] for w in weapons])

        questions = [
            f"武器库里有哪些{model}？",
            f"查询所有{model}",
            f"列出{model}的不同品质版本",
        ]

        for q in questions:
            qa_pairs.append({
                "instruction": "查询武器型号",
                "input": q,
                "output": f"武器库中的{model}{wtype}有：{weapon_names}。",
                "task_type": "model_query"
            })

    return qa_pairs


def generate_quality_comparison() -> list:
    """生成品质对比问答"""
    qa_pairs = []
    quality_str = "轩辕/黑鹰/铁爪 > 卓越 > 精制 > 改进 > 完好 > 修复 > 破损"

    # 生成所有品质对的比较
    for i, q1 in enumerate(QUALITY_ORDER):
        for j, q2 in enumerate(QUALITY_ORDER):
            if i == j:
                continue

            if i < j:
                answer = f"{q1}品质高于{q2}。品质从高到低依次为：{quality_str}。"
            else:
                answer = f"{q2}品质高于{q1}。品质从高到低依次为：{quality_str}。"

            questions = [
                f"{q1}和{q2}哪个品质更好？",
                f"{q1}品质高还是{q2}品质高？",
                f"比较{q1}和{q2}的品质",
            ]

            for q in questions:
                qa_pairs.append({
                    "instruction": "对比武器品质",
                    "input": q,
                    "output": answer,
                    "task_type": "quality_compare"
                })

    return qa_pairs


def generate_is_weapon_qa(weapon: dict) -> list:
    """生成"是否是武器"的问答"""
    name = weapon["name"]
    wtype = weapon["type"]

    questions = [
        f"{name}是武器吗？",
        f"{name}是不是武器？",
    ]

    qa_pairs = []
    for q in questions:
        qa_pairs.append({
            "instruction": "判断物品类型",
            "input": q,
            "output": f"是的，{name}是{wtype}类型的武器。",
            "task_type": "is_weapon"
        })

    return qa_pairs


def main():
    # 解析武器数据
    csv_path = Path("/Users/guoyichen/EasonAI/LLaMA-Factory/item_name.csv")
    weapons_data = parse_weapons_from_csv(csv_path)

    print(f"解析到 {len(weapons_data['all'])} 个武器")

    all_qa = []

    # 1. 为每个武器生成细粒度问答（核心）
    print("生成单武器问答...")
    for weapon in weapons_data["all"]:
        qa_pairs = generate_single_weapon_qa(weapon)
        all_qa.extend(qa_pairs)

        # 是否是武器
        qa_pairs = generate_is_weapon_qa(weapon)
        all_qa.extend(qa_pairs)

    print(f"  单武器问答: {len(all_qa)} 条")

    # 2. 类型查询（少量武器）
    print("生成类型查询...")
    type_qa_count = 0
    for wtype in WEAPON_TYPES.keys():
        qa_pairs = generate_type_query(weapons_data["by_type"], wtype)
        all_qa.extend(qa_pairs)
        type_qa_count += len(qa_pairs)
    print(f"  类型查询: {type_qa_count} 条")

    # 3. 品质查询（少量武器）
    print("生成品质查询...")
    quality_qa_count = 0
    for quality in QUALITY_ORDER:
        qa_pairs = generate_quality_query(weapons_data["by_quality"], quality)
        all_qa.extend(qa_pairs)
        quality_qa_count += len(qa_pairs)
    print(f"  品质查询: {quality_qa_count} 条")

    # 4. 型号查询
    print("生成型号查询...")
    model_qa = generate_model_query(weapons_data["by_model"])
    all_qa.extend(model_qa)
    print(f"  型号查询: {len(model_qa)} 条")

    # 5. 品质对比
    print("生成品质对比...")
    compare_qa = generate_quality_comparison()
    all_qa.extend(compare_qa)
    print(f"  品质对比: {len(compare_qa)} 条")

    # 打乱顺序
    random.shuffle(all_qa)

    print(f"\n总数据量: {len(all_qa)} 条")

    # 统计各类型数量
    type_counts = defaultdict(int)
    for qa in all_qa:
        type_counts[qa["task_type"]] += 1
    print("\n各类型数量:")
    for t, c in sorted(type_counts.items()):
        print(f"  {t}: {c}")

    # 保存
    output_path = Path("/Users/guoyichen/EasonAI/LLaMA-Factory/data/weapon_inventory_sft_v3.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_qa, f, ensure_ascii=False, indent=2)

    print(f"\n数据已保存到: {output_path}")

    # 显示示例
    print("\n=== 数据示例 ===")
    for task_type in ["single_quality", "single_type", "single_combo", "type_query_small"]:
        examples = [qa for qa in all_qa if qa["task_type"] == task_type][:2]
        for ex in examples:
            print(f"\n[{task_type}]")
            print(f"  Q: {ex['input']}")
            print(f"  A: {ex['output']}")


if __name__ == "__main__":
    main()
