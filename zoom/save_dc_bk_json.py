import akshare as ak
import json
import pandas as pd


def get_stock_concept_data_save_json():
    """
    获取股票概念板块数据，提取字段并保存为JSON文件
    """
    try:
        # 1. 获取原始数据
        df = ak.stock_board_concept_name_em()

        # 数据清洗（保证数据完整性）
        df = df.reset_index(drop=True).dropna().drop_duplicates()

        # 2. 提取字段（列名）
        fields = df.columns.tolist()
        print(f"提取的字段列表: {fields}")

        # 3. 格式1：结构化JSON（字段为key，对应值为列表）
        json_structured = {field: df[field].tolist() for field in fields}

        # 4. 格式2：列表式JSON（每行数据为一个字典，更易读取）
        json_list = df.to_dict(orient='records')  # orient='records' 按行转字典列表

        # 5. 保存JSON文件（指定编码为utf-8，避免中文乱码）
        # 保存结构化JSON
        with open("stock_concept_structured.json", "w", encoding="utf-8") as f:
            json.dump(json_structured, f, ensure_ascii=False, indent=4)

        # 保存列表式JSON（推荐，可读性更高）
        with open("stock_concept_list.json", "w", encoding="utf-8") as f:
            json.dump(json_list, f, ensure_ascii=False, indent=4)

        print("JSON文件保存成功！")
        print(f"\n结构化JSON示例（前2条）:")
        # 打印前2条结构化数据示例
        for k, v in json_structured.items():
            print(f"{k}: {v[:2]}")

        print(f"\n列表式JSON示例（第1条）:")
        print(json_list[0])

        return json_structured, json_list

    except Exception as e:
        print(f"执行失败: {e}")
        print("\n解决建议：")
        print("1. 升级akshare: pip install akshare --upgrade")
        print("2. 检查网络连接")
        return None, None


# 调用函数
structured_json, list_json = get_stock_concept_data_save_json()