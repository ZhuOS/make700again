from flask import Flask, render_template, jsonify, request
import tushare as ts
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import logging
import hashlib
import xml.etree.ElementTree as ET
import time

# 配置日志, 输出到控制台
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
load_dotenv()

app = Flask(__name__)

# 配置tushare token
token = os.getenv('TUSHARE_TOKEN')
if not token:
    logger.error("Tushare token not found in .env file")
    raise ValueError("Please set TUSHARE_TOKEN in .env file")

# 微信公众号配置
WECHAT_TOKEN = os.getenv('WECHAT_TOKEN', 'test_token_123')  # 在.env文件中设置
DEBUG_MODE = os.getenv('DEBUG_MODE', 'True').lower() == 'true'

logger.info(f"Initializing Tushare with token: {token[:8]}...")  # 只显示token的前8位
logger.info(f"Debug mode: {DEBUG_MODE}")
ts.set_token(token)
pro = ts.pro_api()

def check_signature(signature, timestamp, nonce):
    """验证微信签名"""
    if DEBUG_MODE:
        logger.info(f"Debug mode: Skipping signature check")
        return True
        
    temp_list = [WECHAT_TOKEN, timestamp, nonce]
    temp_list.sort()
    temp_str = ''.join(temp_list)
    hash_obj = hashlib.sha1()
    hash_obj.update(temp_str.encode('utf-8'))
    return hash_obj.hexdigest() == signature

def parse_xml(xml_data):
    """解析微信发来的XML数据"""
    if DEBUG_MODE:
        logger.info(f"Debug mode: Received XML data: {xml_data}")
        
    root = ET.fromstring(xml_data)
    msg_type = root.find('MsgType').text
    from_user = root.find('FromUserName').text
    to_user = root.find('ToUserName').text
    create_time = root.find('CreateTime').text
    
    if msg_type == 'text':
        content = root.find('Content').text
        return {
            'type': msg_type,
            'from_user': from_user,
            'to_user': to_user,
            'create_time': create_time,
            'content': content
        }
    return None

def generate_response(to_user, from_user, content):
    """生成微信响应XML"""
    timestamp = int(time.time())
    response = f"""
    <xml>
        <ToUserName><![CDATA[{to_user}]]></ToUserName>
        <FromUserName><![CDATA[{from_user}]]></FromUserName>
        <CreateTime>{timestamp}</CreateTime>
        <MsgType><![CDATA[text]]></MsgType>
        <Content><![CDATA[{content}]]></Content>
    </xml>
    """
    
    if DEBUG_MODE:
        logger.info(f"Debug mode: Generated response: {response}")
        
    return response

def get_stock_data(stock_code='300604.SZ'):  # 使用长川科技作为示例
    """获取股票的价格和成交量数据"""
    try:
        # 获取最近5年的数据
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=5*365)).strftime('%Y%m%d')
        
        logger.info(f"Fetching data for {stock_code} from {start_date} to {end_date}")
        logger.info(f"Using token: {token[:8]}...")  # 只显示token的前8位
        
        # 获取日线数据
        logger.info("Trying to fetch daily data...")
        try:
            df = pro.daily(ts_code=stock_code, start_date=start_date, end_date=end_date)
            logger.info(f"Daily data response: {df.head() if not df.empty else 'Empty DataFrame'}")
            logger.info(f"Daily data shape: {df.shape}")
        except Exception as e:
            logger.error(f"Error fetching daily data: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error details: {e.__dict__ if hasattr(e, '__dict__') else 'No details'}")
            return []
        
        if df.empty:
            logger.error(f"No daily data found for {stock_code}")
            return []
            
        # 获取复权因子
        logger.info("Trying to fetch adjustment factor...")
        try:
            adj_factor = pro.adj_factor(ts_code=stock_code, start_date=start_date, end_date=end_date)
            logger.info(f"Adjustment factor response: {adj_factor.head() if not adj_factor.empty else 'Empty DataFrame'}")
            logger.info(f"Adjustment factor shape: {adj_factor.shape}")
        except Exception as e:
            logger.error(f"Error fetching adjustment factor: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error details: {e.__dict__ if hasattr(e, '__dict__') else 'No details'}")
            return []
        
        if adj_factor.empty:
            logger.error(f"No adjustment factor found for {stock_code}")
            return []
        
        # 合并数据
        df = pd.merge(df, adj_factor[['trade_date', 'adj_factor']], on='trade_date')
        
        # 计算复权价格
        df['adj_close'] = df['close'] * df['adj_factor']
        
        # 计算价格百分位
        df['price_percentile'] = df['adj_close'].rolling(window=252).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1]
        )
        
        # 计算成交量百分位
        df['volume_percentile'] = df['vol'].rolling(window=252).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1]
        )
        
        # 格式化日期
        df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d')
        
        # 将NaN替换为None
        df = df.replace({np.nan: None})
        
        logger.info(f"Successfully processed data for {stock_code}")
        logger.info(f"Final data shape: {df.shape}")
        logger.info(f"Final data columns: {df.columns.tolist()}")
        return df[['trade_date', 'adj_close', 'price_percentile', 'vol', 'volume_percentile']].to_dict('records')
        
    except Exception as e:
        logger.error(f"Error processing data for {stock_code}: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error details: {e.__dict__ if hasattr(e, '__dict__') else 'No details'}")
        return []

@app.route('/')
def index():
    """首页"""
    logger.info(f"Home page request, using token: {token[:8]}...")  # 只显示token的前8位
    return render_template('index.html')

@app.route('/valuation')
def valuation():
    """估值分析页面"""
    logger.info(f"Valuation page request, using token: {token[:8]}...")  # 只显示token的前8位
    return render_template('valuation.html')

@app.route('/api/pe_data')
def pe_data():
    """获取股票数据的API"""
    logger.info(f"Stock data API request, using token: {token[:8]}...")  # 只显示token的前8位
    try:
        data = get_stock_data()
        if not data:
            return jsonify({
                'code': 1,
                'message': '获取数据失败，请检查股票代码或稍后重试'
            })
        return jsonify({
            'code': 0,
            'data': data
        })
    except Exception as e:
        logger.error(f"API error: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error details: {e.__dict__ if hasattr(e, '__dict__') else 'No details'}")
        return jsonify({
            'code': 1,
            'message': f'服务器错误: {str(e)}'
        })

@app.route('/wechat', methods=['GET', 'POST'])
def wechat():
    """处理微信消息"""
    if request.method == 'GET':
        # 处理微信服务器的验证请求
        signature = request.args.get('signature', '')
        timestamp = request.args.get('timestamp', '')
        nonce = request.args.get('nonce', '')
        echostr = request.args.get('echostr', '')
        
        if DEBUG_MODE:
            logger.info(f"Debug mode: GET request received")
            logger.info(f"Signature: {signature}")
            logger.info(f"Timestamp: {timestamp}")
            logger.info(f"Nonce: {nonce}")
            logger.info(f"Echostr: {echostr}")
        
        if check_signature(signature, timestamp, nonce):
            return echostr
        return 'Invalid signature'
    
    elif request.method == 'POST':
        # 处理微信发来的消息
        xml_data = request.data
        
        if DEBUG_MODE:
            logger.info(f"Debug mode: POST request received")
            logger.info(f"Raw data: {xml_data}")
        
        msg = parse_xml(xml_data)
        
        if not msg:
            return generate_response(msg['to_user'], msg['from_user'], '暂不支持该类型消息')
        
        if msg['type'] == 'text':
            content = msg['content'].strip()
            
            if DEBUG_MODE:
                logger.info(f"Debug mode: Received text message: {content}")
            
            # 处理股票查询命令
            if content.startswith('股票'):
                stock_code = content[2:].strip()
                if not stock_code:
                    return generate_response(msg['to_user'], msg['from_user'], '请输入股票代码，例如：股票002371')
                
                try:
                    data = get_stock_data(stock_code)
                    if not data:
                        return generate_response(msg['to_user'], msg['from_user'], f'获取{stock_code}数据失败，请检查股票代码是否正确')
                    
                    # 获取最新数据
                    latest = data[-1]
                    response = f"""
{stock_code}最新数据：
日期：{latest['trade_date']}
复权价格：{latest['adj_close']:.2f}
价格百分位：{latest['price_percentile']*100:.2f}%
成交量：{latest['vol']}
成交量百分位：{latest['volume_percentile']*100:.2f}%
                    """
                    return generate_response(msg['to_user'], msg['from_user'], response)
                except Exception as e:
                    logger.error(f"Error processing stock query: {str(e)}")
                    return generate_response(msg['to_user'], msg['from_user'], '处理请求时发生错误，请稍后重试')
            
            # 处理帮助命令
            elif content == '帮助' or content == 'help':
                help_text = """
欢迎使用股票分析助手！
可用命令：
1. 股票[代码] - 查询股票数据，例如：股票002371
2. 帮助 - 显示帮助信息
                """
                return generate_response(msg['to_user'], msg['from_user'], help_text)
            
            # 处理其他消息
            else:
                return generate_response(msg['to_user'], msg['from_user'], '请输入"帮助"查看可用命令')
        
        return generate_response(msg['to_user'], msg['from_user'], '暂不支持该类型消息')

if __name__ == '__main__':
    app.run(debug=True) 