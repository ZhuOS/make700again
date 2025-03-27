# 微信股票数据服务

这是一个基于Flask的微信股票数据服务，提供股票数据查询和分析功能。用户可以通过微信公众号查询股票信息，也可以在网页端查看数据。

## 功能特点

- 微信公众号集成
- 股票数据查询（基于Tushare API）
- 价格和成交量百分位分析
- Web界面展示
- 复权价格计算

## 安装步骤

1. 克隆项目
```bash
git clone https://github.com/ZhuOS/make700again.git
cd make700again
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置环境变量
创建 `.env` 文件并添加以下配置：
```
TUSHARE_TOKEN=your_tushare_token_here
WECHAT_TOKEN=your_wechat_token_here
DEBUG_MODE=True
```

## 配置说明

### Tushare Token
1. 访问 [Tushare官网](https://tushare.pro)
2. 注册并登录账号
3. 在个人中心获取您的 token
4. 将 token 填入 `.env` 文件的 `TUSHARE_TOKEN` 字段

### 微信 Token
1. 访问 [微信公众平台](https://mp.weixin.qq.com/)
2. 登录您的公众号
3. 进入"开发 -> 基本配置"
4. 在"服务器配置"中设置 Token
5. 将设置的 Token 填入 `.env` 文件的 `WECHAT_TOKEN` 字段

## 运行服务

```bash
python app.py
```

服务将在本地启动，默认地址：`http://localhost:5000`

## 使用说明

### 微信公众号
- 发送格式：`股票代码`
- 示例：`股票002371`
- 返回数据包括：
  - 最新价格
  - 价格百分位
  - 成交量
  - 成交量百分位

### Web界面
- 首页：`http://localhost:5000/`
- 估值分析：`http://localhost:5000/valuation`
- API接口：`http://localhost:5000/api/pe_data`

## 数据说明

### 价格百分位
- 范围：0-1
- 含义：当前价格在历史价格中的相对位置
- 示例：0.8 表示当前价格高于80%的历史价格

### 成交量百分位
- 范围：0-1
- 含义：当前成交量在历史成交量中的相对位置
- 示例：0.3 表示当前成交量低于70%的历史成交量

## 开发模式

在 `.env` 文件中设置 `DEBUG_MODE=True` 可以启用调试模式：
- 跳过微信签名验证
- 显示详细的日志信息
- 方便本地开发和测试

## 注意事项

1. 请妥善保管您的 Tushare token 和微信 token
2. 生产环境部署时请关闭调试模式
3. 建议使用虚拟环境运行项目
4. 定期更新依赖包以获取安全更新

## 许可证

MIT License 