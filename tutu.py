import tushare as ts
import json
import os
from datetime import datetime


def save_to_json(df, json_path):
    """提取指定字段，转换为JSON格式并写入文件"""
    if df is None or df.empty:
        print("无有效数据，跳过保存")
        return

    try:
        # 步骤1：筛选目标字段（确保只保留需要的字段）
        df_target = df[TARGET_FIELDS].copy()

        # 步骤2：数据清洗（处理空值、格式化数值）
        df_target = df_target.fillna(0)  # 空值填充为0
        # 格式化浮点数（如换手率保留4位小数）
        for col in df_target.columns:
            if df_target[col].dtype == 'float64':
                df_target[col] = df_target[col].apply(lambda x: round(x, 4))

        # 步骤3：转换为JSON格式（两种常用结构可选）
        # 结构1：列表+字典（推荐，易解析）→ [{"ts_code": "xxx", "name": "xxx"}, ...]
        json_data = df_target.to_dict(orient='records')

        # 结构2：字典+索引（如需保留行索引）→ {"0": {"ts_code": "xxx"}, "1": {...}}
        # json_data = df_target.to_dict(orient='index')

        # 步骤4：写入JSON文件（格式化+UTF-8编码）
        with open(json_path, 'w', encoding='utf-8') as f:
            # indent=4：格式化缩进，ensure_ascii=False：保留中文
            json.dump(
                json_data,
                f,
                ensure_ascii=False,
                indent=4,
                sort_keys=False  # 不排序字段，保持原顺序
            )

        # 补充：添加元数据（如获取时间）（可选）
        # json_data_with_meta = {
        #     "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        #     "data": json_data
        # }
        # with open(json_path, 'w', encoding='utf-8') as f:
        #     json.dump(json_data_with_meta, f, ensure_ascii=False, indent=4)

        print(f"\nJSON 文件保存成功！")
        print(f"文件路径：{os.path.abspath(json_path)}")
        print(f"提取的字段：{TARGET_FIELDS}")
        print(f"数据条数：{len(json_data)}")

        # 打印JSON预览（前2条）
        print("\nJSON 数据预览（前2条）：")
        print(json.dumps(json_data[:2], ensure_ascii=False, indent=4))

    except KeyError as e:
        print(f"字段提取失败：不存在字段 {e}")
    except Exception as e:
        print(f"保存 JSON 失败：{str(e)}")



# token秘钥
token = "168b63e0215b64bf1f7cc2558f3547bdd7b9d9168896e7ce6a14c79e7559"

pro = ts.pro_api(token)
pro._DataApi__token = token  # 需要添加的代码
pro._DataApi__http_url = 'http://42.194.163.97:5000'  #

TARGET_FIELDS = ['ts_code', 'name', 'turnover_rate', 'up_num', 'down_num']



def dc_member_to_json(trade_date='20251213', ts_code='BK1184.DC'):
    """
    获取 DC 成分股数据并保存为 JSON 文件
    :param trade_date: 交易日期（格式：YYYYMMDD）
    :param ts_code: DC 代码（如 BK1184.DC）
    :return: 保存后的 JSON 数据
    """
    try:
        # 2. 获取 DC 成分股数据
        df = pro.dc_member(trade_date=trade_date, ts_code=ts_code)

        # 3. 数据清洗（避免空值/重复值导致 JSON 解析异常）
        df = df.reset_index(drop=True)  # 重置索引
        df = df.dropna()  # 删除空值行
        df = df.drop_duplicates()  # 删除重复行

        # 4. 提取字段并转换为 JSON 格式（推荐列表式，每行一个字典）
        # orient='records'：按行转字典列表，可读性最强
        json_data = df.to_dict(orient='records')

        # 5. 写入 JSON 文件（解决中文乱码+格式化）
        file_name = f"dc_member_{ts_code}_{trade_date}.json"  # 自定义文件名
        with open(file_name, 'w', encoding='utf-8') as f:
            json.dump(
                json_data,
                f,
                ensure_ascii=False,  # 保留中文（关键）
                indent=4  # 格式化缩进，增强可读性
            )

        # 打印结果提示
        print(f"✅ 数据已保存为 JSON 文件：{file_name}")
        print(f"📊 数据字段：{df.columns.tolist()}")
        print(f"📈 数据行数：{len(json_data)}")
        print(f"🔍 第一条数据示例：\n{json_data[0] if json_data else '无数据'}")

        return json_data

    except Exception as e:
        print(f"❌ 执行失败：{str(e)}")
        # 常见报错原因及解决方案
        print("\n🔧 解决建议：")
        print("1. 检查 Tushare Token 是否有效（需实名认证）")
        print("2. 确认 trade_date 为有效交易日（非节假日/周末）")
        print("3. 检查 ts_code 格式是否正确（如 BK1184.DC）")
        print("4. 确保 Tushare 版本为最新：pip install tushare --upgrade")
        return None


if __name__ == "__main__":
    dc_member_to_json(trade_date='20251213', ts_code='BK1184.DC')
