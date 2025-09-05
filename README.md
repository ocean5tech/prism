# Prism - 智能股票分析系统

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com/)

## 🎯 项目概述

Prism 是一个高性能的股票分析系统，提供实时股票数据获取、技术面分析、基本面分析和AI智能投资建议。系统采用渐进式用户界面设计，让用户实时看到分析进度和结果。

## ✨ 核心功能

### 📊 股票数据分析
- **基础信息**: 实时股价、市值、PE比率、行业分类
- **技术分析**: RSI、MACD、移动均线、趋势判断
- **基本面分析**: 财务指标、估值数据、业绩评估
- **市场情绪**: 新闻情绪分析、分析师评级、市场热度

### 🤖 AI智能分析
- **双重视角**: 资深分析师 + 暗黑评论员的不同观点
- **实时生成**: 基于最新数据的动态投资建议
- **风险评估**: 多维度风险分析和预警

### 🎨 渐进式用户体验
- **实时进度**: 分析进度条，告别"黑盒"等待
- **逐步展示**: 数据分步骤呈现，用户体验友好
- **响应式设计**: 支持桌面端和移动端访问
- **平滑动画**: 视觉效果优雅，操作流畅

## 🏗️ 系统架构

### 技术栈
```
前端: HTML5 + CSS3 + Vanilla JavaScript
后端: FastAPI + Python 3.12
缓存: Redis
数据源: 多源股票数据API
AI集成: 模拟智能分析引擎
```

### 架构设计
```
用户输入 → 数据验证 → 基础数据获取 → AI分析引擎 → 结果聚合 → 渐进式展示
    ↓           ↓            ↓            ↓           ↓           ↓
  10%        20%          45%          75%        95%        100%
```

## 🚀 快速开始

### 环境要求
- Python 3.12+
- Redis 服务器
- 网络连接（用于获取股票数据）

### 安装与运行

1. **克隆项目**
```bash
git clone https://github.com/ocean5tech/prism.git
cd prism
```

2. **创建虚拟环境**
```bash
python -m venv prism_venv
source prism_venv/bin/activate  # Linux/Mac
# prism_venv\Scripts\activate  # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，配置必要参数
```

5. **启动服务**
```bash
# 启动渐进式测试服务器（推荐）
source prism_venv/bin/activate && python test_server.py

# 或启动完整系统
uvicorn src.api.main:app --host 0.0.0.0 --port 3005 --reload
```

### 访问系统
- **主界面**: http://localhost:3006/
- **健康检查**: http://localhost:3006/health
- **API文档**: http://localhost:3006/docs

## 📁 项目结构

```
prism/
├── src/                    # 核心源代码
│   ├── api/               # API路由和控制器
│   ├── core/              # 核心业务逻辑
│   ├── services/          # 外部服务集成
│   └── workers/           # 后台任务处理器
├── frontend/              # 前端静态文件
│   ├── css/              # 样式文件
│   ├── js/               # JavaScript文件
│   └── index.html        # 主页面
├── tests/                 # 测试用例
├── config/                # 配置文件
├── scripts/               # 部署脚本
├── test_server.py         # 测试服务器
├── requirements.txt       # Python依赖
├── .env.example          # 环境变量模板
└── README.md             # 项目说明
```

## 🔧 开发指南

### API接口

#### 获取股票基础信息
```http
GET /api/stock/{stock_code}/basic
```

#### 启动AI分析任务
```http
POST /api/stock/{stock_code}/analyze
```

#### 查询分析结果
```http
GET /api/analysis/{task_id}/status
```

### 本地开发

```bash
# 代码格式化
python -m black src/

# 代码检查
python -m flake8 src/

# 运行测试
pytest tests/
```

## 📈 系统特色

### 🎨 渐进式用户体验
- ✅ **实时进度反馈**: 不再是"黑盒"等待，用户清楚看到每个分析步骤
- ✅ **分步数据展示**: 基础信息 → 技术分析 → 基本面 → 市场情绪 → AI观点
- ✅ **平滑视觉效果**: 专业的动画和过渡效果
- ✅ **响应式设计**: 完美适配各种设备屏幕

### 🔍 智能分析引擎
- **多维度分析**: 技术面、基本面、市场情绪三位一体
- **AI双重视角**: 理性分析师 + 犀利评论员，提供全面观点
- **实时数据源**: 基于最新市场数据的动态分析

### ⚡ 高性能架构
- **异步处理**: FastAPI异步框架，高并发支持
- **智能缓存**: Redis缓存机制，减少重复计算
- **模块化设计**: 清晰的代码结构，易于维护和扩展

## 🌟 版本历史

### v1.0.0 (当前) - 渐进式体验版
- ✅ 实现渐进式用户界面
- ✅ 完整的股票分析流程
- ✅ 双AI分析师观点系统
- ✅ 响应式前端设计
- ✅ 健康检查和监控接口

### 下一版本计划
- 📋 增加更多股票数据源
- 📋 实现用户账户和历史记录
- 📋 添加技术指标可视化图表
- 📋 支持投资组合分析

## 🤝 贡献指南

欢迎提交 Issues 和 Pull Requests！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启 Pull Request

## 📝 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 📞 联系方式

- 项目主页: https://github.com/ocean5tech/prism
- 问题反馈: https://github.com/ocean5tech/prism/issues

---

⭐ 如果这个项目对您有帮助，请给我们一个 Star！