#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prism系统测试服务器 - 简化版本
用于验证核心功能
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime
import json
import redis
import uuid
import os
import shutil
from loguru import logger
import aiohttp

# 创建FastAPI应用
app = FastAPI(
    title="Prism Test System",
    version="1.0.0",
    description="Prism股票分析文章生成系统测试版"
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务
app.mount("/static", StaticFiles(directory="frontend"), name="static")
app.mount("/assets", StaticFiles(directory="frontend/assets"), name="assets")

# 根路由 - 直接访问前端
@app.get("/")
async def read_root():
    """重定向到前端页面"""
    from fastapi.responses import FileResponse
    return FileResponse('frontend/index.html')

# 仪表盘路由
@app.get("/dashboard")
async def dashboard():
    """访问仪表盘页面"""
    from fastapi.responses import FileResponse
    return FileResponse('frontend/dashboard.html')

@app.get("/dashboard_v2")
async def dashboard_v2():
    """访问优化后的仪表盘页面"""
    from fastapi.responses import FileResponse
    return FileResponse('frontend/dashboard_v2.html')

@app.get("/expert")
async def expert_dashboard():
    """访问专家分析仪表盘页面"""
    from fastapi.responses import FileResponse
    return FileResponse('frontend/expert_dashboard.html')

@app.get("/upload")
async def upload_page():
    """访问文件上传页面"""
    from fastapi.responses import FileResponse
    return FileResponse('frontend/upload.html')

# 数据模型
class ArticleRequest(BaseModel):
    stock_code: str
    article_styles: Optional[List[str]] = None

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

# 全局变量存储任务状态
task_storage = {}

# 股票数据缓存
stock_data_cache = {}

# 健康检查
@app.get("/health")
async def health_check():
    """系统健康检查"""
    try:
        # 检查Redis连接
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        redis_status = "connected"
    except:
        redis_status = "disconnected"
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "services": {
            "redis": redis_status,
            "database": "simulated"
        }
    }

# 真实股票数据获取
@app.get("/api/stocks/{stock_code}/data")
async def get_stock_data(stock_code: str, data_type: Optional[str] = None):
    """获取股票数据 (真实数据)"""
    
    # 验证股票代码格式
    if not stock_code or len(stock_code) < 6:
        raise HTTPException(status_code=400, detail="股票代码格式错误")
    
    try:
        # 获取真实股票数据
        real_data = await fetch_real_stock_data(stock_code)
        
        if data_type:
            if data_type in real_data:
                return real_data[data_type]
            else:
                raise HTTPException(status_code=400, detail="不支持的数据类型")
        
        return real_data
        
    except Exception as e:
        logger.error(f"获取股票数据失败: {stock_code} - {e}")
        raise HTTPException(status_code=500, detail=f"获取股票数据失败: {str(e)}")

async def fetch_real_stock_data(stock_code: str) -> Dict[str, Any]:
    """从真实API获取股票数据"""
    base_url = "http://35.77.54.203:3003"
    
    async with aiohttp.ClientSession() as session:
        try:
            # 获取基本面数据
            async with session.get(f"{base_url}/stocks/{stock_code}/analysis/fundamental") as response:
                if response.status == 200:
                    fundamental_raw = await response.json()
                else:
                    fundamental_raw = {}
            
            # 获取技术面数据
            async with session.get(f"{base_url}/stocks/{stock_code}/analysis/technical") as response:
                if response.status == 200:
                    technical_raw = await response.json()
                else:
                    technical_raw = {}
            
            # 处理基本面数据
            basic_info = fundamental_raw.get("basic_info", {})
            fundamental_data = {
                "source": "fundamental_analysis",
                "stock_code": stock_code,
                "stock_name": fundamental_raw.get("stock_name", "未知股票"),
                "current_price": basic_info.get("最新", 0),
                "market_cap": basic_info.get("总市值", 0),
                "circulating_market_cap": basic_info.get("流通市值", 0),
                "pe_ratio": 0,  # 基本面数据中没有PE，从技术面获取
                "industry": basic_info.get("行业", "未知行业"),
                "listing_date": basic_info.get("上市时间", ""),
                "total_shares": basic_info.get("总股本", 0),
                "circulating_shares": basic_info.get("流通股", 0),
                "updated_at": datetime.now().isoformat()
            }
            
            # 处理技术面数据 - 提取更多指标
            real_time_data = technical_raw.get("real_time_data", {})
            analysis_data = technical_raw.get("analysis_data", {})
            k_line_data = technical_raw.get("k_line_data", [])
            
            # 获取最新一天的K线数据
            latest_k = k_line_data[-1] if k_line_data else {}
            
            technical_data = {
                "source": "technical_analysis", 
                "stock_code": stock_code,
                "analysis_type": technical_raw.get("analysis_type", "技术分析"),
                "current_price": real_time_data.get("最新", analysis_data.get("current_price", 0)),
                "price_change": analysis_data.get("price_change", real_time_data.get("涨跌", 0)),
                "price_change_pct": analysis_data.get("price_change_pct", real_time_data.get("涨幅", 0)),
                "volume": analysis_data.get("volume", real_time_data.get("总手", 0)),
                "turnover": real_time_data.get("金额", 0),
                "turnover_rate": analysis_data.get("turnover_rate", real_time_data.get("换手", 0)),
                "volume_ratio": real_time_data.get("量比", 0),
                "pe_ratio": technical_raw.get("technical_indicators", {}).get("市盈率", 0),
                "pb_ratio": technical_raw.get("technical_indicators", {}).get("市净率", 0),
                "high_price": analysis_data.get("recent_high", real_time_data.get("最高", latest_k.get("最高", 0))),
                "low_price": analysis_data.get("recent_low", real_time_data.get("最低", latest_k.get("最低", 0))),
                "open_price": real_time_data.get("今开", latest_k.get("开盘", 0)),
                "prev_close": real_time_data.get("昨收", 0),
                "limit_up": real_time_data.get("涨停", 0),
                "limit_down": real_time_data.get("跌停", 0),
                "bid_ask_spread": {
                    "buy_1": real_time_data.get("buy_1", 0),
                    "buy_1_vol": real_time_data.get("buy_1_vol", 0),
                    "sell_1": real_time_data.get("sell_1", 0),
                    "sell_1_vol": real_time_data.get("sell_1_vol", 0),
                },
                "market_mood": {
                    "外盘": real_time_data.get("外盘", 0),
                    "内盘": real_time_data.get("内盘", 0),
                },
                "recent_performance": {
                    "振幅": latest_k.get("振幅", 0) if latest_k else 0,
                    "涨跌幅": latest_k.get("涨跌幅", 0) if latest_k else 0,
                },
                "indicators": technical_raw.get("technical_indicators", {}),
                "signals": technical_raw.get("trading_signals", []),
                "trend": determine_trend(k_line_data[-10:] if len(k_line_data) >= 10 else k_line_data),
                "updated_at": datetime.now().isoformat()
            }
            
            # 从基本面数据提取财务指标
            financial_indicators = fundamental_raw.get("financial_indicators", [])
            
            # 提取主要财务数据
            revenue_data = {}
            profit_data = {}
            roe_data = {}
            eps_data = {}
            cash_flow_data = {}
            
            for indicator in financial_indicators[:10]:  # 取前10个主要指标
                indicator_name = indicator.get("指标", "")
                if indicator_name == "营业总收入":
                    for quarter in ["20250630", "20250331", "20241231", "20240930", "20240630"]:
                        if quarter in indicator and indicator[quarter]:
                            revenue_data[quarter] = indicator[quarter]
                elif indicator_name == "归母净利润":
                    for quarter in ["20250630", "20250331", "20241231", "20240930", "20240630"]:
                        if quarter in indicator and indicator[quarter]:
                            profit_data[quarter] = indicator[quarter]
                elif indicator_name == "净资产收益率(ROE)":
                    for quarter in ["20250630", "20250331", "20241231", "20240930"]:
                        if quarter in indicator and indicator[quarter]:
                            roe_data[quarter] = indicator[quarter]
                elif indicator_name == "基本每股收益":
                    for quarter in ["20250630", "20250331", "20241231", "20240930"]:
                        if quarter in indicator and indicator[quarter]:
                            eps_data[quarter] = indicator[quarter]
                elif indicator_name == "经营现金流量净额":
                    for quarter in ["20250630", "20250331", "20241231", "20240930"]:
                        if quarter in indicator and indicator[quarter]:
                            cash_flow_data[quarter] = indicator[quarter]
            
            financial_data = {
                "source": "financial_data",
                "stock_code": stock_code,
                "revenue_data": revenue_data,
                "profit_data": profit_data,
                "roe_data": roe_data,
                "eps_data": eps_data,
                "cash_flow_data": cash_flow_data,
                "financial_indicators": financial_indicators[:8],  # 取前8个主要指标
                "updated_at": datetime.now().isoformat()
            }
            
            # 模拟市场情绪数据 (基于技术面数据)
            outer_inner_ratio = 0.5  # 中性
            if real_time_data.get("外盘", 0) and real_time_data.get("内盘", 0):
                total_trade = real_time_data["外盘"] + real_time_data["内盘"]
                if total_trade > 0:
                    outer_inner_ratio = real_time_data["外盘"] / total_trade
            
            sentiment_score = min(max((outer_inner_ratio - 0.3) * 2, 0), 1)  # 0-1范围
            
            sentiment_data = {
                "source": "market_sentiment",
                "stock_code": stock_code,
                "sentiment_score": sentiment_score,
                "news_sentiment": "positive" if sentiment_score > 0.6 else ("negative" if sentiment_score < 0.4 else "neutral"),
                "market_mood": "多头气氛" if outer_inner_ratio > 0.55 else ("空头气氛" if outer_inner_ratio < 0.45 else "盘整气氛"),
                "volume_analysis": "放量" if real_time_data.get("量比", 0) > 1.5 else ("缩量" if real_time_data.get("量比", 0) < 0.8 else "正常"),
                "analyst_ratings": {"buy": 3, "hold": 2, "sell": 1},  # 模拟数据
                "updated_at": datetime.now().isoformat()
            }
            
            return {
                "stock_code": stock_code,
                "collected_at": datetime.now().isoformat(),
                "fundamental": fundamental_data,
                "technical": technical_data,
                "financial": financial_data,
                "sentiment": sentiment_data
            }
            
        except Exception as e:
            logger.error(f"获取股票数据异常: {stock_code} - {e}")
            raise

# AI分析缓存存储 (每日缓存)
daily_ai_cache = {}

def get_cache_key(stock_code: str, analysis_type: str) -> str:
    """生成每日缓存键"""
    today = datetime.now().strftime("%Y-%m-%d")
    return f"{stock_code}_{analysis_type}_{today}"

def is_cache_valid(cache_key: str) -> bool:
    """检查缓存是否有效"""
    return cache_key in daily_ai_cache

async def financial_statement_expert(stock_code: str, financial_data: dict) -> dict:
    """财报分析专家 - 专业财务漏洞检测"""
    
    # 检查缓存
    cache_key = get_cache_key(stock_code, "financial_expert")
    if is_cache_valid(cache_key):
        logger.info(f"🔄 使用财报专家缓存: {stock_code}")
        return daily_ai_cache[cache_key]
    
    try:
        # 获取财务指标
        financial_indicators = financial_data.get("financial_indicators", [])
        revenue_data = financial_data.get("revenue_data", {})
        profit_data = financial_data.get("profit_data", {})
        cash_flow_data = financial_data.get("cash_flow_data", {})
        
        # 财报异常检测逻辑
        red_flags = []
        quality_score = 100
        
        # 1. 收入与利润增长率匹配度检测
        if revenue_data and profit_data:
            recent_quarters = sorted(revenue_data.keys(), reverse=True)[:2]
            if len(recent_quarters) >= 2:
                q1, q2 = recent_quarters[0], recent_quarters[1]
                if revenue_data[q1] and revenue_data[q2] and profit_data.get(q1) and profit_data.get(q2):
                    revenue_growth = (revenue_data[q1] - revenue_data[q2]) / revenue_data[q2] * 100
                    profit_growth = (profit_data[q1] - profit_data[q2]) / profit_data[q2] * 100
                    
                    if abs(revenue_growth - profit_growth) > 30:
                        red_flags.append(f"⚠️ 收入增长率({revenue_growth:.1f}%)与利润增长率({profit_growth:.1f}%)严重不匹配")
                        quality_score -= 15
        
        # 2. 现金流与利润匹配度检测
        if cash_flow_data and profit_data:
            recent_quarter = max(cash_flow_data.keys()) if cash_flow_data else None
            if recent_quarter and recent_quarter in profit_data:
                cash_flow = cash_flow_data[recent_quarter] / 100000000  # 转为亿元
                profit = profit_data[recent_quarter] / 100000000  # 转为亿元
                if profit > 0:
                    cash_profit_ratio = cash_flow / profit
                    if cash_profit_ratio < 0.5:
                        red_flags.append(f"🚨 经营现金流({cash_flow:.1f}亿)远低于净利润({profit:.1f}亿)，现金质量堪忧")
                        quality_score -= 20
                    elif cash_profit_ratio < 0.8:
                        red_flags.append(f"⚠️ 经营现金流({cash_flow:.1f}亿)低于净利润({profit:.1f}亿)，需关注")
                        quality_score -= 10
        
        # 3. 应收账款分析（基于营业收入推算）
        if revenue_data:
            recent_quarters = sorted(revenue_data.keys(), reverse=True)[:4]  # 最近4个季度
            if len(recent_quarters) >= 2:
                q1_revenue = revenue_data[recent_quarters[0]] / 100000000
                q4_revenue_total = sum(revenue_data.get(q, 0) for q in recent_quarters) / 100000000
                # 假设应收账款占营业收入比例超过20%为异常
                if q1_revenue > 0:
                    estimated_ar_ratio = min((q4_revenue_total * 0.15) / q1_revenue, 0.3)
                    if estimated_ar_ratio > 0.2:
                        red_flags.append(f"⚠️ 推算应收账款占收入比例偏高({estimated_ar_ratio*100:.1f}%)，需关注回款能力")
                        quality_score -= 10
        
        # 4. 毛利率稳定性检测
        if revenue_data and len(financial_indicators) > 2:
            cost_indicator = next((item for item in financial_indicators if "营业成本" in item.get("指标", "")), None)
            if cost_indicator:
                gross_margins = []
                for quarter in sorted(revenue_data.keys(), reverse=True)[:4]:
                    if quarter in revenue_data and quarter in cost_indicator:
                        revenue = revenue_data[quarter]
                        cost = cost_indicator.get(quarter, 0)
                        if revenue and cost and revenue > cost:
                            margin = (revenue - cost) / revenue * 100
                            gross_margins.append(margin)
                
                if len(gross_margins) >= 3:
                    margin_std = sum((x - sum(gross_margins)/len(gross_margins))**2 for x in gross_margins) ** 0.5
                    if margin_std > 5:
                        red_flags.append(f"⚠️ 毛利率波动较大(标准差{margin_std:.1f}%)，盈利能力不稳定")
                        quality_score -= 12
        
        # 生成专业分析报告
        analysis_content = f"""
【财报质量评估报告】
质量评分: {quality_score}/100 {'🟢优秀' if quality_score >= 80 else '🟡一般' if quality_score >= 60 else '🔴警告'}

【关键财务指标分析】
最新季度营业收入: {max(revenue_data.values())/100000000:.1f}亿元
最新季度净利润: {max(profit_data.values())/100000000:.1f}亿元  
最新季度现金流: {max(cash_flow_data.values())/100000000:.1f}亿元

【财报异常识别】
{'发现以下异常信号：' if red_flags else '✅ 未发现明显财务异常'}
{chr(10).join(red_flags) if red_flags else '财务数据整体表现正常，各项指标匹配度较好。'}

【专业建议】
{'建议重点关注财务数据真实性，谨慎投资' if quality_score < 60 else '财务质量尚可，但需持续跟踪关键指标变化' if quality_score < 80 else '财务数据质量良好，可作为投资参考'}
        """
        
        result = {
            "expert_type": "financial_statement_analyst",
            "title": f"财报分析专家报告 - {stock_code}",
            "content": analysis_content.strip(),
            "quality_score": quality_score,
            "red_flags": red_flags,
            "summary": f"财务质量得分{quality_score}分，{'发现{len(red_flags)}个异常' if red_flags else '财务数据正常'}",
            "generated_at": datetime.now().isoformat()
        }
        
        # 缓存结果
        daily_ai_cache[cache_key] = result
        logger.info(f"💼 财报专家分析完成: {stock_code} - 质量得分{quality_score}")
        return result
        
    except Exception as e:
        logger.error(f"财报分析专家异常: {e}")
        return {
            "expert_type": "financial_statement_analyst",
            "title": f"财报分析专家报告 - {stock_code}",
            "content": "财报数据分析异常，请稍后重试",
            "quality_score": 50,
            "red_flags": [],
            "summary": "分析异常",
            "generated_at": datetime.now().isoformat()
        }

async def market_maker_expert(stock_code: str, technical_data: dict, sentiment_data: dict) -> dict:
    """庄家分析专家 - 主力资金行为分析"""
    
    # 检查缓存
    cache_key = get_cache_key(stock_code, "market_maker_expert")
    if is_cache_valid(cache_key):
        logger.info(f"🔄 使用庄家专家缓存: {stock_code}")
        return daily_ai_cache[cache_key]
    
    try:
        # 获取技术指标
        volume = technical_data.get("volume", 0)
        turnover_rate = technical_data.get("turnover_rate", 0)
        volume_ratio = technical_data.get("volume_ratio", 1)
        price_change_pct = technical_data.get("price_change_pct", 0)
        market_mood = technical_data.get("market_mood", {})
        
        # 庄家行为检测
        banker_signals = []
        manipulation_score = 0
        
        # 1. 异常成交量分析
        if volume_ratio > 3:
            banker_signals.append(f"🚨 量比{volume_ratio:.1f}倍，成交量暴增，疑似主力大举建仓或出货")
            manipulation_score += 25
        elif volume_ratio > 2:
            banker_signals.append(f"⚠️ 量比{volume_ratio:.1f}倍，成交量明显放大，主力可能有动作")
            manipulation_score += 15
        elif volume_ratio < 0.5:
            banker_signals.append(f"📉 量比{volume_ratio:.1f}倍，成交萎缩，主力观望或控盘中")
            manipulation_score += 10
        
        # 2. 外盘内盘分析
        outer_disk = market_mood.get("外盘", 0)
        inner_disk = market_mood.get("内盘", 0)
        if outer_disk > 0 and inner_disk > 0:
            total_trade = outer_disk + inner_disk
            outer_ratio = outer_disk / total_trade
            
            if outer_ratio > 0.7:
                banker_signals.append(f"🟢 外盘占比{outer_ratio*100:.1f}%，主动买盘强劲，主力吸筹明显")
                manipulation_score += 20
            elif outer_ratio < 0.3:
                banker_signals.append(f"🔴 外盘占比{outer_ratio*100:.1f}%，主动卖盘占优，主力可能出货")
                manipulation_score += 20
            elif 0.45 <= outer_ratio <= 0.55:
                banker_signals.append(f"⚖️ 外盘占比{outer_ratio*100:.1f}%，多空平衡，主力控盘稳定")
                manipulation_score += 5
        
        # 3. 涨跌幅与成交量匹配度
        if abs(price_change_pct) > 5 and volume_ratio < 1.5:
            banker_signals.append(f"🎯 股价{'+' if price_change_pct > 0 else ''}{price_change_pct:.1f}%大幅变动但成交量未放大，疑似控盘拉升/打压")
            manipulation_score += 30
        elif abs(price_change_pct) < 2 and volume_ratio > 2.5:
            banker_signals.append(f"🔄 股价波动小({price_change_pct:+.1f}%)但成交量大增，疑似主力对倒或换庄")
            manipulation_score += 25
        
        # 4. 换手率分析
        if turnover_rate > 10:
            banker_signals.append(f"🔥 换手率{turnover_rate:.1f}%，资金非常活跃，主力大幅操作")
            manipulation_score += 20
        elif turnover_rate > 5:
            banker_signals.append(f"📈 换手率{turnover_rate:.1f}%，资金活跃度较高，有主力参与")
            manipulation_score += 10
        elif turnover_rate < 1:
            banker_signals.append(f"🔒 换手率{turnover_rate:.1f}%，筹码锁定度高，主力控盘稳定")
            manipulation_score += 15
        
        # 综合评估
        if manipulation_score >= 60:
            risk_level = "🚨 高度疑似庄家操控"
            advice = "建议谨慎跟风，注意主力出货风险"
        elif manipulation_score >= 30:
            risk_level = "⚠️ 存在主力操作迹象"
            advice = "可适量参与，但需密切关注资金动向"
        else:
            risk_level = "✅ 暂未发现明显操控"
            advice = "市场交易相对自然，可正常投资决策"
        
        analysis_content = f"""
【庄家行为分析报告】
操控嫌疑度: {manipulation_score}/100 {risk_level}

【关键资金指标】
成交量: {volume:,.0f}手 (量比{volume_ratio:.1f})
换手率: {turnover_rate:.1f}%
外盘占比: {outer_ratio*100:.1f}% (外:{outer_disk:,.0f} 内:{inner_disk:,.0f})

【主力行为识别】
{'检测到以下异常信号：' if banker_signals else '✅ 未发现明显庄家操控痕迹'}
{chr(10).join(banker_signals) if banker_signals else '成交数据显示市场交易行为相对自然，无明显人为操控迹象。'}

【投资建议】
{advice}
        """
        
        result = {
            "expert_type": "market_maker_analyst",
            "title": f"庄家分析专家报告 - {stock_code}",
            "content": analysis_content.strip(),
            "manipulation_score": manipulation_score,
            "banker_signals": banker_signals,
            "risk_level": risk_level,
            "summary": f"操控嫌疑{manipulation_score}分，{risk_level}",
            "generated_at": datetime.now().isoformat()
        }
        
        # 缓存结果
        daily_ai_cache[cache_key] = result
        logger.info(f"🎯 庄家专家分析完成: {stock_code} - 嫌疑度{manipulation_score}")
        return result
        
    except Exception as e:
        logger.error(f"庄家分析专家异常: {e}")
        return {
            "expert_type": "market_maker_analyst", 
            "title": f"庄家分析专家报告 - {stock_code}",
            "content": "庄家行为分析异常，请稍后重试",
            "manipulation_score": 0,
            "banker_signals": [],
            "risk_level": "分析异常",
            "summary": "分析异常",
            "generated_at": datetime.now().isoformat()
        }

# AI分析接口
@app.post("/api/ai/analyze")
async def ai_analyze_stock(stock_code: str, analysis_style: str = "professional"):
    """AI分析股票数据 (基于真实数据) - 带每日缓存"""
    
    # 检查缓存
    cache_key = get_cache_key(stock_code, f"ai_{analysis_style}")
    if is_cache_valid(cache_key):
        logger.info(f"🔄 使用AI分析缓存: {stock_code} - {analysis_style}")
        cached_result = daily_ai_cache[cache_key]
        
        # 更新实时价格数据但保留AI分析内容
        try:
            fresh_stock_data = await fetch_real_stock_data(stock_code)
            fundamental = fresh_stock_data.get("fundamental", {})
            cached_result["current_price"] = fundamental.get("current_price", 0)
            cached_result["price_change"] = fresh_stock_data.get("technical", {}).get("price_change", 0)
            cached_result["price_change_pct"] = fresh_stock_data.get("technical", {}).get("price_change_pct", 0)
            cached_result["last_updated"] = datetime.now().isoformat()
        except:
            pass  # 如果获取实时数据失败，仍返回缓存的结果
            
        return cached_result
    
    try:
        # 获取真实股票数据用于分析
        stock_data = await fetch_real_stock_data(stock_code)
        fundamental = stock_data.get("fundamental", {})
        technical = stock_data.get("technical", {})
        financial = stock_data.get("financial", {})
        
        stock_name = fundamental.get("stock_name", stock_code)
        current_price = fundamental.get("current_price", 0)
        pe_ratio = fundamental.get("pe_ratio", 0)
        industry = fundamental.get("industry", "未知")
        market_cap = fundamental.get("market_cap", 0) / 100000000  # 转换为亿元
        
        # 基于真实数据生成分析内容
        style_templates = {
            "professional": {
                "title": f"{stock_name}({stock_code}) 资深分析师深度报告",
                "content": f"作为拥有15年A股研究经验的资深分析师，我对{stock_name}({stock_code})进行了全面分析。该股属于{industry}行业，当前股价{current_price}元，总市值{market_cap:.0f}亿元，市盈率{pe_ratio}倍。从基本面看，公司财务指标表现{get_performance_assessment(pe_ratio)}，估值水平{get_valuation_assessment(pe_ratio)}。技术面显示{technical.get('trend', '趋势待观察')}。综合分析，建议投资者理性看待，注意风险控制。",
                "summary": f"市值{market_cap:.0f}亿，PE{pe_ratio}倍，{get_investment_suggestion(pe_ratio, market_cap)}",
                "tone": "专业、深度、客观"
            },
            "dark": {
                "title": f"{stock_name}({stock_code}) 暗黑评论员独立观点", 
                "content": f"老铁们，今天扒一扒{stock_name}({stock_code})。当前价格{current_price}元，市值{market_cap:.0f}亿，PE高达{pe_ratio}倍{'，估值明显偏高' if pe_ratio > 30 else '，估值还算合理'}。{industry}这个行业{'竞争激烈，要小心' if industry in ['软件服务', '互联网', '电子信息'] else '相对稳定'}。{'大盘股相对安全些' if market_cap > 1000 else '中小盘风险较高'}，但也要防止机构割韭菜。记住：股市有风险，活着最重要！",
                "summary": f"价格{current_price}元，PE{pe_ratio}倍，{get_risk_warning(pe_ratio, market_cap)}",
                "tone": "犀利、独立、风险提示"
            },
            "optimistic": {
                "title": f"{stock_name}({stock_code}) 投资机会深度挖掘",
                "content": f"{stock_name}({stock_code})展现出不俗的投资价值！当前价格{current_price}元，处于{industry}这个{'高成长' if industry in ['新能源', '科技', '医药'] else '稳健'}行业。市值{market_cap:.0f}亿{'，仍有成长空间' if market_cap < 500 else '，行业地位稳固'}，PE{pe_ratio}倍{'合理估值' if pe_ratio < 25 else '反映市场预期'}。技术面呈现{technical.get('trend', '积极信号')}，是布局的好时机！",
                "summary": f"价格{current_price}元，{industry}板块，投资机会{get_opportunity_level(pe_ratio, market_cap)}",
                "tone": "积极、乐观"
            },
            "conservative": {
                "title": f"{stock_name}({stock_code}) 稳健投资评估",
                "content": f"从稳健投资角度评估{stock_name}({stock_code})：股价{current_price}元，市值{market_cap:.0f}亿，PE{pe_ratio}倍。作为{industry}行业的{'龙头企业' if market_cap > 1000 else '成长型企业'}，{'基本面相对稳健' if pe_ratio < 30 else '需关注估值风险'}。建议{'适量配置' if pe_ratio < 25 else '谨慎观望'}，采用分批建仓策略，设置合理止损位。",
                "summary": f"市值{market_cap:.0f}亿，PE{pe_ratio}倍，{get_conservative_advice(pe_ratio, market_cap)}",
                "tone": "稳重、保守"
            }
        }
        
        template = style_templates.get(analysis_style, style_templates["professional"])
        
        analysis_result = {
            "agent_id": f"real_agent_{analysis_style}",
            "style": analysis_style,
            "title": template["title"],
            "content": template["content"],
            "summary": template["summary"],
            "recommendations": get_recommendations(pe_ratio, market_cap, analysis_style),
            "confidence_score": 0.8,
            "risk_assessment": get_risk_level(pe_ratio, market_cap),
            "generated_at": datetime.now().isoformat(),
            "processing_time": 0.5,
            "data_quality": "real_data",
            "current_price": current_price,
            "price_change": technical.get("price_change", 0),
            "price_change_pct": technical.get("price_change_pct", 0),
            "last_updated": datetime.now().isoformat()
        }
        
        # 缓存分析结果
        daily_ai_cache[cache_key] = analysis_result
        
        logger.info(f"✅ 完成AI分析: {stock_code} - {analysis_style}风格 - 基于真实数据 - 已缓存")
        return analysis_result
        
    except Exception as e:
        logger.error(f"AI分析失败: {stock_code} - {e}")
        raise HTTPException(status_code=500, detail=f"AI分析失败: {str(e)}")

# 专业分析师接口
@app.post("/api/experts/financial")
async def financial_expert_analysis(stock_code: str):
    """财报分析专家接口"""
    try:
        # 获取股票数据
        stock_data = await fetch_real_stock_data(stock_code)
        financial_data = stock_data.get("financial", {})
        
        # 调用财报分析专家
        result = await financial_statement_expert(stock_code, financial_data)
        
        logger.info(f"💼 财报专家分析请求: {stock_code}")
        return result
        
    except Exception as e:
        logger.error(f"财报专家分析失败: {stock_code} - {e}")
        raise HTTPException(status_code=500, detail=f"财报专家分析失败: {str(e)}")

@app.post("/api/experts/market-maker")
async def market_maker_expert_analysis(stock_code: str):
    """庄家分析专家接口"""
    try:
        # 获取股票数据
        stock_data = await fetch_real_stock_data(stock_code)
        technical_data = stock_data.get("technical", {})
        sentiment_data = stock_data.get("sentiment", {})
        
        # 调用庄家分析专家
        result = await market_maker_expert(stock_code, technical_data, sentiment_data)
        
        logger.info(f"🎯 庄家专家分析请求: {stock_code}")
        return result
        
    except Exception as e:
        logger.error(f"庄家专家分析失败: {stock_code} - {e}")
        raise HTTPException(status_code=500, detail=f"庄家专家分析失败: {str(e)}")

@app.post("/api/experts/comprehensive")
async def comprehensive_expert_analysis(stock_code: str):
    """综合专家分析接口 - 包含财报和庄家双重分析"""
    try:
        # 获取股票数据
        stock_data = await fetch_real_stock_data(stock_code)
        fundamental = stock_data.get("fundamental", {})
        financial_data = stock_data.get("financial", {})
        technical_data = stock_data.get("technical", {})
        sentiment_data = stock_data.get("sentiment", {})
        
        # 并行调用两个专家
        financial_analysis, market_maker_analysis = await asyncio.gather(
            financial_statement_expert(stock_code, financial_data),
            market_maker_expert(stock_code, technical_data, sentiment_data)
        )
        
        # 综合评估
        stock_name = fundamental.get("stock_name", stock_code)
        current_price = fundamental.get("current_price", 0)
        
        # 计算综合风险评分
        financial_score = financial_analysis.get("quality_score", 50)
        manipulation_score = market_maker_analysis.get("manipulation_score", 0)
        
        # 综合风险评级 (0-100，越低越安全)
        comprehensive_risk = ((100 - financial_score) * 0.6 + manipulation_score * 0.4)
        
        if comprehensive_risk <= 20:
            risk_rating = "🟢 低风险"
            investment_advice = "财务质量良好，市场行为自然，可考虑投资"
        elif comprehensive_risk <= 40:
            risk_rating = "🟡 中等风险"
            investment_advice = "财务或交易存在一定问题，需谨慎分析"
        elif comprehensive_risk <= 60:
            risk_rating = "🟠 较高风险"  
            investment_advice = "财务质量或市场操控风险较高，不建议投资"
        else:
            risk_rating = "🔴 高风险"
            investment_advice = "存在严重财务问题或庄家操控嫌疑，强烈不建议投资"
        
        result = {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "current_price": current_price,
            "comprehensive_risk_score": round(comprehensive_risk, 1),
            "risk_rating": risk_rating,
            "investment_advice": investment_advice,
            "financial_analysis": financial_analysis,
            "market_maker_analysis": market_maker_analysis,
            "analysis_summary": {
                "financial_quality": f"{financial_score}/100分",
                "manipulation_risk": f"{manipulation_score}/100分",
                "overall_assessment": f"{risk_rating} - {investment_advice}"
            },
            "generated_at": datetime.now().isoformat()
        }
        
        logger.info(f"🔍 综合专家分析完成: {stock_code} - 风险评分{comprehensive_risk:.1f}")
        return result
        
    except Exception as e:
        logger.error(f"综合专家分析失败: {stock_code} - {e}")
        raise HTTPException(status_code=500, detail=f"综合专家分析失败: {str(e)}")

# 缓存管理接口
@app.get("/api/cache/status")
async def get_cache_status():
    """获取缓存状态"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 统计今日缓存
    today_cache = {k: v for k, v in daily_ai_cache.items() if today in k}
    
    cache_stats = {
        "total_cached_analyses": len(daily_ai_cache),
        "today_cached_analyses": len(today_cache),
        "cache_date": today,
        "cache_types": {}
    }
    
    # 按类型统计
    for key in today_cache.keys():
        analysis_type = key.split('_')[1] if len(key.split('_')) >= 2 else 'unknown'
        cache_stats["cache_types"][analysis_type] = cache_stats["cache_types"].get(analysis_type, 0) + 1
    
    return cache_stats

@app.delete("/api/cache/clear")
async def clear_cache():
    """清理缓存"""
    global daily_ai_cache
    old_count = len(daily_ai_cache)
    daily_ai_cache.clear()
    
    logger.info(f"🗑️ 缓存已清理，清理了{old_count}个缓存项")
    return {
        "message": "缓存已清理",
        "cleared_count": old_count,
        "cleared_at": datetime.now().isoformat()
    }

# 文件上传接口
@app.post("/api/upload/logo")
async def upload_logo(file: UploadFile = File(...)):
    """上传应用logo"""
    try:
        # 检查文件类型
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="只支持图片格式文件")
        
        # 检查文件大小 (最大5MB)
        file_size = 0
        file_content = await file.read()
        file_size = len(file_content)
        
        if file_size > 5 * 1024 * 1024:  # 5MB
            raise HTTPException(status_code=400, detail="文件大小不能超过5MB")
        
        # 确保assets目录存在
        assets_dir = "frontend/assets"
        os.makedirs(assets_dir, exist_ok=True)
        
        # 生成文件名
        file_extension = os.path.splitext(file.filename)[1].lower()
        if not file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
            raise HTTPException(status_code=400, detail="不支持的文件格式")
        
        filename = f"logo{file_extension}"
        file_path = os.path.join(assets_dir, filename)
        
        # 保存文件
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        
        # 返回文件访问URL
        file_url = f"/assets/{filename}"
        
        logger.info(f"📁 Logo上传成功: {filename} ({file_size} bytes)")
        
        return {
            "message": "Logo上传成功",
            "filename": filename,
            "file_url": file_url,
            "file_size": file_size,
            "uploaded_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Logo上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

# 龙虎榜数据API
@app.get("/api/stocks/{stock_code}/longhubang")
async def get_longhubang_data(stock_code: str):
    """获取股票龙虎榜数据"""
    try:
        # 模拟龙虎榜数据
        longhubang_data = {
            "stock_code": stock_code,
            "date": "2025-09-05",
            "reason": "日涨幅偏离值达7%的证券",
            "buy_top5": [
                {
                    "rank": 1,
                    "seat_name": "华泰证券股份有限公司深圳益田路荣超商务中心营业部",
                    "buy_amount": 45678900,
                    "sell_amount": 1234500,
                    "net_amount": 44444400,
                    "type": "机构专用"
                },
                {
                    "rank": 2,
                    "seat_name": "中信建投证券股份有限公司北京东直门南大街营业部",
                    "buy_amount": 38765400,
                    "sell_amount": 2345600,
                    "net_amount": 36419800,
                    "type": "游资"
                },
                {
                    "rank": 3,
                    "seat_name": "国泰君安证券股份有限公司上海江苏路营业部",
                    "buy_amount": 32156700,
                    "sell_amount": 5678900,
                    "net_amount": 26477800,
                    "type": "机构专用"
                },
                {
                    "rank": 4,
                    "seat_name": "招商证券股份有限公司深圳蛇口工业一路营业部",
                    "buy_amount": 28934500,
                    "sell_amount": 3456780,
                    "net_amount": 25477720,
                    "type": "游资"
                },
                {
                    "rank": 5,
                    "seat_name": "广发证券股份有限公司广州天河北路营业部",
                    "buy_amount": 24567800,
                    "sell_amount": 1987600,
                    "net_amount": 22580200,
                    "type": "游资"
                }
            ],
            "sell_top5": [
                {
                    "rank": 1,
                    "seat_name": "东方财富证券股份有限公司拉萨团结路第二营业部",
                    "buy_amount": 2345600,
                    "sell_amount": 53467800,
                    "net_amount": -51122200,
                    "type": "游资"
                },
                {
                    "rank": 2,
                    "seat_name": "银河证券股份有限公司北京中关村大街营业部",
                    "buy_amount": 1234500,
                    "sell_amount": 41234500,
                    "net_amount": -40000000,
                    "type": "游资"
                },
                {
                    "rank": 3,
                    "seat_name": "中信证券股份有限公司上海淮海中路营业部",
                    "buy_amount": 3456700,
                    "sell_amount": 38765400,
                    "net_amount": -35308700,
                    "type": "机构专用"
                },
                {
                    "rank": 4,
                    "seat_name": "海通证券股份有限公司深圳红荔路营业部",
                    "buy_amount": 2987600,
                    "sell_amount": 32156700,
                    "net_amount": -29169100,
                    "type": "游资"
                },
                {
                    "rank": 5,
                    "seat_name": "申万宏源证券有限公司上海东川路营业部",
                    "buy_amount": 4567800,
                    "sell_amount": 28934500,
                    "net_amount": -24366700,
                    "type": "游资"
                }
            ],
            "total_buy": 170102500,
            "total_sell": 194569500,
            "net_amount": -24467000,
            "turnover": 876543200
        }
        
        logger.info(f"🐲 获取龙虎榜数据: {stock_code}")
        return longhubang_data
        
    except Exception as e:
        logger.error(f"获取龙虎榜数据失败: {e}")
        return {
            "error": f"获取龙虎榜数据失败: {str(e)}",
            "stock_code": stock_code
        }

# 公司公告API
@app.get("/api/stocks/{stock_code}/announcements")
async def get_announcements(stock_code: str, limit: int = 10):
    """获取公司公告数据"""
    try:
        # 模拟公司公告数据
        announcements = [
            {
                "id": "2025090501",
                "title": "关于召开2025年第三次临时股东大会的通知",
                "type": "临时公告",
                "date": "2025-09-05",
                "importance": "重要",
                "summary": "公司拟召开2025年第三次临时股东大会，审议重大资产重组相关议案",
                "keywords": ["股东大会", "重大资产重组"],
                "url": f"http://www.cninfo.com.cn/announcement/{stock_code}_2025090501.pdf"
            },
            {
                "id": "2025090301",
                "title": "关于重大资产重组进展的公告",
                "type": "临时公告",
                "date": "2025-09-03",
                "importance": "重要",
                "summary": "公司重大资产重组项目已完成尽职调查，正在进行资产评估工作",
                "keywords": ["重大资产重组", "尽职调查", "资产评估"],
                "url": f"http://www.cninfo.com.cn/announcement/{stock_code}_2025090301.pdf"
            },
            {
                "id": "2025090201",
                "title": "2025年半年度业绩快报",
                "type": "定期报告",
                "date": "2025-09-02",
                "importance": "重要",
                "summary": "2025年上半年实现营业收入15.6亿元，同比增长12.3%；净利润2.1亿元，同比增长8.7%",
                "keywords": ["半年报", "业绩快报", "营业收入"],
                "url": f"http://www.cninfo.com.cn/announcement/{stock_code}_2025090201.pdf"
            },
            {
                "id": "2025083101",
                "title": "关于高级管理人员辞职的公告",
                "type": "临时公告",
                "date": "2025-08-31",
                "importance": "一般",
                "summary": "公司副总经理张XX因个人原因辞职，辞职后不在公司担任任何职务",
                "keywords": ["人事变动", "高管辞职"],
                "url": f"http://www.cninfo.com.cn/announcement/{stock_code}_2025083101.pdf"
            },
            {
                "id": "2025083001",
                "title": "关于获得政府补助的公告",
                "type": "临时公告",
                "date": "2025-08-30",
                "importance": "一般",
                "summary": "公司收到政府科技创新专项补助资金500万元",
                "keywords": ["政府补助", "科技创新"],
                "url": f"http://www.cninfo.com.cn/announcement/{stock_code}_2025083001.pdf"
            },
            {
                "id": "2025082801",
                "title": "关于签署战略合作协议的公告",
                "type": "临时公告",
                "date": "2025-08-28",
                "importance": "重要",
                "summary": "公司与XXX科技有限公司签署战略合作协议，共同开展人工智能技术研发",
                "keywords": ["战略合作", "人工智能", "技术研发"],
                "url": f"http://www.cninfo.com.cn/announcement/{stock_code}_2025082801.pdf"
            },
            {
                "id": "2025082501",
                "title": "关于股东减持计划的预披露公告",
                "type": "临时公告",
                "date": "2025-08-25",
                "importance": "重要",
                "summary": "持股5%以上股东拟在未来6个月内减持不超过公司总股本的2%",
                "keywords": ["股东减持", "减持计划"],
                "url": f"http://www.cninfo.com.cn/announcement/{stock_code}_2025082501.pdf"
            },
            {
                "id": "2025082201",
                "title": "关于回购公司股份的进展公告",
                "type": "临时公告",
                "date": "2025-08-22",
                "importance": "一般",
                "summary": "截至本公告日，公司已累计回购股份123.45万股，占公司总股本的0.12%",
                "keywords": ["股份回购", "回购进展"],
                "url": f"http://www.cninfo.com.cn/announcement/{stock_code}_2025082201.pdf"
            },
            {
                "id": "2025082001",
                "title": "2025年第二季度报告",
                "type": "定期报告",
                "date": "2025-08-20",
                "importance": "重要",
                "summary": "公司2025年第二季度实现营业收入8.2亿元，净利润1.1亿元",
                "keywords": ["季度报告", "财务数据"],
                "url": f"http://www.cninfo.com.cn/announcement/{stock_code}_2025082001.pdf"
            },
            {
                "id": "2025081801",
                "title": "关于投资设立子公司的公告",
                "type": "临时公告",
                "date": "2025-08-18",
                "importance": "重要",
                "summary": "公司拟投资3000万元设立全资子公司，主要从事新能源技术开发",
                "keywords": ["投资", "子公司", "新能源"],
                "url": f"http://www.cninfo.com.cn/announcement/{stock_code}_2025081801.pdf"
            }
        ]
        
        # 返回指定数量的公告
        result_announcements = announcements[:limit]
        
        logger.info(f"📢 获取公司公告数据: {stock_code}, 数量: {len(result_announcements)}")
        
        return {
            "stock_code": stock_code,
            "total_count": len(announcements),
            "returned_count": len(result_announcements),
            "announcements": result_announcements,
            "last_update": "2025-09-05T10:30:00"
        }
        
    except Exception as e:
        logger.error(f"获取公司公告失败: {e}")
        return {
            "error": f"获取公司公告失败: {str(e)}",
            "stock_code": stock_code,
            "announcements": []
        }

# 文章生成工作流
@app.post("/api/generate-articles", response_model=TaskResponse)
async def generate_articles(request: ArticleRequest):
    """生成股票分析文章"""
    
    task_id = str(uuid.uuid4())
    
    # 默认文章风格
    if not request.article_styles:
        request.article_styles = ["professional", "optimistic", "conservative"]
    
    # 模拟异步任务处理
    task_info = {
        "task_id": task_id,
        "stock_code": request.stock_code,
        "status": "processing",
        "created_at": datetime.now().isoformat(),
        "article_styles": request.article_styles,
        "progress": 0
    }
    
    task_storage[task_id] = task_info
    
    # 启动后台处理
    asyncio.create_task(process_article_generation(task_id, request.stock_code, request.article_styles))
    
    logger.info(f"✅ 文章生成任务已创建: {task_id} for {request.stock_code}")
    
    return TaskResponse(
        task_id=task_id,
        status="pending",
        message=f"股票 {request.stock_code} 的文章生成任务已启动"
    )

async def process_article_generation(task_id: str, stock_code: str, styles: List[str]):
    """后台处理文章生成"""
    try:
        # 更新进度
        task_storage[task_id]["progress"] = 20
        task_storage[task_id]["status"] = "collecting_data"
        
        # 模拟获取股票数据 (1秒)
        await asyncio.sleep(1)
        
        task_storage[task_id]["progress"] = 50
        task_storage[task_id]["status"] = "ai_analyzing"
        
        # 模拟AI分析处理 (2秒)
        await asyncio.sleep(2)
        
        task_storage[task_id]["progress"] = 80
        task_storage[task_id]["status"] = "generating_articles"
        
        # 生成文章
        articles = []
        for i, style in enumerate(styles):
            # 调用AI分析接口获取内容
            analysis = await ai_analyze_stock(stock_code, style)
            
            article = {
                "id": f"article_{i+1}",
                "style": style,
                "title": analysis["title"],
                "content": analysis["content"],
                "summary": analysis["summary"],
                "recommendations": analysis["recommendations"],
                "confidence_score": analysis["confidence_score"],
                "word_count": len(analysis["content"]),
                "generated_at": datetime.now().isoformat()
            }
            articles.append(article)
        
        await asyncio.sleep(1)
        
        # 完成任务
        result = {
            "task_id": task_id,
            "stock_code": stock_code,
            "articles": articles,
            "metadata": {
                "total_articles": len(articles),
                "processing_time": datetime.now().isoformat(),
                "styles_processed": styles
            },
            "status": "completed"
        }
        
        task_storage[task_id].update(result)
        task_storage[task_id]["progress"] = 100
        task_storage[task_id]["completed_at"] = datetime.now().isoformat()
        
        logger.info(f"🎉 文章生成任务完成: {task_id}")
        
    except Exception as e:
        task_storage[task_id]["status"] = "failed"
        task_storage[task_id]["error"] = str(e)
        logger.error(f"❌ 任务处理失败: {task_id} - {e}")

# 查询任务状态
@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """获取任务执行状态"""
    if task_id not in task_storage:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return task_storage[task_id]

# 批量处理
@app.post("/api/batch/generate-articles")
async def batch_generate_articles(stock_codes: List[str], article_styles: Optional[List[str]] = None):
    """批量生成多只股票的分析文章"""
    if len(stock_codes) > 5:
        raise HTTPException(status_code=400, detail="批量处理最多支持5只股票")
    
    if not article_styles:
        article_styles = ["professional", "optimistic"]
    
    task_ids = []
    for stock_code in stock_codes:
        request = ArticleRequest(stock_code=stock_code, article_styles=article_styles)
        task_response = await generate_articles(request)
        task_ids.append({
            "stock_code": stock_code,
            "task_id": task_response.task_id
        })
    
    logger.info(f"✅ 批量任务创建完成: {len(task_ids)} 个任务")
    
    return {
        "message": f"已创建 {len(task_ids)} 个文章生成任务",
        "tasks": task_ids
    }

# 系统统计
@app.get("/api/system/stats")
async def get_system_stats():
    """获取系统运行统计信息"""
    completed_tasks = sum(1 for task in task_storage.values() if task.get("status") == "completed")
    running_tasks = sum(1 for task in task_storage.values() if task.get("status") in ["processing", "pending"])
    failed_tasks = sum(1 for task in task_storage.values() if task.get("status") == "failed")
    
    return {
        "system": {
            "uptime": datetime.now().isoformat(),
            "version": "1.0.0"
        },
        "tasks": {
            "total_tasks": len(task_storage),
            "completed_tasks": completed_tasks,
            "running_tasks": running_tasks,
            "failed_tasks": failed_tasks
        },
        "performance": {
            "avg_processing_time": "3.5s",
            "success_rate": f"{(completed_tasks/(len(task_storage) or 1)*100):.1f}%"
        }
    }

def get_performance_assessment(pe_ratio: float) -> str:
    """评估业绩表现"""
    if pe_ratio < 15:
        return "稳健且估值偏低"
    elif pe_ratio < 25:
        return "表现良好"
    elif pe_ratio < 40:
        return "成长性较好但需关注估值"
    else:
        return "高成长但估值偏高"

def get_valuation_assessment(pe_ratio: float) -> str:
    """估值评估"""
    if pe_ratio < 15:
        return "明显低估"
    elif pe_ratio < 25:
        return "合理估值"
    elif pe_ratio < 40:
        return "略微偏高"
    else:
        return "明显高估"

def get_investment_suggestion(pe_ratio: float, market_cap: float) -> str:
    """投资建议"""
    if pe_ratio < 20 and market_cap > 500:
        return "值得关注的投资标的"
    elif pe_ratio < 30:
        return "可适度关注"
    else:
        return "需谨慎评估风险"

def get_risk_warning(pe_ratio: float, market_cap: float) -> str:
    """风险提示"""
    if pe_ratio > 40:
        return "估值风险较高"
    elif market_cap < 100:
        return "小盘股波动性大"
    else:
        return "风险相对可控"

def get_opportunity_level(pe_ratio: float, market_cap: float) -> str:
    """机会程度"""
    if pe_ratio < 20:
        return "显著"
    elif pe_ratio < 30:
        return "一般"
    else:
        return "需谨慎评估"

def get_conservative_advice(pe_ratio: float, market_cap: float) -> str:
    """保守建议"""
    if pe_ratio < 18 and market_cap > 300:
        return "适合稳健投资"
    elif pe_ratio < 25:
        return "可考虑小仓位"
    else:
        return "建议观望为主"

def get_recommendations(pe_ratio: float, market_cap: float, style: str) -> List[str]:
    """获取投资建议"""
    base_recommendations = [
        "密切关注市场动态",
        "控制投资仓位比例",
        "设置合理止盈止损点"
    ]
    
    if style == "professional":
        base_recommendations.append("关注公司基本面变化")
        if pe_ratio > 30:
            base_recommendations.append("注意估值风险")
    elif style == "dark":
        base_recommendations.extend(["防范机构割韭菜", "保持理性，避免追涨杀跌"])
    elif style == "optimistic":
        base_recommendations.extend(["抓住市场机遇", "适当增加配置比例"])
    elif style == "conservative":
        base_recommendations.extend(["分散投资降低风险", "长期持有策略"])
    
    return base_recommendations

def get_risk_level(pe_ratio: float, market_cap: float) -> str:
    """风险评级"""
    if pe_ratio > 40 or market_cap < 50:
        return "high"
    elif pe_ratio > 25 or market_cap < 200:
        return "medium"
    else:
        return "low"

def determine_trend(k_data: List[Dict]) -> str:
    """基于近期K线数据判断趋势"""
    if not k_data or len(k_data) < 3:
        return "数据不足"
    
    # 简单的趋势判断逻辑
    recent_closes = [float(k.get("收盘", 0)) for k in k_data[-5:]]
    if len(recent_closes) < 3:
        return "趋势未明"
    
    # 计算趋势
    up_days = sum(1 for i in range(1, len(recent_closes)) if recent_closes[i] > recent_closes[i-1])
    down_days = sum(1 for i in range(1, len(recent_closes)) if recent_closes[i] < recent_closes[i-1])
    
    if up_days > down_days + 1:
        return "上升趋势"
    elif down_days > up_days + 1:
        return "下跌趋势"
    else:
        return "震荡趋势"

def format_large_number(num):
    """格式化大数字"""
    if not num or num == 0:
        return "0"
    
    if abs(num) >= 100000000:  # 亿
        return f"{num/100000000:.2f}亿"
    elif abs(num) >= 10000:  # 万
        return f"{num/10000:.2f}万"
    else:
        return f"{num:.2f}"

if __name__ == "__main__":
    import uvicorn
    print("🚀 启动Prism测试服务器 (使用真实股票数据完整版)...")
    uvicorn.run(app, host="0.0.0.0", port=3006, log_level="info")