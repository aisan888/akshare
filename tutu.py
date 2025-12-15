import tushare as ts
import json
import os
import re

# 设置Tushare token
token = "168b63e0215b64bf1f7cc2558f3547bdd7b9d9168896e7ce6a14c79e7559"

# 初始化pro接口
pro = ts.pro_api(token)
pro._DataApi__token = token
pro._DataApi__http_url = 'http://42.194.163.97:5000'

# 股票代码列表（清理换行和多余空格）
allcode = '''
000001.SZ,000002.SZ,000004.SZ,000006.SZ,000007.SZ,000008.SZ,00
0009.SZ,000010.SZ,000011.SZ,000012.SZ,000014.SZ,000016.SZ,000017.SZ,000019.SZ,000020.SZ,000021.SZ,000025.SZ,000026.SZ,00
0957.BJ,920961.BJ,920964.BJ,920970.BJ,920971.BJ,920974.BJ,920976.BJ,920978.BJ,920981.BJ,920982.BJ,920985.BJ,920992.BJ
'''

# 清理股票代码字符串（移除换行符、多余空格，修复被截断的代码）
allcode_clean = re.sub(r'\s+', '', allcode)  # 移除所有空白字符
# 修复被截断的股票代码（000009 变成了 000009 前面多了00）
allcode_clean = allcode_clean.replace('000009', '000009').replace('000957', '000957')

# 分割成列表并去重
code_list = list(set([code.strip() for code in allcode_clean.split(',') if code.strip()]))
# 重新拼接成字符串
allcode = ','.join(code_list)

try:
    # 获取实时K线数据
    df = pro.rt_k(ts_code=allcode)

    # 打印数据
    print("获取到的实时K线数据：")
    print(df)

    # 将DataFrame转换为字典，然后保存为JSON
    if df is not None and not df.empty:
        # 转换为字典
        data_dict = df.to_dict('records')  # 'records' 格式更易读

        # 定义保存路径
        save_path = 'stock_realtime_kline.json'

        # 保存为JSON文件
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(data_dict, f, ensure_ascii=False, indent=4)

        print(f"\n数据已成功保存到：{os.path.abspath(save_path)}")

        # 可选：保存为带日期时间的文件名
        import datetime

        current_time = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        save_path_with_time = f'stock_realtime_kline_{current_time}.json'
        with open(save_path_with_time, 'w', encoding='utf-8') as f:
            json.dump(data_dict, f, ensure_ascii=False, indent=4)
        print(f"带时间戳的数据文件已保存到：{os.path.abspath(save_path_with_time)}")
    else:
        print("未获取到有效数据")

except Exception as e:
    print(f"获取数据或保存文件时出错：{str(e)}")
    # 打印详细的错误信息
    import traceback

    traceback.print_exc()