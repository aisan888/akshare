import zmq
import tushare as ts
import json
import time
import traceback
from datetime import datetime

# ===================== 配置项 =====================
TUSHARE_TOKEN = "你的Tushare Token"  # 替换为有效Token
ZMQ_PORT = "5555"  # ZMQ通信端口（需与C++客户端一致）
TRADE_DATE = "20251213"  # 默认交易日，可改为动态获取
ENCODING = "utf-8"  # 编码格式（与C++客户端统一）

# ===================== 初始化 =====================
# 1. 初始化Tushare Pro接口
pro = ts.pro_api(TUSHARE_TOKEN)

# 2. 初始化ZMQ上下文和Socket（使用REQ-REP模式，适配C++客户端）
context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind(f"tcp://*:{ZMQ_PORT}")  # 监听所有网卡的指定端口

print(f"✅ ZMQ服务端已启动，监听端口：{ZMQ_PORT}")
print(f"📅 默认交易日：{TRADE_DATE}")
print("===========================================")


def get_dc_member_detail(ts_code: str, trade_date: str = TRADE_DATE) -> str:
    """
    获取DC板块详情并转为JSON字符串（适配C++解析）
    :param ts_code: 板块代码（如BK1184.DC）
    :param trade_date: 交易日（YYYYMMDD）
    :return: JSON字符串（失败返回错误信息JSON）
    """
    try:
        # 1. 调用Tushare接口获取数据
        df = pro.dc_member(trade_date=trade_date, ts_code=ts_code)

        # 2. 数据清洗
        df = df.reset_index(drop=True).dropna().drop_duplicates()

        # 3. 转为JSON（ensure_ascii=False保留中文，separators压缩空格）
        json_data = df.to_dict(orient="records")
        result = {
            "code": 0,  # 0=成功，1=失败
            "msg": "success",
            "data": json_data,
            "ts_code": ts_code,
            "trade_date": trade_date,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    except Exception as e:
        # 异常处理：返回错误信息
        error_msg = f"获取板块{ts_code}详情失败：{str(e)}"
        print(f"❌ {error_msg}")
        traceback.print_exc()

        result = {
            "code": 1,
            "msg": error_msg,
            "data": [],
            "ts_code": ts_code,
            "trade_date": trade_date,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    # 转为JSON字符串（适配C++解析，避免多余空格）
    return json.dumps(result, ensure_ascii=False, separators=(",", ":"))


def main():
    """主循环：持续监听并响应C++客户端请求"""
    while True:
        try:
            # 1. 接收C++客户端发送的板块代码（bytes转字符串）
            request = socket.recv_string(encoding=ENCODING)
            ts_code = request.strip()  # 去除首尾空格/换行
            print(f"\n📥 收到客户端请求：板块代码 = {ts_code}")

            # 2. 心跳检测（C++客户端可能发送心跳包）
            if ts_code.lower() in ["ping", "heartbeat"]:
                response = json.dumps({
                    "code": 0,
                    "msg": "pong",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }, ensure_ascii=False)
                socket.send_string(response, encoding=ENCODING)
                print(f"📤 发送心跳响应：pong")
                continue

            # 3. 校验板块代码格式（示例：BKxxx.DC）
            if not (ts_code.startswith("BK") and "." in ts_code and ts_code.split(".")[-1] == "DC"):
                error_response = json.dumps({
                    "code": 1,
                    "msg": f"板块代码格式错误，示例：BK1184.DC，当前：{ts_code}",
                    "data": [],
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }, ensure_ascii=False)
                socket.send_string(error_response, encoding=ENCODING)
                print(f"❌ 板块代码格式错误，已返回错误响应")
                continue

            # 4. 获取板块详情并返回
            response = get_dc_member_detail(ts_code)
            socket.send_string(response, encoding=ENCODING)
            print(f"📤 已发送板块{ts_code}详情，数据长度：{len(response)}字节")

        except zmq.ZMQError as e:
            print(f"❌ ZMQ通信错误：{e}")
            time.sleep(1)  # 出错后休眠1秒，避免死循环

        except KeyboardInterrupt:
            print("\n🛑 服务端被手动终止")
            break

        except Exception as e:
            print(f"❌ 未知错误：{e}")
            traceback.print_exc()
            # 发送通用错误响应
            error_response = json.dumps({
                "code": 1,
                "msg": f"服务端未知错误：{str(e)}",
                "data": [],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }, ensure_ascii=False)
            socket.send_string(error_response, encoding=ENCODING)
            time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    finally:
        # 释放资源
        socket.close()
        context.term()
        print("✅ ZMQ资源已释放，服务端退出")