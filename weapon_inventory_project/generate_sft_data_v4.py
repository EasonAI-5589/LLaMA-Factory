#!/usr/bin/env python3
"""
武器库存SFT数据集生成脚本 v4
核心改进：
1. 细粒度问答（v3基础）
2. 反向问答（属性→武器）
3. 否定样本（是/不是判断）
4. 组合条件查询（类型+品质）
5. 相似武器区分
"""

import json
import random
from pathlib import Path
from collections import defaultdict

# 品质等级排序（从高到低）
QUALITY_ORDER = ["轩辕", "黑鹰", "铁爪", "卓越", "精制", "改进", "完好", "修复", "破损"]

# 防具品质排序（从高到低，仅4-7级有）
ARMOR_QUALITY_ORDER = ["轩辕", "黑鹰", "铁爪"]

# 防具等级
ARMOR_LEVELS = [1, 2, 3, 4, 5, 6, 7]

# 防具类型
ARMOR_TYPES = ["头盔", "防弹衣"]

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

ALL_WEAPON_TYPES = list(WEAPON_TYPES.keys())

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
    name = item_name
    for quality in QUALITY_ORDER:
        name = name.replace(f"({quality})", "")
    for wtype in ["狙击枪", "冲锋枪", "突击步枪", "射手步枪", "轻机枪", "霰弹枪", "手枪"]:
        name = name.replace(wtype, "")
    return name.strip()


def parse_weapons_from_csv(csv_path: str) -> dict:
    """解析CSV文件，返回结构化的武器数据"""
    weapons_by_type = defaultdict(list)
    weapons_by_quality = defaultdict(list)
    weapons_by_model = defaultdict(list)
    weapons_by_type_quality = defaultdict(list)  # 新增：类型+品质组合
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
                # 类型+品质组合
                weapons_by_type_quality[(weapon_type, quality)].append(weapon_info)
            if model:
                weapons_by_model[model].append(weapon_info)

    return {
        "all": all_weapons,
        "by_type": dict(weapons_by_type),
        "by_quality": dict(weapons_by_quality),
        "by_model": dict(weapons_by_model),
        "by_type_quality": dict(weapons_by_type_quality)
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


def generate_negative_qa(weapon: dict) -> list:
    """生成否定样本问答"""
    name = weapon["name"]
    wtype = weapon["type"]
    quality = weapon["quality"]

    qa_pairs = []

    # 类型否定：问是否是其他类型
    other_types = [t for t in ALL_WEAPON_TYPES if t != wtype]
    for wrong_type in random.sample(other_types, min(2, len(other_types))):
        questions = [
            f"{name}是{wrong_type}吗？",
            f"{name}是不是{wrong_type}？",
        ]
        for q in questions:
            qa_pairs.append({
                "instruction": "判断武器类型",
                "input": q,
                "output": f"不是，{name}不是{wrong_type}，是{wtype}。",
                "task_type": "negative_type"
            })

    # 品质否定：问是否是其他品质
    if quality:
        other_qualities = [q for q in QUALITY_ORDER if q != quality]
        for wrong_quality in random.sample(other_qualities, min(2, len(other_qualities))):
            questions = [
                f"{name}是{wrong_quality}品质吗？",
                f"{name}是不是{wrong_quality}级？",
            ]
            for q in questions:
                qa_pairs.append({
                    "instruction": "判断武器品质",
                    "input": q,
                    "output": f"不是，{name}不是{wrong_quality}品质，是{quality}品质。",
                    "task_type": "negative_quality"
                })

    return qa_pairs


def generate_reverse_qa(weapons_by_type: dict, weapons_by_quality: dict) -> list:
    """生成反向问答（属性→武器）- 每个问题只生成一个答案，避免一对多"""
    qa_pairs = []

    # 类型反向：每种问法只保留一个答案
    for wtype, weapons in weapons_by_type.items():
        # 随机选一个武器作为标准答案
        weapon = random.choice(weapons)
        questions = [
            (f"说一个{wtype}", f"{weapon['name']}是{wtype}。"),
            (f"举例一个{wtype}", f"{weapon['name']}是{wtype}。"),
            (f"给我一个{wtype}的例子", f"{weapon['name']}是{wtype}。"),
        ]
        for q, a in questions:
            qa_pairs.append({
                "instruction": "查询武器示例",
                "input": q,
                "output": a,
                "task_type": "reverse_type"
            })

    # 品质反向：每种问法只保留一个答案
    for quality, weapons in weapons_by_quality.items():
        weapon = random.choice(weapons)
        questions = [
            (f"说一个{quality}品质的武器", f"{weapon['name']}是{quality}品质的{weapon['type']}。"),
            (f"举例一个{quality}级武器", f"{weapon['name']}是{quality}品质的{weapon['type']}。"),
            (f"给我一个{quality}品质的例子", f"{weapon['name']}是{quality}品质的{weapon['type']}。"),
        ]
        for q, a in questions:
            qa_pairs.append({
                "instruction": "查询武器示例",
                "input": q,
                "output": a,
                "task_type": "reverse_quality"
            })

    return qa_pairs


def generate_combo_condition_qa(weapons_by_type_quality: dict) -> list:
    """生成组合条件查询（类型+品质）"""
    qa_pairs = []

    # 有的组合
    for (wtype, quality), weapons in weapons_by_type_quality.items():
        if len(weapons) > 0:
            # 单个示例
            weapon = random.choice(weapons)
            questions = [
                f"有{quality}品质的{wtype}吗？",
                f"武器库里有没有{quality}级的{wtype}？",
            ]
            for q in questions:
                qa_pairs.append({
                    "instruction": "查询特定武器",
                    "input": q,
                    "output": f"有，比如{weapon['name']}就是{quality}品质的{wtype}。",
                    "task_type": "combo_exists"
                })

            # 列出多个（如果有）
            if len(weapons) >= 2:
                sampled = random.sample(weapons, min(3, len(weapons)))
                names = "、".join([w["name"] for w in sampled])
                qa_pairs.append({
                    "instruction": "查询特定武器",
                    "input": f"列出{quality}品质的{wtype}",
                    "output": f"{quality}品质的{wtype}有：{names}。",
                    "task_type": "combo_list"
                })

    # 没有的组合
    all_combos = set(weapons_by_type_quality.keys())
    for wtype in ALL_WEAPON_TYPES:
        for quality in QUALITY_ORDER:
            if (wtype, quality) not in all_combos:
                questions = [
                    f"有{quality}品质的{wtype}吗？",
                    f"武器库里有没有{quality}级的{wtype}？",
                ]
                for q in questions:
                    qa_pairs.append({
                        "instruction": "查询特定武器",
                        "input": q,
                        "output": f"没有，武器库中没有{quality}品质的{wtype}。",
                        "task_type": "combo_not_exists"
                    })

    return qa_pairs


def generate_type_query(weapons_by_type: dict, wtype: str) -> list:
    """生成类型查询（只列出少量武器）"""
    weapons = weapons_by_type.get(wtype, [])
    if len(weapons) < 3:
        return []

    qa_pairs = []

    for _ in range(20):
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

    for _ in range(15):
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


# ============ 新增：武器区分性问答 ============

def generate_model_comparison_qa(weapons_by_type: dict, weapons_by_model: dict) -> list:
    """生成同类型不同型号对比问答 - 使用完整武器名称"""
    qa_pairs = []

    for wtype, weapons in weapons_by_type.items():
        # 获取该类型下所有不同的型号，构建完整名称
        models = list(set(w["model"] for w in weapons if w["model"]))
        if len(models) < 2:
            continue

        # 两两对比
        for i, model1 in enumerate(models):
            for model2 in models[i+1:]:
                # 完整名称
                full_name1 = f"{model1}{wtype}"
                full_name2 = f"{model2}{wtype}"

                # 问：A和B有什么区别？
                qa_pairs.append({
                    "instruction": "对比武器型号",
                    "input": f"{full_name1}和{full_name2}有什么区别？",
                    "output": f"{full_name1}和{full_name2}都是{wtype}类型，但它们是不同的武器型号。",
                    "task_type": "model_comparison"
                })

                # 问：A和B都是XX类型吗？
                qa_pairs.append({
                    "instruction": "确认武器类型",
                    "input": f"{full_name1}和{full_name2}都是{wtype}吗？",
                    "output": f"是的，{full_name1}和{full_name2}都属于{wtype}类型。",
                    "task_type": "model_comparison"
                })

                # 问：A是不是B？（易混淆澄清）
                qa_pairs.append({
                    "instruction": "区分武器型号",
                    "input": f"{full_name1}是{full_name2}吗？",
                    "output": f"不是。{full_name1}和{full_name2}是两种不同的{wtype}型号。",
                    "task_type": "model_comparison"
                })

    return qa_pairs


def generate_type_difference_qa(weapons_by_type: dict) -> list:
    """生成不同类型武器区分问答 - 使用完整武器名称"""
    qa_pairs = []

    type_list = list(weapons_by_type.keys())

    # 两两对比类型
    for i, type1 in enumerate(type_list):
        for type2 in type_list[i+1:]:
            # 获取每种类型的示例型号，构建完整名称
            models1 = list(set(w["model"] for w in weapons_by_type[type1] if w["model"]))[:3]
            models2 = list(set(w["model"] for w in weapons_by_type[type2] if w["model"]))[:3]

            # 使用完整名称
            full_names1 = [f"{m}{type1}" for m in models1]
            full_names2 = [f"{m}{type2}" for m in models2]

            examples1 = "、".join(full_names1) if full_names1 else type1
            examples2 = "、".join(full_names2) if full_names2 else type2

            # 问：两种类型有什么区别？
            qa_pairs.append({
                "instruction": "区分武器类型",
                "input": f"{type1}和{type2}有什么区别？",
                "output": f"{type1}和{type2}是不同的武器类型。{type1}包括{examples1}等，{type2}包括{examples2}等。",
                "task_type": "type_difference"
            })

            qa_pairs.append({
                "instruction": "区分武器类型",
                "input": f"{type1}和{type2}有什么不同？",
                "output": f"{type1}和{type2}是两种不同的武器类型。",
                "task_type": "type_difference"
            })

            # 取一个完整名称问它是type1还是type2
            if full_names1:
                full_name = full_names1[0]
                qa_pairs.append({
                    "instruction": "判断武器类型",
                    "input": f"{full_name}是{type1}还是{type2}？",
                    "output": f"{full_name}是{type1}，不是{type2}。",
                    "task_type": "type_difference"
                })

            if full_names2:
                full_name = full_names2[0]
                qa_pairs.append({
                    "instruction": "判断武器类型",
                    "input": f"{full_name}是{type1}还是{type2}？",
                    "output": f"{full_name}是{type2}，不是{type1}。",
                    "task_type": "type_difference"
                })

    return qa_pairs


def generate_model_identity_qa(weapons_by_model: dict) -> list:
    """生成型号识别强化问答 - 使用完整武器名称"""
    qa_pairs = []

    for model, weapons in weapons_by_model.items():
        if len(weapons) < 1 or len(model) < 2:
            continue

        wtype = weapons[0]["type"]
        full_name = f"{model}{wtype}"

        # 问：XX是什么类型？（用完整名称）
        qa_pairs.append({
            "instruction": "识别武器型号",
            "input": f"{full_name}是什么类型的武器？",
            "output": f"{full_name}是{wtype}类型的武器。",
            "task_type": "model_identity"
        })

        qa_pairs.append({
            "instruction": "识别武器型号",
            "input": f"{full_name}属于哪种武器？",
            "output": f"{full_name}属于{wtype}类型。",
            "task_type": "model_identity"
        })

        # 强化：XX是YY吗？（正确的类型）
        qa_pairs.append({
            "instruction": "确认武器类型",
            "input": f"{full_name}是{wtype}吗？",
            "output": f"是的，{full_name}是{wtype}。",
            "task_type": "model_identity"
        })

    return qa_pairs


def generate_confusion_clarification_qa(weapons_by_type: dict, weapons_by_model: dict) -> list:
    """生成易混淆武器澄清问答 - 使用完整武器名称"""
    qa_pairs = []

    # 1. 同类型不同型号的混淆
    for wtype, weapons in weapons_by_type.items():
        models = list(set(w["model"] for w in weapons if w["model"]))

        for weapon in weapons:
            name = weapon["name"]
            model = weapon["model"]
            quality = weapon["quality"]

            if not model or not quality:
                continue

            # 找同类型的其他型号
            other_models = [m for m in models if m != model]
            if not other_models:
                continue

            # 随机选一个其他型号问（使用完整名称）
            other_model = random.choice(other_models)
            other_full_name = f"{other_model}{wtype}"
            my_full_name = f"{model}{wtype}"
            qa_pairs.append({
                "instruction": "澄清武器型号",
                "input": f"{name}是{other_full_name}吗？",
                "output": f"不是。{name}是{my_full_name}，不是{other_full_name}。它们是两种不同的{wtype}。",
                "task_type": "confusion_clarify"
            })

    # 2. 名称相似的型号混淆（如 M416 vs M417）- 使用完整名称
    similar_pairs = [
        ("M416", "M417", "突击步枪", "射手步枪"),
        ("M24", "M249", "狙击枪", "轻机枪"),
        ("MK12", "MK14", "射手步枪", "射手步枪"),
        ("P90", "P92", "冲锋枪", "手枪"),
        ("P18C", "P1911", "手枪", "手枪"),
    ]

    for m1, m2, t1, t2 in similar_pairs:
        full_name1 = f"{m1}{t1}"
        full_name2 = f"{m2}{t2}"

        if t1 == t2:
            qa_pairs.append({
                "instruction": "区分相似武器",
                "input": f"{full_name1}和{full_name2}是同一种武器吗？",
                "output": f"不是。{full_name1}和{full_name2}是两种不同的{t1}型号。",
                "task_type": "confusion_clarify"
            })
        else:
            qa_pairs.append({
                "instruction": "区分相似武器",
                "input": f"{full_name1}和{full_name2}是同一种武器吗？",
                "output": f"不是。{full_name1}是{t1}，{full_name2}是{t2}，它们是不同类型的武器。",
                "task_type": "confusion_clarify"
            })

            qa_pairs.append({
                "instruction": "区分相似武器",
                "input": f"{full_name1}和{full_name2}有什么区别？",
                "output": f"{full_name1}属于{t1}类型，{full_name2}属于{t2}类型，它们是完全不同的武器。",
                "task_type": "confusion_clarify"
            })

    return qa_pairs


def generate_type_definition_qa(weapons_by_type: dict) -> list:
    """生成武器类型定义问答 - 使用完整武器名称"""
    qa_pairs = []

    # 问：什么是XX？
    for wtype, weapons in weapons_by_type.items():
        models = list(set(w["model"] for w in weapons if w["model"]))[:5]
        # 使用完整名称
        full_names = [f"{m}{wtype}" for m in models]
        full_names_str = "、".join(full_names) if full_names else ""

        qa_pairs.append({
            "instruction": "解释武器类型",
            "input": f"什么是{wtype}？",
            "output": f"{wtype}是一种武器类型。武器库中的{wtype}包括{full_names_str}等。",
            "task_type": "type_definition"
        })

        qa_pairs.append({
            "instruction": "查询武器类型",
            "input": f"武器库里有多少种{wtype}？",
            "output": f"武器库中有多种{wtype}，包括：{full_names_str}等。",
            "task_type": "type_definition"
        })

    # 问：武器库有哪些武器类型？
    all_types = "、".join(list(weapons_by_type.keys()))
    qa_pairs.append({
        "instruction": "查询武器类型",
        "input": "武器库有哪些武器类型？",
        "output": f"武器库中的武器类型包括：{all_types}。",
        "task_type": "type_definition"
    })

    qa_pairs.append({
        "instruction": "查询武器类型",
        "input": "武器有几种类型？",
        "output": f"武器库中有{len(weapons_by_type)}种武器类型：{all_types}。",
        "task_type": "type_definition"
    })

    return qa_pairs


# ============ 防具相关函数 ============

def parse_armor_items(csv_path: str) -> dict:
    """解析防具数据（头盔和防弹衣）"""
    helmets = []  # 头盔
    vests = []    # 防弹衣
    helmets_by_level = defaultdict(list)
    vests_by_level = defaultdict(list)
    helmets_by_quality = defaultdict(list)
    vests_by_quality = defaultdict(list)

    with open(csv_path, "r", encoding="utf-8") as f:
        for line in f:
            item_name = line.strip()
            if not item_name:
                continue

            # 跳过礼包、物资箱等
            if "礼包" in item_name or "物资箱" in item_name:
                continue

            # 跳过子物品（可选：也可以包含）
            if item_name.startswith("子物品-"):
                continue

            # 解析头盔
            if "头盔" in item_name and "级头盔" in item_name:
                armor_info = parse_single_armor(item_name, "头盔")
                if armor_info:
                    helmets.append(armor_info)
                    helmets_by_level[armor_info["level"]].append(armor_info)
                    if armor_info["quality"]:
                        helmets_by_quality[armor_info["quality"]].append(armor_info)

            # 解析防弹衣
            elif "防弹衣" in item_name and "级防弹衣" in item_name:
                armor_info = parse_single_armor(item_name, "防弹衣")
                if armor_info:
                    vests.append(armor_info)
                    vests_by_level[armor_info["level"]].append(armor_info)
                    if armor_info["quality"]:
                        vests_by_quality[armor_info["quality"]].append(armor_info)

    return {
        "helmets": helmets,
        "vests": vests,
        "helmets_by_level": dict(helmets_by_level),
        "vests_by_level": dict(vests_by_level),
        "helmets_by_quality": dict(helmets_by_quality),
        "vests_by_quality": dict(vests_by_quality),
        "all_armors": helmets + vests
    }


def parse_single_armor(item_name: str, armor_type: str) -> dict:
    """解析单个防具的信息"""
    import re

    # 提取等级
    level_match = re.search(r"(\d)级", item_name)
    if not level_match:
        return None
    level = int(level_match.group(1))

    # 提取品质
    quality = None
    for q in ARMOR_QUALITY_ORDER:
        if f"({q})" in item_name:
            quality = q
            break

    # 判断是否是特殊款
    is_special = "·" in item_name
    special_name = None
    if is_special:
        # 提取特殊款名称，如 "墨守"、"特劳斯"
        special_match = re.search(r"·(.+)$", item_name)
        if special_match:
            special_name = special_match.group(1)

    return {
        "name": item_name,
        "type": armor_type,
        "level": level,
        "quality": quality,
        "is_special": is_special,
        "special_name": special_name
    }


def generate_armor_level_qa(armor_data: dict) -> list:
    """生成防具等级查询问答"""
    qa_pairs = []

    all_armors = armor_data["all_armors"]

    for armor in all_armors:
        name = armor["name"]
        level = armor["level"]
        atype = armor["type"]

        # 问：XX是几级？
        questions = [
            f"{name}是几级{atype}？",
            f"{name}是什么等级？",
            f"查询{name}的等级",
        ]

        for q in questions:
            qa_pairs.append({
                "instruction": "查询防具等级",
                "input": q,
                "output": f"{name}是{level}级{atype}。",
                "task_type": "armor_level"
            })

    return qa_pairs


def generate_armor_quality_qa(armor_data: dict) -> list:
    """生成防具品质查询问答"""
    qa_pairs = []

    all_armors = armor_data["all_armors"]

    for armor in all_armors:
        name = armor["name"]
        quality = armor["quality"]
        level = armor["level"]
        atype = armor["type"]

        questions = [
            f"{name}是什么品质？",
            f"{name}的品质是什么？",
            f"查询{name}的品质",
        ]

        if quality:
            answer = f"{name}是{quality}品质。"
        else:
            answer = f"{name}是普通品质，没有特殊品质后缀。"

        for q in questions:
            qa_pairs.append({
                "instruction": "查询防具品质",
                "input": q,
                "output": answer,
                "task_type": "armor_quality"
            })

    return qa_pairs


def generate_armor_type_qa(armor_data: dict) -> list:
    """生成防具类型识别问答"""
    qa_pairs = []

    all_armors = armor_data["all_armors"]

    for armor in all_armors:
        name = armor["name"]
        atype = armor["type"]
        other_type = "防弹衣" if atype == "头盔" else "头盔"

        # 问：XX是头盔还是防弹衣？
        qa_pairs.append({
            "instruction": "识别防具类型",
            "input": f"{name}是头盔还是防弹衣？",
            "output": f"{name}是{atype}。",
            "task_type": "armor_type"
        })

        qa_pairs.append({
            "instruction": "识别防具类型",
            "input": f"{name}属于什么防具类型？",
            "output": f"{name}是{atype}类型。",
            "task_type": "armor_type"
        })

        # 问：XX是YY吗？（正确）
        qa_pairs.append({
            "instruction": "确认防具类型",
            "input": f"{name}是{atype}吗？",
            "output": f"是的，{name}是{atype}。",
            "task_type": "armor_type"
        })

    return qa_pairs


def generate_armor_level_compare_qa(armor_data: dict) -> list:
    """生成防具等级对比问答"""
    qa_pairs = []

    # 头盔等级对比
    helmets = armor_data["helmets"]
    for i, h1 in enumerate(helmets):
        for h2 in helmets[i+1:]:
            if h1["level"] == h2["level"]:
                continue

            name1, level1 = h1["name"], h1["level"]
            name2, level2 = h2["name"], h2["level"]

            if level1 > level2:
                higher, lower = name1, name2
                higher_level, lower_level = level1, level2
            else:
                higher, lower = name2, name1
                higher_level, lower_level = level2, level1

            qa_pairs.append({
                "instruction": "对比防具等级",
                "input": f"{name1}和{name2}哪个等级更高？",
                "output": f"{higher}等级更高。{higher_level}级 > {lower_level}级。",
                "task_type": "armor_level_compare"
            })

    # 防弹衣等级对比
    vests = armor_data["vests"]
    for i, v1 in enumerate(vests):
        for v2 in vests[i+1:]:
            if v1["level"] == v2["level"]:
                continue

            name1, level1 = v1["name"], v1["level"]
            name2, level2 = v2["name"], v2["level"]

            if level1 > level2:
                higher, lower = name1, name2
                higher_level, lower_level = level1, level2
            else:
                higher, lower = name2, name1
                higher_level, lower_level = level2, level1

            qa_pairs.append({
                "instruction": "对比防具等级",
                "input": f"{name1}和{name2}哪个等级更高？",
                "output": f"{higher}等级更高。{higher_level}级 > {lower_level}级。",
                "task_type": "armor_level_compare"
            })

    # 限制数量，避免太多
    if len(qa_pairs) > 200:
        qa_pairs = random.sample(qa_pairs, 200)

    return qa_pairs


def generate_armor_quality_compare_qa(armor_data: dict) -> list:
    """生成防具品质对比问答"""
    qa_pairs = []
    quality_order = {"轩辕": 0, "黑鹰": 1, "铁爪": 2}

    # 同等级不同品质对比
    for level in ARMOR_LEVELS:
        # 头盔
        helmets_at_level = armor_data["helmets_by_level"].get(level, [])
        quality_helmets = [h for h in helmets_at_level if h["quality"]]

        for i, h1 in enumerate(quality_helmets):
            for h2 in quality_helmets[i+1:]:
                if h1["quality"] == h2["quality"]:
                    continue

                name1, q1 = h1["name"], h1["quality"]
                name2, q2 = h2["name"], h2["quality"]

                if quality_order[q1] < quality_order[q2]:
                    better, worse = name1, name2
                    better_q = q1
                else:
                    better, worse = name2, name1
                    better_q = q2

                qa_pairs.append({
                    "instruction": "对比防具品质",
                    "input": f"{name1}和{name2}哪个品质更好？",
                    "output": f"{better}品质更好。品质排序：轩辕 > 黑鹰 > 铁爪。",
                    "task_type": "armor_quality_compare"
                })

        # 防弹衣
        vests_at_level = armor_data["vests_by_level"].get(level, [])
        quality_vests = [v for v in vests_at_level if v["quality"]]

        for i, v1 in enumerate(quality_vests):
            for v2 in quality_vests[i+1:]:
                if v1["quality"] == v2["quality"]:
                    continue

                name1, q1 = v1["name"], v1["quality"]
                name2, q2 = v2["name"], v2["quality"]

                if quality_order[q1] < quality_order[q2]:
                    better, worse = name1, name2
                else:
                    better, worse = name2, name1

                qa_pairs.append({
                    "instruction": "对比防具品质",
                    "input": f"{name1}和{name2}哪个品质更好？",
                    "output": f"{better}品质更好。品质排序：轩辕 > 黑鹰 > 铁爪。",
                    "task_type": "armor_quality_compare"
                })

    return qa_pairs


def generate_armor_existence_qa(armor_data: dict) -> list:
    """生成防具存在性查询问答"""
    qa_pairs = []

    # 各等级头盔存在性
    for level in ARMOR_LEVELS:
        helmets = armor_data["helmets_by_level"].get(level, [])
        if helmets:
            names = "、".join([h["name"] for h in helmets])
            qa_pairs.append({
                "instruction": "查询防具存在",
                "input": f"武器库有{level}级头盔吗？",
                "output": f"有。武器库中有{names}。",
                "task_type": "armor_existence"
            })

    # 各等级防弹衣存在性
    for level in ARMOR_LEVELS:
        vests = armor_data["vests_by_level"].get(level, [])
        if vests:
            names = "、".join([v["name"] for v in vests])
            qa_pairs.append({
                "instruction": "查询防具存在",
                "input": f"武器库有{level}级防弹衣吗？",
                "output": f"有。武器库中有{names}。",
                "task_type": "armor_existence"
            })

    # 不存在的等级
    qa_pairs.append({
        "instruction": "查询防具存在",
        "input": "有8级头盔吗？",
        "output": "没有。武器库中头盔最高等级为7级。",
        "task_type": "armor_existence"
    })

    qa_pairs.append({
        "instruction": "查询防具存在",
        "input": "有8级防弹衣吗？",
        "output": "没有。武器库中防弹衣最高等级为7级。",
        "task_type": "armor_existence"
    })

    qa_pairs.append({
        "instruction": "查询防具存在",
        "input": "有0级头盔吗？",
        "output": "没有。武器库中头盔最低等级为1级。",
        "task_type": "armor_existence"
    })

    return qa_pairs


def generate_armor_negative_qa(armor_data: dict) -> list:
    """生成防具否定判断问答"""
    qa_pairs = []

    all_armors = armor_data["all_armors"]

    for armor in all_armors:
        name = armor["name"]
        level = armor["level"]
        atype = armor["type"]
        quality = armor["quality"]
        other_type = "防弹衣" if atype == "头盔" else "头盔"

        # 类型否定
        qa_pairs.append({
            "instruction": "判断防具类型",
            "input": f"{name}是{other_type}吗？",
            "output": f"不是。{name}是{atype}，不是{other_type}。",
            "task_type": "armor_negative"
        })

        # 等级否定（问其他等级）
        other_levels = [l for l in ARMOR_LEVELS if l != level]
        for wrong_level in random.sample(other_levels, min(2, len(other_levels))):
            qa_pairs.append({
                "instruction": "判断防具等级",
                "input": f"{name}是{wrong_level}级{atype}吗？",
                "output": f"不是。{name}是{level}级{atype}，不是{wrong_level}级{atype}。",
                "task_type": "armor_negative"
            })

        # 品质否定
        if quality:
            other_qualities = [q for q in ARMOR_QUALITY_ORDER if q != quality]
            for wrong_quality in other_qualities:
                qa_pairs.append({
                    "instruction": "判断防具品质",
                    "input": f"{name}是{wrong_quality}品质吗？",
                    "output": f"不是。{name}是{quality}品质，不是{wrong_quality}品质。",
                    "task_type": "armor_negative"
                })

    return qa_pairs


def generate_armor_special_qa(armor_data: dict) -> list:
    """生成特殊款防具识别问答"""
    qa_pairs = []

    all_armors = armor_data["all_armors"]
    special_armors = [a for a in all_armors if a["is_special"]]

    for armor in special_armors:
        name = armor["name"]
        level = armor["level"]
        atype = armor["type"]
        special_name = armor["special_name"]

        qa_pairs.append({
            "instruction": "识别特殊防具",
            "input": f"{name}是什么？",
            "output": f"{name}是{level}级{atype}的特殊款式。",
            "task_type": "armor_special"
        })

        qa_pairs.append({
            "instruction": "识别特殊防具",
            "input": f"{name}和普通{level}级{atype}有什么区别？",
            "output": f"{name}是{level}级{atype}的特殊款式，都是{level}级{atype}。",
            "task_type": "armor_special"
        })

        qa_pairs.append({
            "instruction": "识别特殊防具",
            "input": f"{name}是{level}级{atype}吗？",
            "output": f"是的，{name}是{level}级{atype}的特殊款式。",
            "task_type": "armor_special"
        })

    return qa_pairs


def generate_armor_definition_qa(armor_data: dict) -> list:
    """生成防具类型定义问答"""
    qa_pairs = []

    # 武器库有哪些防具类型？
    qa_pairs.append({
        "instruction": "查询防具类型",
        "input": "武器库有哪些防具类型？",
        "output": "武器库中的防具类型包括：头盔和防弹衣。",
        "task_type": "armor_definition"
    })

    qa_pairs.append({
        "instruction": "查询防具类型",
        "input": "防具有哪些种类？",
        "output": "防具分为两种：头盔和防弹衣。",
        "task_type": "armor_definition"
    })

    # 头盔等级说明
    helmet_levels = sorted(armor_data["helmets_by_level"].keys())
    min_level, max_level = min(helmet_levels), max(helmet_levels)
    qa_pairs.append({
        "instruction": "查询防具等级",
        "input": "头盔有哪些等级？",
        "output": f"头盔有{min_level}级到{max_level}级，共{len(helmet_levels)}个等级。4级及以上有铁爪、黑鹰、轩辕品质版本。",
        "task_type": "armor_definition"
    })

    # 防弹衣等级说明
    vest_levels = sorted(armor_data["vests_by_level"].keys())
    min_level, max_level = min(vest_levels), max(vest_levels)
    qa_pairs.append({
        "instruction": "查询防具等级",
        "input": "防弹衣有哪些等级？",
        "output": f"防弹衣有{min_level}级到{max_level}级，共{len(vest_levels)}个等级。4级及以上有铁爪、黑鹰、轩辕品质版本。",
        "task_type": "armor_definition"
    })

    # 品质说明
    qa_pairs.append({
        "instruction": "查询防具品质",
        "input": "防具有哪些品质？",
        "output": "防具品质从高到低为：轩辕 > 黑鹰 > 铁爪 > 普通。4级及以上的防具才有品质区分。",
        "task_type": "armor_definition"
    })

    qa_pairs.append({
        "instruction": "查询防具品质",
        "input": "防具品质排序是什么？",
        "output": "防具品质从高到低为：轩辕 > 黑鹰 > 铁爪。1-3级防具没有品质后缀。",
        "task_type": "armor_definition"
    })

    return qa_pairs


def main():
    # 解析武器数据
    csv_path = Path("/Users/guoyichen/EasonAI/LLaMA-Factory/item_name.csv")
    weapons_data = parse_weapons_from_csv(csv_path)

    print(f"解析到 {len(weapons_data['all'])} 个武器")
    print(f"类型+品质组合数: {len(weapons_data['by_type_quality'])}")

    all_qa = []

    # 1. 单武器正向问答（核心）
    print("\n生成单武器问答...")
    for weapon in weapons_data["all"]:
        qa_pairs = generate_single_weapon_qa(weapon)
        all_qa.extend(qa_pairs)
        qa_pairs = generate_is_weapon_qa(weapon)
        all_qa.extend(qa_pairs)
    print(f"  单武器问答: {len(all_qa)} 条")

    # 2. 否定样本
    print("生成否定样本...")
    neg_count = 0
    for weapon in weapons_data["all"]:
        qa_pairs = generate_negative_qa(weapon)
        all_qa.extend(qa_pairs)
        neg_count += len(qa_pairs)
    print(f"  否定样本: {neg_count} 条")

    # 3. 反向问答
    print("生成反向问答...")
    reverse_qa = generate_reverse_qa(weapons_data["by_type"], weapons_data["by_quality"])
    all_qa.extend(reverse_qa)
    print(f"  反向问答: {len(reverse_qa)} 条")

    # 4. 组合条件查询
    print("生成组合条件查询...")
    combo_qa = generate_combo_condition_qa(weapons_data["by_type_quality"])
    all_qa.extend(combo_qa)
    print(f"  组合条件: {len(combo_qa)} 条")

    # 5. 类型查询
    print("生成类型查询...")
    type_qa_count = 0
    for wtype in WEAPON_TYPES.keys():
        qa_pairs = generate_type_query(weapons_data["by_type"], wtype)
        all_qa.extend(qa_pairs)
        type_qa_count += len(qa_pairs)
    print(f"  类型查询: {type_qa_count} 条")

    # 6. 品质查询
    print("生成品质查询...")
    quality_qa_count = 0
    for quality in QUALITY_ORDER:
        qa_pairs = generate_quality_query(weapons_data["by_quality"], quality)
        all_qa.extend(qa_pairs)
        quality_qa_count += len(qa_pairs)
    print(f"  品质查询: {quality_qa_count} 条")

    # 7. 型号查询
    print("生成型号查询...")
    model_qa = generate_model_query(weapons_data["by_model"])
    all_qa.extend(model_qa)
    print(f"  型号查询: {len(model_qa)} 条")

    # 8. 品质对比
    print("生成品质对比...")
    compare_qa = generate_quality_comparison()
    all_qa.extend(compare_qa)
    print(f"  品质对比: {len(compare_qa)} 条")

    # ============ 新增：武器区分性问答 ============

    # 9. 同类型型号对比
    print("生成型号对比...")
    model_compare_qa = generate_model_comparison_qa(weapons_data["by_type"], weapons_data["by_model"])
    all_qa.extend(model_compare_qa)
    print(f"  型号对比: {len(model_compare_qa)} 条")

    # 10. 不同类型区分
    print("生成类型区分...")
    type_diff_qa = generate_type_difference_qa(weapons_data["by_type"])
    all_qa.extend(type_diff_qa)
    print(f"  类型区分: {len(type_diff_qa)} 条")

    # 11. 型号识别强化
    print("生成型号识别...")
    model_id_qa = generate_model_identity_qa(weapons_data["by_model"])
    all_qa.extend(model_id_qa)
    print(f"  型号识别: {len(model_id_qa)} 条")

    # 12. 易混淆澄清
    print("生成易混淆澄清...")
    confusion_qa = generate_confusion_clarification_qa(weapons_data["by_type"], weapons_data["by_model"])
    all_qa.extend(confusion_qa)
    print(f"  易混淆澄清: {len(confusion_qa)} 条")

    # 13. 类型定义
    print("生成类型定义...")
    type_def_qa = generate_type_definition_qa(weapons_data["by_type"])
    all_qa.extend(type_def_qa)
    print(f"  类型定义: {len(type_def_qa)} 条")

    # ============ 新增：防具问答 ============
    print("\n" + "="*50)
    print("开始生成防具数据...")
    print("="*50)

    # 解析防具数据
    armor_data = parse_armor_items(csv_path)
    print(f"解析到 {len(armor_data['helmets'])} 个头盔")
    print(f"解析到 {len(armor_data['vests'])} 个防弹衣")

    # 14. 防具等级查询
    print("\n生成防具等级查询...")
    armor_level_qa = generate_armor_level_qa(armor_data)
    all_qa.extend(armor_level_qa)
    print(f"  防具等级查询: {len(armor_level_qa)} 条")

    # 15. 防具品质查询
    print("生成防具品质查询...")
    armor_quality_qa = generate_armor_quality_qa(armor_data)
    all_qa.extend(armor_quality_qa)
    print(f"  防具品质查询: {len(armor_quality_qa)} 条")

    # 16. 防具类型识别
    print("生成防具类型识别...")
    armor_type_qa = generate_armor_type_qa(armor_data)
    all_qa.extend(armor_type_qa)
    print(f"  防具类型识别: {len(armor_type_qa)} 条")

    # 17. 防具等级对比
    print("生成防具等级对比...")
    armor_level_compare_qa = generate_armor_level_compare_qa(armor_data)
    all_qa.extend(armor_level_compare_qa)
    print(f"  防具等级对比: {len(armor_level_compare_qa)} 条")

    # 18. 防具品质对比
    print("生成防具品质对比...")
    armor_quality_compare_qa = generate_armor_quality_compare_qa(armor_data)
    all_qa.extend(armor_quality_compare_qa)
    print(f"  防具品质对比: {len(armor_quality_compare_qa)} 条")

    # 19. 防具存在性查询
    print("生成防具存在性查询...")
    armor_existence_qa = generate_armor_existence_qa(armor_data)
    all_qa.extend(armor_existence_qa)
    print(f"  防具存在性查询: {len(armor_existence_qa)} 条")

    # 20. 防具否定判断
    print("生成防具否定判断...")
    armor_negative_qa = generate_armor_negative_qa(armor_data)
    all_qa.extend(armor_negative_qa)
    print(f"  防具否定判断: {len(armor_negative_qa)} 条")

    # 21. 特殊款防具识别
    print("生成特殊款防具识别...")
    armor_special_qa = generate_armor_special_qa(armor_data)
    all_qa.extend(armor_special_qa)
    print(f"  特殊款防具识别: {len(armor_special_qa)} 条")

    # 22. 防具类型定义
    print("生成防具类型定义...")
    armor_def_qa = generate_armor_definition_qa(armor_data)
    all_qa.extend(armor_def_qa)
    print(f"  防具类型定义: {len(armor_def_qa)} 条")

    # 去重：同一个 input 只保留一条（保留第一个）
    print("\n去重处理...")
    seen_inputs = set()
    unique_qa = []
    for qa in all_qa:
        inp = qa.get("input", "")
        if inp not in seen_inputs:
            seen_inputs.add(inp)
            unique_qa.append(qa)
    print(f"  去重前: {len(all_qa)} 条")
    print(f"  去重后: {len(unique_qa)} 条")
    all_qa = unique_qa

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
    output_path = Path("/Users/guoyichen/EasonAI/LLaMA-Factory/data/weapon_inventory_sft_v4.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_qa, f, ensure_ascii=False, indent=2)

    print(f"\n数据已保存到: {output_path}")

    # 显示示例
    print("\n=== 数据类型示例 ===")
    sample_types = [
        "negative_type", "negative_quality",
        "model_comparison", "type_difference",
        "model_identity", "confusion_clarify", "type_definition",
        # 防具类型
        "armor_level", "armor_quality", "armor_type",
        "armor_level_compare", "armor_negative", "armor_definition"
    ]
    for task_type in sample_types:
        examples = [qa for qa in all_qa if qa["task_type"] == task_type][:2]
        for ex in examples:
            print(f"\n[{task_type}]")
            print(f"  Q: {ex['input']}")
            print(f"  A: {ex['output']}")


if __name__ == "__main__":
    main()
