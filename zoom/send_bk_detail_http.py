import uvicorn
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
import tushare as ts
import pandas as pd
from datetime import datetime

# ===================== 配置项 =====================
HTTP_HOST = "0.0.0.0"  # 监听所有网卡（允许外部访问）
HTTP_PORT = 8000  # HTTP端口（C++客户端访问此端口）
DEFAULT_TRADE_DATE = "20251213"

# ===================== 初始化 =====================
# 1. 初始化Tushare Pro接口
token = "168b63e0215b64bf1f7cc2558f3547bdd7b9d9168896e7ce6a14c79e7559"

pro = ts.pro_api(token)
pro._DataApi__token = token  # 需要添加的代码
pro._DataApi__http_url = 'http://42.194.163.97:5000'  #

# 2. 初始化FastAPI应用
app = FastAPI(
    title="板块详情查询API",
    description="C++客户端HTTP接口：查询DC板块成分股详情",
    version="1.0.0"
)


# ===================== 核心接口 =====================
@app.get("/api/dc_member", response_class=JSONResponse)
async def get_dc_member(
        ts_code: str = Query(..., description="板块代码，示例：BK1184.DC"),
        trade_date: str = Query(DEFAULT_TRADE_DATE, description="交易日，格式：YYYYMMDD")
):
    """
    HTTP GET接口：查询DC板块成分股详情
    :param ts_code: 板块代码（必填）
    :param trade_date: 交易日（可选，默认20251213）
    :return: JSON格式的板块详情
    """
    try:


        # 2. 调用Tushare接口获取数据
        df = pro.dc_member(trade_date=trade_date, ts_code=ts_code)

        # 3. 数据清洗
        df = df.reset_index(drop=True).dropna().drop_duplicates()

        # 4. 构造响应数据
        response_data = {
            "code": 0,  # 0=成功，1=失败
            "msg": "success",
            "data": df.to_dict(orient="records"),
            "request_params": {
                "ts_code": ts_code,
                "trade_date": trade_date
            },
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        return response_data

    except ts.exceptions.TushareError as e:
        # Tushare接口错误
        raise HTTPException(
            status_code=500,
            detail=f"Tushare接口调用失败：{str(e)}"
        )
    except Exception as e:
        # 其他未知错误
        raise HTTPException(
            status_code=500,
            detail=f"服务端错误：{str(e)}"
        )


# 心跳检测接口（用于C++客户端检测服务是否在线）
@app.get("/api/heartbeat", response_class=JSONResponse)
async def heartbeat():
    return {
        "code": 0,
        "msg": "pong",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "service_status": "running"
    }


# ===================== 启动服务 =====================
if __name__ == "__main__":
    # 启动UVicorn服务（生产环境可配合Nginx反向代理）
    uvicorn.run(
        app=app,
        host=HTTP_HOST,
        port=HTTP_PORT,
        log_level="info"  # 日志级别：debug/info/warning/error
    )