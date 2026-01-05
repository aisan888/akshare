import akshare as ak
'''
gongsi xinxi
'''
stock_individual_info_em_df = ak.stock_individual_info_em(symbol="000001")
print(stock_individual_info_em_df)

stock_individual_basic_info_xq_df = ak.stock_individual_basic_info_xq(symbol="SH601127")
print(stock_individual_basic_info_xq_df)


'''
zuixin
'''
stock_bid_ask_em_df = ak.stock_bid_ask_em(symbol="000001")
print(stock_bid_ask_em_df)

'''
suoyou shenzhen  all zuixin
'''
stock_sz_a_spot_em_df = ak.stock_sz_a_spot_em()
print(stock_sz_a_spot_em_df)

'''
suoyou shanghai  all zuixin
'''
stock_sh_a_spot_em_df = ak.stock_sh_a_spot_em()
print(stock_sh_a_spot_em_df)

'''
suoyou beijing  all zuixin
'''
stock_bj_a_spot_em_df = ak.stock_bj_a_spot_em()
print(stock_bj_a_spot_em_df)

'''
新浪财经-沪深京 A 股数据
'''
stock_zh_a_spot_df = ak.stock_zh_a_spot()
print(stock_zh_a_spot_df)

'''
 实时行情数据-雪球
 '''
stock_individual_spot_xq_df = ak.stock_individual_spot_xq(symbol="SH600000")
print(stock_individual_spot_xq_df)