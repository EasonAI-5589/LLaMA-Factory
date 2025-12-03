#!/usr/bin/env python3
"""
武器库存SFT数据集生成脚本 v8
核心改进：
1. 平衡正/负例比例（目标 50:50）
2. 减少对比问答数量
3. 增加正例问法变体
4. 按武器分组排列
5. 添加装备（头盔、防弹衣、背包）支持
"""

import json
import random
import re
from pathlib import Path
from collections import defaultdict

# 品质等级排序（从高到低）
QUALITY_ORDER = ["轩辕", "卓越", "黑鹰", "铁爪", "精制", "改进", "完好", "修复", "破损"]
ARMOR_QUALITY = ["轩辕", "黑鹰", "铁爪"]  # 装备可用的品质

# 枪类武器类型
GUN_TYPES = ["狙击枪", "冲锋枪", "突击步枪", "射手步枪", "轻机枪", "霰弹枪", "手枪"]

# 装备类型
ARMOR_TYPES = ["头盔", "防弹衣", "背包"]

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


def parse_armors_from_csv(csv_path: str) -> list:
    """解析CSV文件，只返回装备（头盔、防弹衣、背包）"""
    armors = []
    seen = set()

    # 匹配模式: X级头盔/防弹衣/背包 或 X级头盔/防弹衣/背包(品质) 或 X级头盔·特殊名
    armor_pattern = re.compile(r'^(\d)级(头盔|防弹衣|背包)(?:\(([^)]+)\)|·(.+))?$')

    with open(csv_path, "r", encoding="utf-8") as f:
        for line in f:
            item_name = line.strip()
            if not item_name:
                continue

            # 排除子物品
            if item_name.startswith("子物品-"):
                continue

            if item_name in seen:
                continue
            seen.add(item_name)

            match = armor_pattern.match(item_name)
            if not match:
                continue

            level = int(match.group(1))
            armor_type = match.group(2)
            quality = match.group(3)  # 括号内的品质
            special_name = match.group(4)  # 特殊名称如"墨守"

            # 验证品质
            if quality and quality not in ARMOR_QUALITY:
                continue

            armors.append({
                "name": item_name,
                "type": armor_type,
                "level": level,
                "quality": quality,  # 可能为 None（无品质装备）
                "special_name": special_name  # 可能为 None
            })

    return armors


def generate_armor_positive_qa(armor: dict) -> list:
    """为装备生成正例问答"""
    name = armor["name"]
    armor_type = armor["type"]
    level = armor["level"]
    quality = armor["quality"]

    qa_pairs = []

    # 1. 是装备吗
    qa_pairs.append({
        "instruction": "",
        "input": f"{name}是装备吗？",
        "output": f"是的，{name}是装备。"
    })

    # 2. 类型问题
    qa_pairs.append({
        "instruction": "",
        "input": f"{name}是什么装备？",
        "output": f"{name}是{level}级{armor_type}。"
    })

    # 3. 等级问题
    qa_pairs.append({
        "instruction": "",
        "input": f"{name}是几级装备？",
        "output": f"{name}是{level}级装备。"
    })

    # 4. 确认类型
    qa_pairs.append({
        "instruction": "",
        "input": f"{name}是{armor_type}吗？",
        "output": f"是的，{name}是{armor_type}。"
    })

    # 5. 如果有品质，添加品质问答
    if quality:
        qa_pairs.append({
            "instruction": "",
            "input": f"{name}是什么品质？",
            "output": f"{name}是{quality}品质。"
        })
        qa_pairs.append({
            "instruction": "",
            "input": f"{name}是{quality}品质吗？",
            "output": f"是的，{name}是{quality}品质。"
        })
        qa_pairs.append({
            "instruction": "",
            "input": f"描述{name}",
            "output": f"{name}是{quality}品质的{level}级{armor_type}。"
        })
    else:
        qa_pairs.append({
            "instruction": "",
            "input": f"描述{name}",
            "output": f"{name}是{level}级{armor_type}。"
        })

    return qa_pairs


def generate_armor_negative_qa(armor: dict) -> list:
    """为装备生成反例问答"""
    name = armor["name"]
    armor_type = armor["type"]
    quality = armor["quality"]

    qa_pairs = []

    # 1. 类型否定
    other_types = [t for t in ARMOR_TYPES if t != armor_type]
    for other_type in other_types:
        qa_pairs.append({
            "instruction": "",
            "input": f"{name}是{other_type}吗？",
            "output": f"不是，{name}是{armor_type}，不是{other_type}。"
        })

    # 2. 品质否定（如果有品质）
    if quality:
        other_qualities = [q for q in ARMOR_QUALITY if q != quality]
        for other_quality in other_qualities:
            qa_pairs.append({
                "instruction": "",
                "input": f"{name}是{other_quality}品质吗？",
                "output": f"不是，{name}是{quality}品质，不是{other_quality}品质。"
            })

    return qa_pairs


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

    # 确认类型问题（正向确认）- 多种问法
    qa_pairs.append({
        "instruction": "",
        "input": f"{name}是{gtype}吗？",
        "output": f"是的，{name}是{gtype}。"
    })
    qa_pairs.append({
        "instruction": "",
        "input": f"{name}属于什么类型？",
        "output": f"{name}属于{gtype}类型。"
    })
    qa_pairs.append({
        "instruction": "",
        "input": f"{name}是什么类型的武器？",
        "output": f"{name}是{gtype}。"
    })

    # 确认品质问题（正向确认）
    qa_pairs.append({
        "instruction": "",
        "input": f"{name}是{quality}品质吗？",
        "output": f"是的，{name}是{quality}品质。"
    })

    return qa_pairs


def generate_negative_qa(gun: dict) -> list:
    """为单把武器生成反例问答（类型否定 + 品质否定）"""
    name = gun["name"]
    gtype = gun["type"]
    quality = gun["quality"]

    qa_pairs = []

    # 1. 类型否定 - 随机选择3个其他类型
    other_types = [t for t in GUN_TYPES if t != gtype]
    selected_types = random.sample(other_types, min(3, len(other_types)))

    for other_type in selected_types:
        qa_pairs.append({
            "instruction": "",
            "input": f"{name}是{other_type}吗？",
            "output": f"不是，{name}是{gtype}，不是{other_type}。"
        })

    # 2. 品质否定 - 随机选择3个其他品质
    other_qualities = [q for q in QUALITY_ORDER if q != quality]
    selected_qualities = random.sample(other_qualities, min(3, len(other_qualities)))

    for other_quality in selected_qualities:
        qa_pairs.append({
            "instruction": "",
            "input": f"{name}是{other_quality}品质吗？",
            "output": f"不是，{name}是{quality}品质，不是{other_quality}品质。"
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
            "output": f"不是，虽然都是{base_name}，但{name}是{quality}品质，{other['name']}是{other['quality']}品质，{quality}和{other['quality']}是不同的品质，所以是不同的武器。"
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
                "output": f"不是，{name}是{gtype}，{other['name']}是{other_type}，{gtype}和{other_type}不是同一类型的武器。"
            })

    return qa_pairs


def generate_type_quality_confusion_qa(guns: list, guns_by_type: dict) -> list:
    """生成品质+类型混淆反例，强化模型对类型的精确识别"""
    qa_pairs = []

    # 1. 用其他类型的武器问是否属于某类型 - 强化类型区分
    # 例如：PKM轻机枪(轩辕)是狙击枪吗？ → 不是，PKM轻机枪(轩辕)是轻机枪，不是狙击枪。
    for gtype in GUN_TYPES:
        type_guns = guns_by_type.get(gtype, [])
        other_types = [t for t in GUN_TYPES if t != gtype]

        for gun in type_guns:
            # 每把武器针对2个其他类型生成反例
            for other_type in random.sample(other_types, min(2, len(other_types))):
                qa_pairs.append({
                    "instruction": "",
                    "input": f"{gun['name']}是{other_type}吗？",
                    "output": f"不是，{gun['name']}是{gtype}，不是{other_type}。"
                })

    # 2. 品质+类型组合的精确查询反例
    # 例如：轩辕品质的狙击枪里有PKM轻机枪(轩辕)吗？ → 没有，PKM轻机枪(轩辕)是轻机枪，不是狙击枪。
    for quality in QUALITY_ORDER:
        for gtype in GUN_TYPES:
            # 获取该品质下其他类型的武器
            other_types = [t for t in GUN_TYPES if t != gtype]
            for other_type in other_types:
                other_type_guns = [g for g in guns_by_type.get(other_type, []) if g["quality"] == quality]
                if other_type_guns:
                    # 随机选一把其他类型的武器
                    wrong_gun = random.choice(other_type_guns)
                    qa_pairs.append({
                        "instruction": "",
                        "input": f"{wrong_gun['name']}是{quality}品质的{gtype}吗？",
                        "output": f"不是，{wrong_gun['name']}是{quality}品质的{other_type}，不是{gtype}。"
                    })

    return qa_pairs


def generate_listing_qa(guns: list, guns_by_type: dict, guns_by_quality: dict) -> list:
    """生成列举类问答，只使用词表中实际存在的完整武器名称（带品质）"""
    qa_pairs = []

    # 1. 按类型+品质组合：存在性问题
    for gtype in GUN_TYPES:
        for quality in QUALITY_ORDER:
            matching_guns = [g for g in guns if g["type"] == gtype and g["quality"] == quality]

            if len(matching_guns) > 0:
                # 有这种组合 - 生成正例
                gun_names = [g["name"] for g in matching_guns]
                sample_size = min(random.randint(2, 3), len(gun_names))
                sampled = random.sample(gun_names, sample_size)
                weapon_list = "、".join(sampled)

                # 存在性问题（更多问法变体）
                existence_questions = [
                    f"有{quality}品质的{gtype}吗？",
                    f"有没有{quality}品质的{gtype}？",
                    f"仓库里有{quality}品质的{gtype}吗？",
                    f"{quality}品质的{gtype}有哪些？",
                    f"列举一些{quality}品质的{gtype}",
                ]
                for q in existence_questions:
                    qa_pairs.append({
                        "instruction": "",
                        "input": q,
                        "output": f"有的，{quality}品质的{gtype}有{weapon_list}等。"
                    })
            else:
                # 没有这种组合 - 生成反例
                negative_questions = [
                    f"有{quality}品质的{gtype}吗？",
                    f"有没有{quality}品质的{gtype}？",
                    f"仓库里有{quality}品质的{gtype}吗？",
                    f"{quality}品质的{gtype}有哪些？",
                    f"列举一些{quality}品质的{gtype}",
                ]
                for q in negative_questions:
                    qa_pairs.append({
                        "instruction": "",
                        "input": q,
                        "output": f"没有，仓库里没有{quality}品质的{gtype}。"
                    })

    # 2. 复杂对比列举：多武器类型对比（2同+1异）
    for gtype in GUN_TYPES:
        type_guns = guns_by_type.get(gtype, [])
        if len(type_guns) < 2:
            continue

        other_types = [t for t in GUN_TYPES if t != gtype]

        for _ in range(30):  # 每种类型生成30个复杂对比
            # 选2个同类型武器
            same_type = random.sample(type_guns, min(2, len(type_guns)))
            same_names = [g["name"] for g in same_type]

            # 选1个不同类型武器
            other_type = random.choice(other_types)
            other_guns = guns_by_type.get(other_type, [])
            if not other_guns:
                continue
            diff_gun = random.choice(other_guns)

            # 生成问答
            all_names = same_names + [diff_gun["name"]]
            random.shuffle(all_names)
            question_list = "、".join(all_names)

            # 统一格式：逐个说明每把武器的类型
            # 找出每个名字对应的类型
            name_type_map = {same_names[0]: gtype, same_names[1]: gtype, diff_gun["name"]: other_type}
            types_str = "、".join([f"{n}是{name_type_map[n]}" for n in all_names])
            qa_pairs.append({
                "instruction": "",
                "input": f"{question_list}是同一类武器吗？",
                "output": f"不是，{types_str}，它们不是同一类武器。"
            })

    # 3. 三个同类型武器对比（正例）- 增加数量平衡正反例
    for gtype in GUN_TYPES:
        type_guns = guns_by_type.get(gtype, [])
        if len(type_guns) < 3:
            continue

        for _ in range(80):  # 每种类型生成80个正例（增加到80）
            same_type = random.sample(type_guns, 3)
            names = [g["name"] for g in same_type]
            question_list = "、".join(names)

            # 统一格式：逐个说明每把武器的类型
            qa_pairs.append({
                "instruction": "",
                "input": f"{question_list}是同一类武器吗？",
                "output": f"是的，{names[0]}是{gtype}，{names[1]}是{gtype}，{names[2]}是{gtype}，它们都是{gtype}。"
            })

    # 4. 三个完全不同类型武器对比（反例）
    all_types = list(guns_by_type.keys())
    for _ in range(200):  # 生成200个三种不同类型的对比
        # 随机选3种不同类型
        if len(all_types) < 3:
            continue
        selected_types = random.sample(all_types, 3)

        guns_selected = []
        for t in selected_types:
            type_guns = guns_by_type.get(t, [])
            if type_guns:
                guns_selected.append(random.choice(type_guns))

        if len(guns_selected) == 3:
            # 打乱顺序，同时保持名称和类型对应
            random.shuffle(guns_selected)
            names = [g["name"] for g in guns_selected]
            types = [g["type"] for g in guns_selected]
            question_list = "、".join(names)

            qa_pairs.append({
                "instruction": "",
                "input": f"{question_list}是同一类武器吗？",
                "output": f"不是，{names[0]}是{types[0]}，{names[1]}是{types[1]}，{names[2]}是{types[2]}，三种都是不同类型的武器。"
            })

    return qa_pairs


def generate_quality_definition_qa() -> list:
    """生成品质定义和对比问答"""
    qa_pairs = []

    # 品质分类
    HIGH_QUALITY = ["轩辕", "卓越", "黑鹰", "铁爪"]
    NORMAL_QUALITY = ["精制", "改进", "完好"]
    LOW_QUALITY = ["修复", "破损"]

    # 1. 品质等级列表
    quality_list = "、".join(QUALITY_ORDER)
    qa_pairs.append({
        "instruction": "",
        "input": "武器有哪些品质等级？",
        "output": f"武器品质从高到低分为：{quality_list}。"
    })
    qa_pairs.append({
        "instruction": "",
        "input": "武器品质有几种？",
        "output": f"武器品质共有{len(QUALITY_ORDER)}种，从高到低分别是：{quality_list}。"
    })
    qa_pairs.append({
        "instruction": "",
        "input": "列出所有品质等级",
        "output": f"品质等级从高到低：{quality_list}。"
    })

    # 1.5 品质分类问答
    high_list = "、".join(HIGH_QUALITY)
    normal_list = "、".join(NORMAL_QUALITY)
    low_list = "、".join(LOW_QUALITY)

    qa_pairs.append({
        "instruction": "",
        "input": "哪些是高品质？",
        "output": f"高品质包括：{high_list}。"
    })
    qa_pairs.append({
        "instruction": "",
        "input": "高品质有哪些？",
        "output": f"高品质有：{high_list}。"
    })
    qa_pairs.append({
        "instruction": "",
        "input": "哪些是普通品质？",
        "output": f"普通品质包括：{normal_list}。"
    })
    qa_pairs.append({
        "instruction": "",
        "input": "普通品质有哪些？",
        "output": f"普通品质有：{normal_list}。"
    })
    qa_pairs.append({
        "instruction": "",
        "input": "哪些是低品质？",
        "output": f"低品质包括：{low_list}。"
    })
    qa_pairs.append({
        "instruction": "",
        "input": "低品质有哪些？",
        "output": f"低品质有：{low_list}。"
    })
    # 品质分类的多种问法变体（增强训练）
    classification_answer = f"品质分为三类：高品质（{high_list}）、普通品质（{normal_list}）、低品质（{low_list}）。"
    classification_questions = [
        "品质是如何分类的？",
        "品质怎么分类？",
        "武器品质如何分类？",
        "品质有哪几类？",
        "品质分成几类？",
        "品质可以分为几类？",
        "武器品质分为哪几类？",
        "品质等级怎么分类的？",
        "品质分类是什么？",
        "介绍一下品质分类",
    ]
    for q in classification_questions:
        qa_pairs.append({
            "instruction": "",
            "input": q,
            "output": classification_answer
        })

    # 每个品质属于哪个分类
    for q in HIGH_QUALITY:
        qa_pairs.append({
            "instruction": "",
            "input": f"{q}是什么级别的品质？",
            "output": f"{q}是高品质。"
        })
        qa_pairs.append({
            "instruction": "",
            "input": f"{q}属于高品质吗？",
            "output": f"是的，{q}属于高品质。"
        })
        qa_pairs.append({
            "instruction": "",
            "input": f"{q}属于普通品质吗？",
            "output": f"不是，{q}是高品质，不是普通品质。"
        })
        qa_pairs.append({
            "instruction": "",
            "input": f"{q}属于低品质吗？",
            "output": f"不是，{q}是高品质，不是低品质。"
        })

    for q in NORMAL_QUALITY:
        qa_pairs.append({
            "instruction": "",
            "input": f"{q}是什么级别的品质？",
            "output": f"{q}是普通品质。"
        })
        qa_pairs.append({
            "instruction": "",
            "input": f"{q}属于普通品质吗？",
            "output": f"是的，{q}属于普通品质。"
        })
        qa_pairs.append({
            "instruction": "",
            "input": f"{q}属于高品质吗？",
            "output": f"不是，{q}是普通品质，不是高品质。"
        })
        qa_pairs.append({
            "instruction": "",
            "input": f"{q}属于低品质吗？",
            "output": f"不是，{q}是普通品质，不是低品质。"
        })

    for q in LOW_QUALITY:
        qa_pairs.append({
            "instruction": "",
            "input": f"{q}是什么级别的品质？",
            "output": f"{q}是低品质。"
        })
        qa_pairs.append({
            "instruction": "",
            "input": f"{q}属于低品质吗？",
            "output": f"是的，{q}属于低品质。"
        })
        qa_pairs.append({
            "instruction": "",
            "input": f"{q}属于高品质吗？",
            "output": f"不是，{q}是低品质，不是高品质。"
        })
        qa_pairs.append({
            "instruction": "",
            "input": f"{q}属于普通品质吗？",
            "output": f"不是，{q}是低品质，不是普通品质。"
        })

    # 2. 最高/最低品质
    qa_pairs.append({
        "instruction": "",
        "input": "最高品质是什么？",
        "output": f"最高品质是{QUALITY_ORDER[0]}。"
    })
    qa_pairs.append({
        "instruction": "",
        "input": "什么品质最高？",
        "output": f"{QUALITY_ORDER[0]}品质最高。"
    })
    qa_pairs.append({
        "instruction": "",
        "input": "最低品质是什么？",
        "output": f"最低品质是{QUALITY_ORDER[-1]}。"
    })
    qa_pairs.append({
        "instruction": "",
        "input": "什么品质最低？",
        "output": f"{QUALITY_ORDER[-1]}品质最低。"
    })

    # 3. 每个品质的排名
    for i, quality in enumerate(QUALITY_ORDER):
        rank = i + 1
        qa_pairs.append({
            "instruction": "",
            "input": f"{quality}品质排第几？",
            "output": f"{quality}品质排第{rank}，共{len(QUALITY_ORDER)}个品质等级。"
        })
        qa_pairs.append({
            "instruction": "",
            "input": f"{quality}是什么等级的品质？",
            "output": f"{quality}是第{rank}高的品质。" if rank <= 4 else f"{quality}是第{rank}的品质，属于较低品质。"
        })

    # 4. 相邻品质对比
    for i in range(len(QUALITY_ORDER) - 1):
        higher = QUALITY_ORDER[i]
        lower = QUALITY_ORDER[i + 1]
        qa_pairs.append({
            "instruction": "",
            "input": f"{higher}和{lower}哪个品质更高？",
            "output": f"{higher}品质更高，{higher}排第{i+1}，{lower}排第{i+2}。"
        })
        qa_pairs.append({
            "instruction": "",
            "input": f"{lower}和{higher}哪个品质更高？",
            "output": f"{higher}品质更高，{higher}排第{i+1}，{lower}排第{i+2}。"
        })
        qa_pairs.append({
            "instruction": "",
            "input": f"{higher}品质高还是{lower}品质高？",
            "output": f"{higher}品质更高。"
        })

    # 5. 跨级品质对比（随机选择一些组合）
    comparisons = [
        (0, 2),  # 轩辕 vs 黑鹰
        (0, 4),  # 轩辕 vs 精制
        (1, 3),  # 卓越 vs 铁爪
        (1, 5),  # 卓越 vs 改进
        (2, 5),  # 黑鹰 vs 改进
        (3, 6),  # 铁爪 vs 完好
        (4, 7),  # 精制 vs 修复
        (5, 8),  # 改进 vs 破损
        (0, 8),  # 轩辕 vs 破损
    ]
    for i, j in comparisons:
        higher = QUALITY_ORDER[i]
        lower = QUALITY_ORDER[j]
        qa_pairs.append({
            "instruction": "",
            "input": f"{higher}和{lower}哪个品质更高？",
            "output": f"{higher}品质更高，{higher}排第{i+1}，{lower}排第{j+1}。"
        })
        qa_pairs.append({
            "instruction": "",
            "input": f"{lower}和{higher}哪个品质更高？",
            "output": f"{higher}品质更高，{higher}排第{i+1}，{lower}排第{j+1}。"
        })

    # 6. 品质高低判断
    for i, q1 in enumerate(QUALITY_ORDER):
        for j, q2 in enumerate(QUALITY_ORDER):
            if i < j:  # q1 比 q2 高
                qa_pairs.append({
                    "instruction": "",
                    "input": f"{q1}品质比{q2}品质高吗？",
                    "output": f"是的，{q1}品质比{q2}品质高。"
                })
                qa_pairs.append({
                    "instruction": "",
                    "input": f"{q2}品质比{q1}品质高吗？",
                    "output": f"不是，{q2}品质比{q1}品质低。"
                })

    return qa_pairs


def main():
    random.seed(42)  # 固定随机种子，保证可复现

    csv_path = Path("/Users/guoyichen/EasonAI/LLaMA-Factory/item_name.csv")

    # 解析枪械
    guns = parse_guns_from_csv(csv_path)
    print(f"解析到 {len(guns)} 把枪类武器")

    # 解析装备
    armors = parse_armors_from_csv(csv_path)
    print(f"解析到 {len(armors)} 件装备")

    # 统计枪械各类型数量
    type_counts = defaultdict(int)
    quality_counts = defaultdict(int)
    for gun in guns:
        type_counts[gun["type"]] += 1
        quality_counts[gun["quality"]] += 1

    print("\n枪械类型分布:")
    for t in GUN_TYPES:
        print(f"  {t}: {type_counts[t]}")

    print("\n枪械品质分布:")
    for q in QUALITY_ORDER:
        if q in quality_counts:
            print(f"  {q}: {quality_counts[q]}")

    # 统计装备
    armor_type_counts = defaultdict(int)
    armor_level_counts = defaultdict(int)
    for armor in armors:
        armor_type_counts[armor["type"]] += 1
        armor_level_counts[armor["level"]] += 1

    print("\n装备类型分布:")
    for t in ARMOR_TYPES:
        print(f"  {t}: {armor_type_counts[t]}")

    print("\n装备等级分布:")
    for level in sorted(armor_level_counts.keys()):
        print(f"  {level}级: {armor_level_counts[level]}")

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
    armor_positive_count = 0
    armor_negative_count = 0

    # 枪械问答
    for gun in guns:
        # 1. 正例
        positive_qa = generate_positive_qa(gun)
        all_qa.extend(positive_qa)
        positive_count += len(positive_qa)

        # 2. 反例
        negative_qa = generate_negative_qa(gun)
        all_qa.extend(negative_qa)
        negative_count += len(negative_qa)

        # 3. 对比问答
        comparison_qa = generate_limited_comparison_qa(gun, guns_by_type, guns_by_quality, gun_base_names)
        all_qa.extend(comparison_qa)
        comparison_count += len(comparison_qa)

    # 品质定义和对比问答
    quality_def_qa = generate_quality_definition_qa()
    all_qa.extend(quality_def_qa)
    quality_def_count = len(quality_def_qa)

    # 列举类问答
    listing_qa = generate_listing_qa(guns, guns_by_type, guns_by_quality)
    all_qa.extend(listing_qa)
    listing_count = len(listing_qa)

    # 类型+品质混淆反例 - 强化类型精确识别
    type_quality_confusion_qa = generate_type_quality_confusion_qa(guns, guns_by_type)
    all_qa.extend(type_quality_confusion_qa)
    type_quality_confusion_count = len(type_quality_confusion_qa)

    print(f"\n生成问答数据: {len(all_qa)} 条")
    print(f"  枪械正例: {positive_count} 条")
    print(f"  枪械反例: {negative_count} 条")
    print(f"  枪械对比: {comparison_count} 条")
    print(f"  品质定义: {quality_def_count} 条")
    print(f"  列举问答: {listing_count} 条")
    print(f"  类型混淆反例: {type_quality_confusion_count} 条")

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
