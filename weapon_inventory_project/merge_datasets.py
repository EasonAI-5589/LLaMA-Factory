#!/usr/bin/env python3
"""
合并 v5 和 v2_fixed 数据集
"""

import json
import random
from pathlib import Path

def main():
    # 加载数据
    v5_path = Path("/Users/guoyichen/EasonAI/LLaMA-Factory/data/weapon_inventory_sft_v5.json")
    v2_fixed_path = Path("/Users/guoyichen/EasonAI/LLaMA-Factory/data/weapon_inventory_sft_v2_fixed.json")

    with open(v5_path, "r", encoding="utf-8") as f:
        v5_data = json.load(f)

    with open(v2_fixed_path, "r", encoding="utf-8") as f:
        v2_data = json.load(f)

    print(f"v5 数据: {len(v5_data)} 条")
    print(f"v2_fixed 数据: {len(v2_data)} 条")

    # 合并，v5 优先（如果有重复 input，使用 v5 的答案）
    merged = []
    seen_inputs = set()

    # 先添加 v5
    for item in v5_data:
        inp = item["input"]
        if inp not in seen_inputs:
            seen_inputs.add(inp)
            merged.append(item)

    # 再添加 v2_fixed 中不重复的
    added_from_v2 = 0
    for item in v2_data:
        inp = item["input"]
        if inp not in seen_inputs:
            seen_inputs.add(inp)
            merged.append(item)
            added_from_v2 += 1

    print(f"\n从 v2_fixed 添加了 {added_from_v2} 条新数据")
    print(f"合并后总计: {len(merged)} 条")

    # 打乱顺序
    random.shuffle(merged)

    # 保存
    output_path = Path("/Users/guoyichen/EasonAI/LLaMA-Factory/data/weapon_inventory_sft_v5_merged.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"\n已保存到: {output_path}")

    # 显示新增的示例
    print("\n=== 从 v2 新增的数据示例 ===")
    v5_inputs = set(item["input"] for item in v5_data)
    new_from_v2 = [item for item in v2_data if item["input"] not in v5_inputs][:5]
    for i, item in enumerate(new_from_v2):
        print(f"\n[{i+1}]")
        print(f"  input: {item['input']}")
        print(f"  output: {item['output'][:80]}...")


if __name__ == "__main__":
    main()
