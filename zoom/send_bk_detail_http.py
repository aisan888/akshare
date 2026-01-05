import json
import socket
import logging
import uvicorn
import tushare as ts
from datetime import datetime
from fastapi.responses import JSONResponse
from fastapi import FastAPI, Query, HTTPException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(funcName)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

HTTP_HOST = "localhost"
HTTP_PORT = 8000

TUSHARE_TOKEN = "168b63e0215b64bf1f7cc2558f3547bdd7b9d9168896e7ce6a14c79e7559"
TUSHARE_HTTP_URL = "http://42.194.163.97:5000"


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

        pro._DataApi__token = TUSHARE_TOKEN
        pro._DataApi__http_url = TUSHARE_HTTP_URL

        pro.trade_cal(exchange='', start_date='20251201', end_date='20251201')
        logger.info("✅ Tushare接口初始化成功")
        return pro
    except Exception as e:
        logger.error(f"❌ Tushare初始化失败：{str(e)}")
        raise RuntimeError(f"Tushare初始化失败：{str(e)}")


if not check_port_available(HTTP_PORT):
    exit(1)

pro = init_tushare()

app = FastAPI(
    title="板块详情查询API",
    description="C++客户端HTTP接口：查询DC板块成分股详情",
    version="1.0.0"
)


def saveJson(save_path, response_data):
    try:
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(response_data, f, ensure_ascii=False, indent=4, sort_keys=False)
        logger.info(f"数据已成功保存到：{save_path}")
    except Exception as e:
        logger.error(f"保存JSON文件失败：{str(e)}")


@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"📥 收到请求 | 方法：{request.method} | 路径：{request.url.path} | 参数：{request.query_params}")
    response = await call_next(request)
    logger.info(f"📤 响应返回 | 状态码：{response.status_code}")
    return response


DEFAULT_TRADE_DATE = "20251213"


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

        df = pro.dc_member(trade_date=trade_date, ts_code=ts_code)
        logger.info(f"Tushare返回数据行数：{len(df) if not df.empty else 0}")

        df = df.reset_index(drop=True).dropna().drop_duplicates()

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


DEFAULT_FIELDS = "ts_code,name,turnover_rate,up_num,down_num"


@app.get("/api/dc_index", response_class=JSONResponse)
async def get_dc_index(
        trade_date: str = Query(DEFAULT_TRADE_DATE, description="交易日，格式：YYYYMMDD"),
        fields: str = Query(DEFAULT_FIELDS, description="查询字段，多个字段用逗号分隔，示例：ts_code,name,turnover_rate")
):
    if len(trade_date) != 8 or not trade_date.isdigit():
        raise HTTPException(status_code=400, detail="交易日格式错误，需为8位数字（YYYYMMDD）")

    if not fields:
        raise HTTPException(status_code=400, detail="查询字段不能为空")

    field_list = [f.strip() for f in fields.split(",") if f.strip()]
    if not field_list:
        raise HTTPException(status_code=400, detail="查询字段格式错误，多个字段请用逗号分隔（示例：ts_code,name）")

    clean_fields = ",".join(list(set(field_list)))

    try:
        logger.info(f"开始查询板块指数数据 | trade_date={trade_date} | fields={clean_fields}")

        df = pro.dc_index(trade_date=trade_date, fields=clean_fields)
        logger.info(f"Tushare返回指数数据行数：{len(df) if not df.empty else 0}")

        df = df.reset_index(drop=True).dropna().drop_duplicates()

        response_data = {
            "code": 0,
            "msg": "success",
            "data": df.to_dict(orient="records"),
            "request_params": {
                "trade_date": trade_date,
                "fields": clean_fields,
                "original_fields": fields
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


VALID_EXCHANGES = ["", "XSHE", "SZSE", "XSHG", "SHSE", "BJSE"]
VALID_LIST_STATUSES = ["L", "D", "P"]
DEFAULT_STOCK_FIELDS = "ts_code,symbol,name,area,industry,list_date"


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

    if list_status not in VALID_LIST_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"上市状态错误！可选值：{VALID_LIST_STATUSES}（L=上市，D=退市，P=暂停上市），当前：{list_status}"
        )

    if not fields:
        raise HTTPException(status_code=400, detail="查询字段不能为空")
    field_list = [f.strip() for f in fields.split(",") if f.strip()]
    if not field_list:
        raise HTTPException(status_code=400, detail="查询字段格式错误，多个字段请用逗号分隔（示例：ts_code,name）")
    clean_fields = ",".join(list(set(field_list)))

    try:
        logger.info(f"开始查询基本信息 | exchange={exchange} | list_status={list_status} | fields={clean_fields}")

        df = pro.stock_basic(
            exchange='',
            list_status='',
            fields=clean_fields
        )
        logger.info(f"Tushare返回基本数据行数：{len(df) if not df.empty else 0}")

        df = df.reset_index(drop=True).dropna().drop_duplicates()

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
        logger.info(f"基本信息查询成功 | 返回数据条数：{len(response_data['data'])}")
        return response_data

    except ts.exceptions.TushareError as e:
        logger.error(f"Tushare stock_basic接口调用失败：{str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Tushare接口调用失败：{str(e)}")
    except Exception as e:
        logger.error(f"服务端未知错误（stock_basic）：{str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务端错误：{str(e)}")


import re

TS_CODE_PATTERN = re.compile(r"^\d{6}\.(SH|SZ|BJ)$")


@app.get("/api/rt_k", response_class=JSONResponse)
async def get_rt_k(ts_codes: str = Query(..., description="格式：600000.SH,600001.SH")):
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

    valid_codes = list(set(valid_codes))
    logger.info(
        f"解析代码 | 原始数量：{len(raw_codes)} | 有效数量：{len(valid_codes)} | 无效数量：{len(invalid_codes)}"
    )

    if not valid_codes:
        raise HTTPException(status_code=400, detail=f"无有效代码！无效代码：{invalid_codes}")

    try:
        logger.info(f"调用Tushare rt_k接口 | 有效代码数：{len(valid_codes)}（无数量限制）")
        valid_codes_str = ",".join(valid_codes)

        df = pro.rt_k(ts_code=valid_codes_str)

        all_data = []
        if not df.empty:
            df = df.reset_index(drop=True).dropna().drop_duplicates(subset=["ts_code"])
            all_data = df.to_dict(orient="records")
            logger.info(f"接口调用成功 | 返回数据行数：{len(all_data)}")
        else:
            logger.warning("Tushare接口返回空数据")

        response_data = {
            "code": 0,
            "msg": "success",
            "data": all_data,
            "meta": {
                "total_input_codes": len(raw_codes),
                "valid_code_count": len(valid_codes),
                "invalid_codes": invalid_codes,
                "return_data_count": len(all_data),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }

        return response_data


    except ts.exceptions.TushareError as e:
        logger.error(f"Tushare接口调用失败：{str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Tushare接口调用失败：{str(e)}")
    except Exception as e:
        logger.error(f"服务端错误：{str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务端错误：{str(e)}")


@app.get("/api/heartbeat", response_class=JSONResponse)
async def heartbeat():
    logger.info("处理心跳检测请求")
    return {
        "code": 0,
        "msg": "pong",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "service_status": "running",
        "tushare_status": "connected"
    }


@app.get("/", response_class=JSONResponse)
async def root():
    return {
        "code": 0,
        "msg": "服务运行中",
        "docs_url": f"http://{HTTP_HOST}:{HTTP_PORT}/docs",
        "redoc_url": f"http://{HTTP_HOST}:{HTTP_PORT}/redoc"
    }


if __name__ == "__main__":
    logger.info(f"🚀 启动FastAPI服务 | 地址：http://{HTTP_HOST}:{HTTP_PORT}")
    logger.info(f"📚 API文档地址：http://{HTTP_HOST}:{HTTP_PORT}/docs")

    uvicorn.run(
        app=app,
        host=HTTP_HOST,
        port=HTTP_PORT,
        log_level="info",
        workers=1,
        timeout_keep_alive=60
    )
