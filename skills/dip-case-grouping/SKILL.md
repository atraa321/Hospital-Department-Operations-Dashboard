---
name: "dip-case-grouping"
description: "DIP病历入组技能。根据病案数据的主诊断和手术操作匹配DIP分组规则，为病历自动生成DIP病种编码和分值。当用户需要为病历进行DIP分组、匹配病种编码或执行病历入组时调用。"
---

# DIP病历入组技能

本技能用于根据导入的病案数据，自动匹配DIP分组规则，为每条病历生成对应的DIP病种编码和分值。

## 前置条件

**重要：执行本技能前，请确保已完成以下数据导入**

1. **DIP分组规则已导入** - 需要先调用 `dip-group-import` 技能导入DIP分组目录
2. **病案数据已导入** - 需要先调用 `case-data-import` 技能导入病案出院病人数据

## 数据源文件

### 病案数据文件

病案数据位于 `基础数据/病案出院病人.xlsx`，包含以下字段：

| 字段名 | 说明 | 用于匹配 |
|-------|------|---------|
| 住院号 | 患者唯一标识 | 关联键 |
| 患者姓名 | 患者姓名 | - |
| 医师 | 主治医师 | - |
| 科室编号 | 科室编码 | - |
| 出院科室 | 出院科室名称 | - |
| 入院科室 | 入院科室名称 | - |
| 入院日期 | 入院时间 | - |
| 出院日期 | 出院时间 | - |
| 诊断类型 | 主要诊断/其他诊断 | 区分主诊断 |
| 诊断ICD | 诊断ICD-10编码 | **匹配键** |
| 诊断名称 | 诊断描述 | - |
| icd | ICD编码（用于DIP分组） | **匹配键** |
| icd3 | ICD-3位编码 | 备用匹配 |
| 手术icd | 手术ICD编码 | **匹配键** |
| 手术名称 | 手术名称 | - |

### DIP分组规则文件

DIP分组规则位于 `基础数据/平顶山2025年DIP2.0分组目录库.xlsx`，目录Sheet包含：

| 字段名 | 说明 |
|-------|------|
| 病种编码 | DIP病种编码（匹配结果） |
| 病种类型 | 1=核心病种，2=综合病种 |
| 主诊断代码 | 主诊断ICD-10编码 |
| 主诊断名称 | 主诊断名称 |
| 主要操作代码 | 主要操作/手术编码 |
| 主要操作名称 | 主要操作/手术名称 |
| 其他操作代码 | 其他操作编码 |
| 其他操作名称 | 其他操作名称 |
| 病种分值 | 病种分值/权重 |

## 匹配规则

### 核心匹配逻辑

DIP入组采用**优先级匹配**策略，按以下顺序进行匹配：

```
优先级1: 主诊断代码 + 主要操作代码（精确匹配）
    ↓ 未匹配
优先级2: 主诊断代码 + 其他操作代码（精确匹配）
    ↓ 未匹配
优先级3: 主诊断代码（无操作代码匹配）
    ↓ 未匹配
优先级4: 主诊断ICD-3位编码模糊匹配
    ↓ 未匹配
未入组: 标记为"未入组"病历
```

### 匹配规则详解

#### 规则1：主诊断+主要操作精确匹配（最高优先级）

当病历有手术/操作时，优先匹配：

```python
def match_diagnosis_with_operation(diagnosis_code, operation_code, dip_rules):
    match = dip_rules[
        (dip_rules['main_diagnosis_code'] == diagnosis_code) &
        (dip_rules['main_operation_code'] == operation_code)
    ]
    return match
```

#### 规则2：主诊断+其他操作匹配

如果主要操作未匹配，尝试匹配其他操作：

```python
def match_diagnosis_with_other_operation(diagnosis_code, operation_code, dip_rules):
    match = dip_rules[
        (dip_rules['main_diagnosis_code'] == diagnosis_code) &
        (dip_rules['other_operation_code'] == operation_code)
    ]
    return match
```

#### 规则3：仅主诊断匹配

对于内科病例（无手术/操作），仅匹配主诊断：

```python
def match_diagnosis_only(diagnosis_code, dip_rules):
    match = dip_rules[
        (dip_rules['main_diagnosis_code'] == diagnosis_code) &
        (dip_rules['main_operation_code'].isna()) &
        (dip_rules['other_operation_code'].isna())
    ]
    return match
```

#### 规则4：ICD-3位编码模糊匹配

当精确匹配失败时，使用ICD-3位编码进行模糊匹配：

```python
def match_icd3_fuzzy(icd3_code, operation_code, dip_rules):
    dip_rules['diagnosis_icd3'] = dip_rules['main_diagnosis_code'].str[:3]
    
    if pd.notna(operation_code):
        match = dip_rules[
            (dip_rules['diagnosis_icd3'] == icd3_code) &
            (dip_rules['main_operation_code'] == operation_code)
        ]
        if len(match) == 0:
            match = dip_rules[
                (dip_rules['diagnosis_icd3'] == icd3_code) &
                (dip_rules['main_operation_code'].isna())
            ]
    else:
        match = dip_rules[
            (dip_rules['diagnosis_icd3'] == icd3_code) &
            (dip_rules['main_operation_code'].isna())
        ]
    return match
```

## 数据预处理

### 步骤1：提取主要诊断

病案数据中同一住院号可能有多条诊断记录，需要提取主要诊断：

```python
def extract_main_diagnosis(df_case):
    main_diagnosis = df_case[df_case['诊断类型'] == '主要诊断'].copy()
    main_diagnosis = main_diagnosis.groupby('住院号').first().reset_index()
    return main_diagnosis
```

### 步骤2：聚合手术信息

将同一患者的手术信息聚合：

```python
def aggregate_surgery_info(df_case):
    surgery_info = df_case[['住院号', '手术icd', '手术名称']].dropna(subset=['手术icd'])
    surgery_info = surgery_info.groupby('住院号').agg({
        '手术icd': lambda x: ','.join(x.dropna().unique()),
        '手术名称': lambda x: ','.join(x.dropna().unique())
    }).reset_index()
    return surgery_info
```

### 步骤3：合并患者完整信息

```python
def merge_patient_info(main_diagnosis, surgery_info):
    patient_info = main_diagnosis.merge(
        surgery_info, 
        on='住院号', 
        how='left'
    )
    return patient_info
```

## 完整入组流程

```python
import pandas as pd
import numpy as np

def dip_case_grouping(case_file, dip_rule_file, output_file=None):
    df_case = pd.read_excel(case_file)
    
    xlsx = pd.ExcelFile(dip_rule_file)
    df_dip = pd.read_excel(xlsx, sheet_name='目录')
    
    column_mapping = {
        '序号': 'id',
        '病种编码': 'dip_code',
        '病种类型（1.核心病种；2.综合病种）': 'dip_type',
        '主诊断代码': 'main_diagnosis_code',
        '主诊断名称': 'main_diagnosis_name',
        '主要操作代码': 'main_operation_code',
        '主要操作名称': 'main_operation_name',
        '其他操作代码': 'other_operation_code',
        '其他操作名称': 'other_operation_name',
        '病种分值': 'score'
    }
    df_dip = df_dip.rename(columns=column_mapping)
    df_dip = df_dip.dropna(subset=['dip_code', 'main_diagnosis_code'])
    
    main_diagnosis = df_case[df_case['诊断类型'] == '主要诊断'].copy()
    main_diagnosis = main_diagnosis.groupby('住院号').first().reset_index()
    
    surgery_info = df_case[['住院号', '手术icd', '手术名称']].dropna(subset=['手术icd'])
    surgery_info = surgery_info.groupby('住院号').first().reset_index()
    
    patient_info = main_diagnosis.merge(surgery_info, on='住院号', how='left')
    
    results = []
    for _, row in patient_info.iterrows():
        patient_id = row['住院号']
        diagnosis_code = row.get('icd', row.get('诊断ICD'))
        icd3_code = row.get('icd3', diagnosis_code[:3] if pd.notna(diagnosis_code) else None)
        operation_code = row.get('手术icd')
        
        matched = None
        match_type = None
        
        if pd.notna(operation_code):
            matched = df_dip[
                (df_dip['main_diagnosis_code'] == diagnosis_code) &
                (df_dip['main_operation_code'] == operation_code)
            ]
            if len(matched) > 0:
                match_type = '主诊断+主要操作'
        
        if matched is None or len(matched) == 0:
            if pd.notna(operation_code):
                matched = df_dip[
                    (df_dip['main_diagnosis_code'] == diagnosis_code) &
                    (df_dip['other_operation_code'] == operation_code)
                ]
                if len(matched) > 0:
                    match_type = '主诊断+其他操作'
        
        if matched is None or len(matched) == 0:
            matched = df_dip[
                (df_dip['main_diagnosis_code'] == diagnosis_code) &
                (df_dip['main_operation_code'].isna()) &
                (df_dip['other_operation_code'].isna())
            ]
            if len(matched) > 0:
                match_type = '仅主诊断'
        
        if matched is None or len(matched) == 0:
            if pd.notna(icd3_code):
                df_dip['diagnosis_icd3'] = df_dip['main_diagnosis_code'].str[:3]
                
                if pd.notna(operation_code):
                    matched = df_dip[
                        (df_dip['diagnosis_icd3'] == icd3_code) &
                        (df_dip['main_operation_code'] == operation_code)
                    ]
                    if len(matched) > 0:
                        match_type = 'ICD3+操作'
                
                if len(matched) == 0:
                    matched = df_dip[
                        (df_dip['diagnosis_icd3'] == icd3_code) &
                        (df_dip['main_operation_code'].isna())
                    ]
                    if len(matched) > 0:
                        match_type = 'ICD3模糊'
        
        if matched is not None and len(matched) > 0:
            best_match = matched.iloc[0]
            results.append({
                '住院号': patient_id,
                '患者姓名': row.get('患者姓名'),
                '主诊断代码': diagnosis_code,
                '手术代码': operation_code,
                'DIP编码': best_match['dip_code'],
                'DIP类型': '核心病种' if best_match['dip_type'] == 1 else '综合病种',
                '病种分值': best_match['score'],
                '匹配方式': match_type,
                '入组状态': '已入组'
            })
        else:
            results.append({
                '住院号': patient_id,
                '患者姓名': row.get('患者姓名'),
                '主诊断代码': diagnosis_code,
                '手术代码': operation_code,
                'DIP编码': None,
                'DIP类型': None,
                '病种分值': None,
                '匹配方式': None,
                '入组状态': '未入组'
            })
    
    result_df = pd.DataFrame(results)
    
    if output_file:
        result_df.to_excel(output_file, index=False)
    
    return result_df

if __name__ == '__main__':
    case_file = '基础数据/病案出院病人.xlsx'
    dip_rule_file = '基础数据/平顶山2025年DIP2.0分组目录库.xlsx'
    output_file = '基础数据/processed/病历DIP入组结果.xlsx'
    
    result = dip_case_grouping(case_file, dip_rule_file, output_file)
    
    print(f'总病历数: {len(result)}')
    print(f'已入组: {len(result[result["入组状态"] == "已入组"])}')
    print(f'未入组: {len(result[result["入组状态"] == "未入组"])}')
    print(f'入组率: {len(result[result["入组状态"] == "已入组"]) / len(result) * 100:.2f}%')
```

## 输出结果

### 入组结果文件

输出文件：`基础数据/processed/病历DIP入组结果.xlsx`

| 字段 | 说明 |
|-----|------|
| 住院号 | 患者住院号 |
| 患者姓名 | 患者姓名 |
| 主诊断代码 | 主诊断ICD编码 |
| 手术代码 | 手术/操作编码 |
| DIP编码 | 匹配的DIP病种编码 |
| DIP类型 | 核心病种/综合病种 |
| 病种分值 | 病种分值 |
| 匹配方式 | 匹配规则说明 |
| 入组状态 | 已入组/未入组 |

### 入组统计报告

执行完成后生成统计报告：

```
=== DIP病历入组统计报告 ===
总病历数: XXX
已入组: XXX
未入组: XXX
入组率: XX.XX%

=== 匹配方式分布 ===
主诊断+主要操作: XXX
主诊断+其他操作: XXX
仅主诊断: XXX
ICD3+操作: XXX
ICD3模糊: XXX

=== 未入组原因分析 ===
诊断编码不在规则中: XXX
操作编码不匹配: XXX
```

## 数据库更新

入组完成后，更新病案信息表：

```sql
UPDATE biz_case_info ci
JOIN (
    SELECT patient_id, dip_code, dip_name, dip_score
    FROM 入组结果表
) r ON ci.patient_id = r.patient_id
SET 
    ci.dip_code = r.dip_code,
    ci.dip_name = r.dip_name,
    ci.dip_score = r.dip_score,
    ci.update_time = NOW();
```

## 注意事项

1. **数据完整性**：确保病案数据中的诊断编码格式正确（ICD-10标准）
2. **编码规范**：诊断编码使用ICD-10标准，操作编码使用ICD-9-CM-3标准
3. **匹配优先级**：严格按照优先级顺序匹配，确保最精确匹配
4. **未入组处理**：未入组病历需要人工审核，可能需要补充诊断或调整规则
5. **分值计算**：入组后可计算DIP金额 = 病种分值 × 分值单价
6. **数据期间**：注意DIP规则的数据期间与病案数据期间匹配

## 常见问题处理

### 1. 入组率低
- 检查诊断编码格式是否正确
- 检查DIP规则是否覆盖该病种
- 考虑使用ICD-3位编码模糊匹配

### 2. 手术病历未入组
- 确认手术编码格式正确
- 检查DIP规则中是否包含该操作
- 尝试匹配其他操作代码

### 3. 多个匹配结果
- 优先选择核心病种（dip_type=1）
- 优先选择有操作代码的匹配
- 按病种分值排序选择

### 4. 诊断编码格式不一致
- 统一转换为大写
- 补全小数点位数
- 处理前导零问题
