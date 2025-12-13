import akshare as ak

'''
概念板块
'''

stock_board_concept_name_em_df = ak.stock_board_concept_name_em()
print(stock_board_concept_name_em_df)

csv_path = "股票概念板块数据.csv"
stock_board_concept_name_em_df.to_csv(
    csv_path,
    index=False,  # 不保存行索引
    encoding="utf-8-sig"  # 解决中文乱码问题
)
print(f"\n数据已保存为CSV文件：{csv_path}")

#
# stock_board_concept_cons_em_df = ak.stock_board_concept_cons_em(symbol="融资融券")
# print(stock_board_concept_cons_em_df)
#
'''
行业板块
'''

stock_board_industry_name_em_df = ak.stock_board_industry_name_em()
print(stock_board_industry_name_em_df)


csv_path = "股票行业板块数据.csv"
stock_board_industry_name_em_df.to_csv(
    csv_path,
    index=False,  # 不保存行索引
    encoding="utf-8-sig"  # 解决中文乱码问题
)
print(f"\n数据已保存为CSV文件：{csv_path}")

#
# stock_board_industry_cons_em_df = ak.stock_board_industry_cons_em(symbol="小金属")
# print(stock_board_industry_cons_em_df)
#
# '''
# 涨停池
# '''
# stock_zt_pool_em_df = ak.stock_zt_pool_em(date='20241008')
# print(stock_zt_pool_em_df)
#
# '''
# 东财热度
# '''
# stock_hot_rank_em_df = ak.stock_hot_rank_em()
# print(stock_hot_rank_em_df)