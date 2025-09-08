# FinanceIQ API Documentation

## Overview
FinanceIQ API提供完整的股票数据分析服务，包括基础信息、技术分析、财务数据和AI智能分析。

**Base URL**: `http://35.77.54.203:3007`

## Core API Endpoints

### 1. 股票数据获取
**GET** `/api/stocks/{stock_code}/data`

获取股票的完整数据，包括基础信息、技术分析、财务数据和市场情绪。

#### Parameters
- `stock_code` (string, required): 6位股票代码 (例如: "000001", "002222")

#### Response Structure
```json
{
  "stock_code": "000001",
  "collected_at": "2025-09-08T02:56:39.781294",
  "fundamental": {
    "source": "fundamental_analysis",
    "stock_code": "000001",
    "stock_name": "平安银行",
    "current_price": 11.71,
    "market_cap": 2272.4,
    "circulating_market_cap": 2272.3958364663,
    "pe_ratio": 0,
    "industry": "银行",
    "updated_at": "2025-09-08T02:56:39.781274"
  },
  "technical": {
    "source": "technical_analysis",
    "stock_code": "000001",
    "current_price": 11.71,
    "price_change": 0,
    "price_change_pct": 0,
    "trend": "趋势待观察",
    "updated_at": "2025-09-08T02:56:39.781281"
  },
  "financial": {
    "source": "financial_data",
    "stock_code": "000001",
    "revenue_data": {
      "2025-06-30": 69385000000.0
    },
    "profit_data": {
      "2025-06-30": 24870000000.0
    },
    "roe_data": {
      "2025-06-30": 5.25
    },
    "cash_flow_data": {
      "2025-06-30": 174682000000.0
    },
    "debt_ratio_data": {
      "2025-06-30": 91.318035
    },
    "net_margin_data": {
      "2025-06-30": 35.843482
    },
    "updated_at": "2025-09-08T02:56:39.781287"
  },
  "sentiment": {
    "source": "market_sentiment",
    "stock_code": "000001",
    "sentiment_score": 0.5,
    "news_sentiment": "neutral",
    "updated_at": "2025-09-08T02:56:39.781291"
  }
}
```

#### Data Field Explanations

##### Fundamental Data
- `stock_name`: 股票名称
- `current_price`: 当前价格 (元)
- `market_cap`: 总市值 (亿元)
- `circulating_market_cap`: 流通市值 (亿元)
- `pe_ratio`: 市盈率
- `industry`: 所属行业

##### Technical Data  
- `current_price`: 当前价格 (元)
- `price_change`: 价格变动 (元)
- `price_change_pct`: 价格变动百分比 (%)
- `trend`: 趋势描述

##### Financial Data
- `revenue_data`: 营业收入数据 (按季度, 单位: 元)
- `profit_data`: 净利润数据 (按季度, 单位: 元)
- `roe_data`: 净资产收益率 (按季度, 单位: %)
- `cash_flow_data`: 经营现金流 (按季度, 单位: 元)
- `debt_ratio_data`: 资产负债率 (按季度, 单位: %)
- `net_margin_data`: 净利率 (按季度, 单位: %)

##### Sentiment Data
- `sentiment_score`: 市场情绪评分 (0-1)
- `news_sentiment`: 新闻情绪 ("positive", "neutral", "negative")

### 2. AI智能分析
**POST** `/api/ai/analyze`

对指定股票进行AI智能分析，提供专业的投资建议。

#### Parameters
- `stock_code` (string, required): 6位股票代码
- `analysis_style` (string, optional): 分析风格 ("professional", "conservative", "aggressive")

#### Request Example
```bash
POST /api/ai/analyze?stock_code=000001&analysis_style=professional
Content-Type: application/json
```

#### Response Structure
```json
{
  "stock_code": "000001",
  "analysis_style": "professional",
  "analysis_result": {
    "summary": "基于深度财务分析...",
    "recommendation": "BUY",
    "target_price": 13.47,
    "risk_level": "MEDIUM",
    "key_points": [
      "营收增长稳定",
      "财务状况良好",
      "行业前景看好"
    ]
  },
  "confidence_score": 0.85,
  "generated_at": "2025-09-08T02:58:00.000Z"
}
```

### 3. 系统健康检查
**GET** `/health`

检查系统运行状态，包括Redis连接、外部API状态等。

#### Response Structure
```json
{
  "status": "healthy",
  "timestamp": "2025-09-08T02:58:00.000Z",
  "services": {
    "redis": "connected",
    "external_api": "accessible",
    "database": "connected"
  },
  "version": "2.3"
}
```

## Frontend Pages

### 1. 主页 (Dashboard)
**GET** `/dashboard`

股票分析主页，包含基础信息、技术分析、财务指标和AI分析。

**Features**:
- 实时股价显示
- 技术指标分析
- 财务关键指标
- AI智能推荐

### 2. 财务报表页
**GET** `/financial`

详细的财务数据对比分析页面。

**Features**:
- 季度财务对比
- 80+财务指标
- 趋势分析图表
- 财务健康度评估

### 3. 综合分析页
**GET** `/analysis`

AI驱动的综合投资分析页面。

**Features**:
- AI智能评分
- 同行业对比
- 预测模型
- 投资策略推荐

## Data Sources

### External APIs
- **Comprehensive Data API**: `http://35.77.54.203:3003/api/comprehensive-data/{stock_code}`
  - 提供80+财务指标
  - 实时股价数据
  - 行业分类信息

### Internal Processing
- 数据清洗和标准化
- 中英文字段名映射
- 数据类型转换 (亿元单位)
- 缓存机制 (Redis)

## Error Handling

### HTTP Status Codes
- `200 OK`: 请求成功
- `400 Bad Request`: 参数错误 (如股票代码格式错误)
- `404 Not Found`: 资源不存在 (如股票代码不存在)
- `500 Internal Server Error`: 服务器内部错误
- `503 Service Unavailable`: 外部API不可用

### Error Response Format
```json
{
  "error": {
    "code": "STOCK_NOT_FOUND",
    "message": "股票代码不存在或数据暂不可用",
    "details": "Stock code 999999 not found in database"
  },
  "timestamp": "2025-09-08T02:58:00.000Z"
}
```

## Rate Limiting
- 每IP每分钟最多60次请求
- AI分析接口每IP每分钟最多10次请求
- 超过限制返回 `429 Too Many Requests`

## Caching Strategy
- 股票基础数据: 5分钟缓存
- 财务数据: 1小时缓存
- AI分析结果: 24小时缓存
- 使用Redis作为缓存后端

## Version History
- **v2.3** (2025-09-08): 修复财务数据零值问题，统一API架构
- **v2.2** (2025-09-07): 完善FinanceIQ界面，优化用户体验
- **v2.1** (2025-09-07): 初始FinanceIQ专业界面发布
- **v1.0** (2025-09-06): 基础功能完成，Prism系统上线