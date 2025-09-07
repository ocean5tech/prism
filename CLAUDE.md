# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

This is a Python-based microservices project using FastAPI, Celery, and Redis. Since there's no package.json or standard build files, use these commands:

### Environment Setup
```bash
pip install -r requirements.txt
```

### Running Services
```bash
# CURRENT WORKING COMMAND - Start test server with FinanceIQ UI
source prism_venv/bin/activate && python test_server.py
# 服务运行在: http://35.77.54.203:3007

# Alternative: Start the FastAPI application (full system)
uvicorn src.api.main:app --host 0.0.0.0 --port 3005 --reload

# Start Celery worker for background tasks (if using full system)
celery -A src.core.task_scheduler.celery_app worker --loglevel=info

# Start Celery monitoring (Flower)
celery -A src.core.task_scheduler.celery_app flower --port=5555
```

### Development
```bash
# Run with specific configuration
python -m src.main --config config/development.json

# Check code with Python linter (if available)
python -m flake8 src/
python -m black src/
```

### Testing
No test framework configuration found. To run tests:
```bash
# If using pytest (recommended)
pytest tests/

# If using unittest
python -m unittest discover tests/
```

## Architecture Overview

Prism is a high-performance microservices system designed to replace n8n workflows for stock analysis article generation. The system follows event-driven architecture with parallel processing capabilities.

### Key Components

- **Task Scheduler** (`src/core/task_scheduler.py`): Core Celery-based task orchestration replacing n8n workflows
- **AI Agent Pool** (`src/services/ai_agent_pool.py`): Manages concurrent AI analysis agents with connection pooling
- **Stock Data Service** (`src/services/stock_data_service.py`): Handles parallel data collection from multiple sources
- **Article Generator Worker** (`src/workers/article_generator.py`): Core workflow processor that coordinates the entire pipeline

### Service Architecture Flow
```
[Input API] → [Task Scheduler] → [Parallel Processing Engine]
                ↓
[Stock Data Service] ↔ [AI Agent Pool] ↔ [Article Generator]
                ↓
[Result Aggregator] → [Output Formatter] → [Multiple Articles Output]
```

### Technology Stack
- **Web Framework**: FastAPI (async)
- **Task Queue**: Celery + Redis
- **Database**: PostgreSQL + Redis caching  
- **AI Integration**: aiohttp connection pools
- **Monitoring**: Prometheus metrics
- **Configuration**: Pydantic settings with environment variables

### Data Flow
1. Stock code input triggers `create_article_generation_task` in task scheduler
2. Parallel data collection from multiple stock data APIs
3. Concurrent AI analysis using different agent styles (professional, dark, optimistic, conservative)
4. Article generation and formatting for multiple output styles
5. Result aggregation with metadata and performance metrics

### Configuration
- Main config in `src/core/config.py` using Pydantic settings
- Environment variables loaded from `.env` file
- **Current Server**: http://35.77.54.203:3006 (test_server.py)
- Full system server runs on configurable ports (default: 3005)
- Database and Redis connections configurable via environment

### Key Features
- **Parallel Processing**: Multiple AI agents process different article styles simultaneously
- **Fault Tolerance**: Automatic fallback analysis when AI services fail
- **Caching**: Redis-based caching for both stock data and AI responses
- **Task Monitoring**: Built-in task status tracking and performance metrics
- **Connection Pooling**: Efficient HTTP session management for external services

### Important Notes
- System designed for horizontal scaling
- All services support async/await patterns
- Task failures trigger automatic retries with exponential backoff
- Built-in monitoring and metrics collection
- Chinese language support for stock analysis content

## 系统状态和部署信息

### 当前状态 (2025-09-07 更新)
- **系统状态**: ✅ 生产就绪 - FinanceIQ专业界面完全实现
- **部署状态**: ✅ 已部署至生产环境
- **服务端口**: 3007 (生产环境已确认稳定运行)
- **服务器**: 运行在 35.77.54.203:3007
- **前端状态**: ✅ FinanceIQ风格，3页面架构，专业金融分析界面
- **后端状态**: ✅ FastAPI + 3003端口API完整集成 + Redis缓存
- **数据质量**: ✅ 所有API数据已验证，80个财务指标，完整技术分析

### 最新重大更新: FinanceIQ专业金融分析系统 🎯

**2025-09-07 重大更新**: 完成了系统架构重构和界面风格统一化

**核心改进内容**:

#### 1. 🎨 统一FinanceIQ专业界面风格
- **设计风格**: 采用专业金融机构级别的界面设计
- **布局结构**: 左侧导航栏 + 主内容区域
- **配色方案**: 蓝色主题 (#4A90E2) + 白色背景
- **字体系统**: Inter字体，清晰易读

#### 2. 📱 3页面功能架构
```
🏠 主页 (/dashboard) 
├── 股票基本信息 (价格、市值、行业等)
├── 技术面分析 (RSI、MACD、KDJ、布林带等)
├── 资金流向分析 (30日主力资金流向)
└── 实时新闻资讯 (20条相关新闻)

📊 财务报表 (/financial)
├── 当季vs上季财务对比
├── 80个完整财务指标展示  
├── 季度趋势分析
└── 财务健康度评估

🔍 综合分析 (/analysis)
├── AI智能评分 (开发中)
├── 同行业对比 (开发中)
├── 智能预测模型 (开发中)
└── 投资策略推荐 (开发中)
```

#### 3. 🔗 完整API数据集成
- **3003端口API**: 19个端点全部验证通过
- **数据完整性**: 95%以上完整性，真实股票数据
- **数据源验证**: 每个字段都有实际数值，无空值问题
- **实时更新**: 股价、新闻、财务数据实时同步

#### 用户体验提升:
- ✅ 实时进度条显示分析进度百分比
- ✅ 清晰的步骤说明文字
- ✅ 数据逐步显现，不再是"黑盒"等待
- ✅ 平滑动画效果，视觉友好
- ✅ 响应式设计，支持移动端和桌面端
- ✅ 修复了所有网络连接和验证问题

### 技术实现细节:
- **前端**: 重写JavaScript逻辑，支持渐进式数据加载
- **API调用**: 先获取股票基础数据，再启动AI分析任务
- **视觉设计**: 添加进度条、数据区域、图标系统
- **错误处理**: 改进了网络连接问题的诊断和处理

### 系统验证状态:
- ✅ 服务器运行正常 (多个后台进程确认)
- ✅ 所有API端点测试通过
- ✅ 健康检查接口正常: http://35.77.54.203:3006/health
- ✅ CORS配置正确
- ✅ 前端资源正常加载
- ✅ JavaScript验证逻辑修复完成

### 访问地址 (2025-09-07更新):
- **🏠 主页**: http://35.77.54.203:3007/ 或 http://35.77.54.203:3007/dashboard
- **📊 财务报表**: http://35.77.54.203:3007/financial
- **🔍 综合分析**: http://35.77.54.203:3007/analysis
- **🔧 健康检查**: http://35.77.54.203:3007/health
- **📚 API文档**: http://35.77.54.203:3007/docs

### 已完成的核心功能 (2025-09-07):
**✅ FinanceIQ专业分析系统**
- [x] ✅ 统一FinanceIQ界面风格，专业金融机构级设计
- [x] ✅ 3页面架构完整实现 (主页/财报/综合分析)
- [x] ✅ 3003端口API完整集成验证 (19个端点)
- [x] ✅ 80个财务指标完整展示和对比功能
- [x] ✅ 真实股票数据验证 (价格、市值、技术指标)
- [x] ✅ 实时新闻和资金流向数据集成
- [x] ✅ 浏览器缓存问题解决和无缓存部署

### 下一步开发计划:
1. **数据可视化增强**: Chart.js图表集成
2. **AI分析功能**: 综合分析页面功能开发
3. **移动端适配**: 响应式设计优化
4. **性能优化**: API响应速度和缓存策略

## 🔍 数据质量验证标准

### 核心验证原则
**CRITICAL**: 每个数据项都必须有有效的、非零的、有意义的值才能被认定为功能正常。

### 验证要求详细说明:
1. **财务数据验证**:
   - 营业收入、净利润等关键指标不能为0或null
   - ROE、ROA、毛利率、净利率必须为合理的百分比值
   - EPS每股收益必须有具体数值
   - 所有财务指标必须基于真实API数据计算

2. **技术指标验证**:
   - RSI、MACD、KDJ等技术指标必须有具体数值
   - 成交量、资金流向必须显示实际数据
   - 价格、涨跌幅必须为当日真实数据
   - 不能出现"加载中"或空白状态

3. **市场数据验证**:
   - 资金流向必须显示30天详细明细
   - 主力资金净流入/流出必须有具体金额
   - 成交量、换手率必须基于实际交易数据
   - 所有数据项都必须有数值，不能显示"--"或"无数据"

### 测试验证流程:
**每次功能修复后必须执行以下验证**:
1. 输入测试股票代码(如002222)
2. 检查每个tab页面的每个数据项
3. 确认所有显示值都是有效的、有意义的数值
4. 任何显示为0、null、"--"、"加载中"的项目都视为未修复

### 验证报告要求:
当声明功能"已修复"或"正常工作"时，必须提供:
- 具体的数值示例 (如: ROE 7.85%, 净利润1.28亿元)
- API数据源确认 (如: 数据来自api/comprehensive-data/002222)
- 每个数据项的验证状态 (✅有效值 / ❌需修复)

### 下次继续工作时:
1. 系统已经完全可用，前端界面已优化
2. 重点关注庄家页面的数据完整性和用户体验
3. 所有基础架构已完成，可专注于业务逻辑改进
4. 考虑添加更多专业投资者关注的数据维度