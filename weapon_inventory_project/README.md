# Qwen2.5-1.5B 武器库存查询 - 词表扩充 + LoRA SFT

## 项目说明

使用 LLaMA-Factory 对 Qwen2.5-1.5B 进行词表扩充和 LoRA SFT 微调，用于武器库存查询任务。

## 文件说明

| 文件 | 说明 |
|------|------|
| `qwen2.5_weapon_inventory_train.yaml` | 训练配置文件 |
| `qwen2.5_weapon_inventory_export.yaml` | 模型导出配置文件 |
| `item_name.csv` | 原始词表文件（1247行） |
| `game_item_tokens.txt` | 处理后的唯一词元列表（1122个） |

## 配置要点

- **词表扩充**: 1122 个游戏物品词元
- **LoRA**: rank=8, target=all
- **关键配置**: `additional_target: embed_tokens,lm_head` (训练新词元的 embedding)
- **数据集**: 3000 条武器库存查询数据 (`data/weapon_inventory_sft.json`)

## 使用方法

### 1. 训练
```bash
llamafactory-cli train weapon_inventory_project/qwen2.5_weapon_inventory_train.yaml
```

### 2. 导出模型
```bash
llamafactory-cli export weapon_inventory_project/qwen2.5_weapon_inventory_export.yaml
```

### 3. 测试推理
```bash
llamafactory-cli chat weapon_inventory_project/qwen2.5_weapon_inventory_export.yaml
```

## 训练的模块

```
LoRA 适配器（低秩分解）:
├── q_proj, k_proj, v_proj, o_proj (Self-Attention)
└── up_proj, gate_proj, down_proj (MLP)

额外全参训练（通过 additional_target）:
├── embed_tokens (输入嵌入层)
└── lm_head (输出头)
```
