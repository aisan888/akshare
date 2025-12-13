import akshare as ak
import json
import pandas as pd


def get_stock_data_save_json(data_type="concept"):
    """
    通用函数：获取股票板块数据（概念/行业）并保存为JSON
    :param data_type: 数据类型，"concept"=概念板块，"industry"=行业板块
    :return: 结构化JSON、列表式JSON
    """
    try:
        # 1. 根据类型获取对应数据
        if data_type == "concept":
            df = ak.stock_board_concept_name_em()
            file_prefix = "stock_concept"  # 概念板块文件前缀
        elif data_type == "industry":
            df = ak.stock_board_industry_name_em()
            file_prefix = "stock_industry"  # 行业板块文件前缀
        else:
            raise ValueError("data_type仅支持 'concept' 或 'industry'")

        # 2. 数据清洗（去空、去重、重置索引）
        df = df.reset_index(drop=True).dropna().drop_duplicates()

        # 3. 提取所有字段（列名）
        fields = df.columns.tolist()
        print(f"\n=== {data_type.upper()} 板块 ===")
        print(f"提取的字段列表: {fields}")
        print(f"有效数据行数: {len(df)}")

        # 4. 格式1：结构化JSON（字段为key，值为列表）
        json_structured = {field: df[field].tolist() for field in fields}

        # 5. 格式2：列表式JSON（每行一个字典，推荐）
        json_list = df.to_dict(orient='records')

        # 6. 保存JSON文件（避免中文乱码，格式化输出）
        # 保存结构化JSON
        struct_file = f"{file_prefix}_structured.json"
        with open(struct_file, "w", encoding="utf-8") as f:
            json.dump(json_structured, f, ensure_ascii=False, indent=4)

        # 保存列表式JSON
        list_file = f"{file_prefix}_list.json"
        with open(list_file, "w", encoding="utf-8") as f:
            json.dump(json_list, f, ensure_ascii=False, indent=4)

        print(f"✅ {data_type}板块JSON文件保存完成：")
        print(f"   - 结构化JSON: {struct_file}")
        print(f"   - 列表式JSON: {list_file}")

        # 打印第一条数据示例
        if json_list:
            print(f"\n第一条数据示例: {json_list[0]}")

        return json_structured, json_list

    except Exception as e:
        print(f"❌ 处理{data_type}板块失败: {e}")
        print("\n解决建议：")
        print("1. 升级akshare: pip install akshare --upgrade")
        print("2. 检查网络连接")
        return None, None


# ==================== 调用示例 ====================
# 1. 处理行业板块数据（核心需求）
industry_struct, industry_list = get_stock_data_save_json(data_type="industry")

# 2. 如需同时处理概念板块，取消注释即可
# concept_struct, concept_list = get_stock_data_save_json(data_type="concept")