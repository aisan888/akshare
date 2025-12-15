import uvicorn
import logging
import socket
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
import tushare as ts
from datetime import datetime


# ===================== 1. 日志配置（关键：排查请求是否到达） =====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(funcName)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===================== 2. 配置项 =====================
HTTP_HOST = "localhost"
HTTP_PORT = 8000
DEFAULT_TRADE_DATE = "20251213"


TUSHARE_TOKEN = "168b63e0215b64bf1f7cc2558f3547bdd7b9d9168896e7ce6a14c79e7559"
TUSHARE_HTTP_URL = "http://42.194.163.97:5000"
DEFAULT_FIELDS = "ts_code,name,turnover_rate,up_num,down_num"

# ===================== 3. 初始化前置检查 =====================
def check_port_available(port: int) -> bool:
    """检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((HTTP_HOST, port))
            return True
        except OSError:
            logger.error(f"端口 {port} 已被占用！请更换端口或关闭占用进程")
            return False


def init_tushare() -> ts.pro_api:

    try:
        pro = ts.pro_api(TUSHARE_TOKEN)
        # 覆盖自定义接口地址（针对私有部署的Tushare）
        pro._DataApi__token = TUSHARE_TOKEN
        pro._DataApi__http_url = TUSHARE_HTTP_URL

        # 预校验Tushare连接（调用基础接口测试）
        pro.trade_cal(exchange='', start_date='20251201', end_date='20251201')
        logger.info("✅ Tushare接口初始化成功")
        return pro
    except Exception as e:
        logger.error(f"❌ Tushare初始化失败：{str(e)}")
        raise RuntimeError(f"Tushare初始化失败：{str(e)}")


# 检查端口可用性
if not check_port_available(HTTP_PORT):
    exit(1)

# 初始化Tushare
pro = init_tushare()

# ===================== 4. 初始化FastAPI（添加中间件记录所有请求） =====================
app = FastAPI(
    title="板块详情查询API",
    description="C++客户端HTTP接口：查询DC板块成分股详情",
    version="1.0.0"
)


# 全局中间件：记录所有入站请求（关键：确认请求是否到达服务端）
@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"📥 收到请求 | 方法：{request.method} | 路径：{request.url.path} | 参数：{request.query_params}")
    response = await call_next(request)
    logger.info(f"📤 响应返回 | 状态码：{response.status_code}")
    return response


# ===================== 5. 核心接口（增强校验+详细日志） =====================
@app.get("/api/dc_member", response_class=JSONResponse)
async def get_dc_member(
        ts_code: str = Query(..., description="板块代码，示例：BK1184.DC"),
        trade_date: str = Query(DEFAULT_TRADE_DATE, description="交易日，格式：YYYYMMDD")
):

    if not ts_code:
        raise HTTPException(status_code=400, detail="板块代码不能为空")
    if len(trade_date) != 8 or not trade_date.isdigit():
        raise HTTPException(status_code=400, detail="交易日格式错误，需为8位数字（YYYYMMDD）")
    if not (ts_code.startswith("BK") and "." in ts_code and ts_code.split(".")[-1] == "DC"):
        raise HTTPException(status_code=400, detail=f"板块代码格式错误！示例：BK1184.DC，当前：{ts_code}")

    try:
        logger.info(f"开始查询板块数据 | ts_code={ts_code} | trade_date={trade_date}")

        # 调用Tushare接口
        df = pro.dc_member(trade_date=trade_date, ts_code=ts_code)
        logger.info(f"Tushare返回数据行数：{len(df) if not df.empty else 0}")

        # 数据清洗
        df = df.reset_index(drop=True).dropna().drop_duplicates()

        # 构造响应
        response_data = {
            "code": 0,
            "msg": "success",
            "data": df.to_dict(orient="records"),
            "request_params": {"ts_code": ts_code, "trade_date": trade_date},
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        logger.info(f"板块数据查询成功 | 返回数据条数：{len(response_data['data'])}")
        return response_data

    except ts.exceptions.TushareError as e:
        logger.error(f"Tushare接口调用失败：{str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Tushare接口调用失败：{str(e)}")
    except Exception as e:
        logger.error(f"服务端未知错误：{str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务端错误：{str(e)}")


@app.get("/api/dc_index", response_class=JSONResponse)
async def get_dc_index(
        trade_date: str = Query(DEFAULT_TRADE_DATE, description="交易日，格式：YYYYMMDD"),
        fields: str = Query(DEFAULT_FIELDS, description="查询字段，多个字段用逗号分隔，示例：ts_code,name,turnover_rate")
):
    """
    HTTP GET接口：查询DC板块指数信息
    :param trade_date: 交易日（可选，默认20251213）
    :param fields: 查询字段（可选，默认：ts_code,name,turnover_rate,up_num,down_num）
    :return: JSON格式的板块指数信息
    """
    # 参数校验
    # 1. 交易日校验
    if len(trade_date) != 8 or not trade_date.isdigit():
        raise HTTPException(status_code=400, detail="交易日格式错误，需为8位数字（YYYYMMDD）")

    # 2. 字段参数校验（非空 + 格式合法）
    if not fields:
        raise HTTPException(status_code=400, detail="查询字段不能为空")
    # 过滤空字段，去重
    field_list = [f.strip() for f in fields.split(",") if f.strip()]
    if not field_list:
        raise HTTPException(status_code=400, detail="查询字段格式错误，多个字段请用逗号分隔（示例：ts_code,name）")
    # 重新拼接去重后的字段（避免重复字段）
    clean_fields = ",".join(list(set(field_list)))

    try:
        logger.info(f"开始查询板块指数数据 | trade_date={trade_date} | fields={clean_fields}")

        # 调用Tushare dc_index接口
        df = pro.dc_index(trade_date=trade_date, fields=clean_fields)
        logger.info(f"Tushare返回指数数据行数：{len(df) if not df.empty else 0}")

        # 数据清洗（和原有接口保持一致的清洗逻辑）
        df = df.reset_index(drop=True).dropna().drop_duplicates()

        # 构造响应（和原有接口格式保持一致，保证前端兼容）
        response_data = {
            "code": 0,
            "msg": "success",
            "data": df.to_dict(orient="records"),
            "request_params": {
                "trade_date": trade_date,
                "fields": clean_fields,  # 返回清洗后的字段
                "original_fields": fields  # 保留原始请求字段（便于排查）
            },
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        logger.info(f"板块指数数据查询成功 | 返回数据条数：{len(response_data['data'])}")
        return response_data

    except ts.exceptions.TushareError as e:
        logger.error(f"Tushare dc_index接口调用失败：{str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Tushare接口调用失败：{str(e)}")
    except Exception as e:
        logger.error(f"服务端未知错误（dc_index）：{str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务端错误：{str(e)}")


# 新增：stock_basic可选参数枚举（用于参数校验）
VALID_EXCHANGES = ["", "XSHE", "SZSE", "XSHG", "SHSE", "BJSE"]  # 空=全部，深市/沪市/北交所
VALID_LIST_STATUSES = ["L", "D", "P"]  # L=上市，D=退市，P=暂停上市
DEFAULT_STOCK_FIELDS = "ts_code,symbol,name,area,industry,list_date"
# http://127.0.0.1:8000/api/stock_basic?fields=ts_code,symbol,market,exchange,list_status,is_hs,name,area,industry,list_date
# ===================== 7. 新增核心接口：stock_basic =====================
@app.get("/api/stock_basic", response_class=JSONResponse)
async def get_stock_basic(
        exchange: str = Query("", description=f"交易所代码，可选值：{VALID_EXCHANGES}（空=全部）"),
        list_status: str = Query("L", description=f"上市状态，可选值：{VALID_LIST_STATUSES}（L=上市，D=退市，P=暂停上市）"),
        fields: str = Query(DEFAULT_STOCK_FIELDS,
                            description="查询字段，多个字段用逗号分隔，示例：ts_code,symbol,name,area")
):

    if exchange not in VALID_EXCHANGES:
        raise HTTPException(
            status_code=400,
            detail=f"交易所代码错误！可选值：{VALID_EXCHANGES}，当前：{exchange}"
        )

    # 2. 上市状态校验
    if list_status not in VALID_LIST_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"上市状态错误！可选值：{VALID_LIST_STATUSES}（L=上市，D=退市，P=暂停上市），当前：{list_status}"
        )

    # 3. 字段参数校验（去空、去重）
    if not fields:
        raise HTTPException(status_code=400, detail="查询字段不能为空")
    field_list = [f.strip() for f in fields.split(",") if f.strip()]
    if not field_list:
        raise HTTPException(status_code=400, detail="查询字段格式错误，多个字段请用逗号分隔（示例：ts_code,name）")
    clean_fields = ",".join(list(set(field_list)))

    try:
        logger.info(f"开始查询股票基本信息 | exchange={exchange} | list_status={list_status} | fields={clean_fields}")

        # 调用Tushare stock_basic接口
        df = pro.stock_basic(
            exchange='',
            list_status='',
            fields=clean_fields
        )
        logger.info(f"Tushare返回股票基本数据行数：{len(df) if not df.empty else 0}")

        # 数据清洗（和原有接口保持一致的逻辑）
        df = df.reset_index(drop=True).dropna().drop_duplicates()

        # 构造响应（格式和原有接口完全一致，保证前端兼容）
        response_data = {
            "code": 0,
            "msg": "success",
            "data": df.to_dict(orient="records"),
            "request_params": {
                "exchange": exchange,
                "list_status": list_status,
                "fields": clean_fields,
                "original_fields": fields
            },
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        logger.info(f"股票基本信息查询成功 | 返回数据条数：{len(response_data['data'])}")
        return response_data

    except ts.exceptions.TushareError as e:
        logger.error(f"Tushare stock_basic接口调用失败：{str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Tushare接口调用失败：{str(e)}")
    except Exception as e:
        logger.error(f"服务端未知错误（stock_basic）：{str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务端错误：{str(e)}")

import re
TS_CODE_PATTERN = re.compile(r"^\d{6}\.(SH|SZ|BJ)$")
# ===================== 4. 核心接口：rt_k（无任何数量限制） =====================
@app.get("/api/rt_k", response_class=JSONResponse)
async def get_rt_k(
        ts_codes: str = Query(..., description="代码列表，多个用逗号分隔（格式：600000.SH，无数量限制）")
):

    raw_codes = [code.strip() for code in ts_codes.split(",") if code.strip()]
    if not raw_codes:
        raise HTTPException(status_code=400, detail="代码列表不能为空")


    valid_codes = []
    invalid_codes = []
    for code in raw_codes:
        if TS_CODE_PATTERN.match(code):
            valid_codes.append(code)
        else:
            invalid_codes.append(code)

    # 3. 代码去重（避免重复查询，不限制数量）
    valid_codes = list(set(valid_codes))
    logger.info(
        f"解析股票代码 | 原始数量：{len(raw_codes)} | 有效数量：{len(valid_codes)} | 无效数量：{len(invalid_codes)}"
    )

    # 4. 检查有效代码是否为空
    if not valid_codes:
        raise HTTPException(status_code=400, detail=f"无有效股票代码！无效代码：{invalid_codes}")

    # 5. 单次调用Tushare rt_k接口（传入所有有效代码，无数量限制）
    try:
        logger.info(f"调用Tushare rt_k接口 | 有效代码数：{len(valid_codes)}（无数量限制）")
        valid_codes_str = ",".join(valid_codes)

        # 核心调用：一次性传入所有有效代码（无论数量多少）
        df = pro.rt_k(ts_code=valid_codes_str)

        # 6. 数据清洗
        all_data = []
        if not df.empty:
            # 重置索引 + 去空值 + 按股票代码去重
            df = df.reset_index(drop=True).dropna().drop_duplicates(subset=["ts_code"])
            all_data = df.to_dict(orient="records")
            logger.info(f"接口调用成功 | 返回数据行数：{len(all_data)}")
        else:
            logger.warning("Tushare接口返回空数据")

        # 7. 极简响应（无任何多余限制字段）
        response_data = {
            "code": 0,          # 0=成功，1=失败
            "msg": "success",   # 响应信息
            "data": all_data,   # 核心K线数据
            "meta": {           # 元信息（仅展示统计，无限制）
                "total_input_codes": len(raw_codes),
                "valid_code_count": len(valid_codes),
                "invalid_codes": invalid_codes,
                "return_data_count": len(all_data),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }

        return response_data

    # 异常处理（仅捕获接口调用错误）
    except ts.exceptions.TushareError as e:
        logger.error(f"Tushare接口调用失败：{str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Tushare接口调用失败：{str(e)}")
    except Exception as e:
        logger.error(f"服务端错误：{str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务端错误：{str(e)}")

# ===================== 6. 心跳检测接口（简化+日志） =====================
@app.get("/api/heartbeat", response_class=JSONResponse)
async def heartbeat():
    logger.info("处理心跳检测请求")
    return {
        "code": 0,
        "msg": "pong",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "service_status": "running",
        "tushare_status": "connected"  # 新增Tushare连接状态
    }


# ===================== 7. 根路径接口（测试服务是否存活） =====================
@app.get("/", response_class=JSONResponse)
async def root():
    return {
        "code": 0,
        "msg": "服务运行中",
        "docs_url": f"http://{HTTP_HOST}:{HTTP_PORT}/docs",  # Swagger文档地址
        "redoc_url": f"http://{HTTP_HOST}:{HTTP_PORT}/redoc"
    }


# ===================== 8. 启动服务（增强配置） =====================
if __name__ == "__main__":
    logger.info(f"🚀 启动FastAPI服务 | 地址：http://{HTTP_HOST}:{HTTP_PORT}")
    logger.info(f"📚 API文档地址：http://{HTTP_HOST}:{HTTP_PORT}/docs")

    # 启动UVicorn（添加workers+超时配置，适配生产环境）
    uvicorn.run(
        app=app,
        host=HTTP_HOST,
        port=HTTP_PORT,
        log_level="info",
        workers=1,  # 单进程（调试更简单），生产环境可改为2-4
        timeout_keep_alive=60  # 长连接超时
    )