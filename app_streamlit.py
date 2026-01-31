import streamlit as st
from streamlit_echarts import st_echarts
import yfinance as yf
import pandas as pd
from datetime import datetime

# --- 1. 页面配置 ---
st.set_page_config(layout="wide", page_title="Stock Analyzer Pro")

# --- 2. 注入 CSS (保持黑金风格) ---
st.markdown("""
<style>
    /* 全局背景 */
    .stApp { background-color: #0f1115; }
    
    /* 侧边栏 */
    [data-testid="stSidebar"] { background-color: #181b21; border-right: 1px solid #333; }
    
    /* 字体颜色 */
    h1, h2, h3, p, span, div, label { color: #e1e1e1; font-family: 'Segoe UI', Roboto, sans-serif; }
    
    /* 输入框 */
    .stTextInput > div > div > input, .stNumberInput > div > div > input {
        color: #fff; background-color: #2b2b2b; border: 1px solid #444;
    }
    
    /* ============== 核心：右侧期权表格样式 ============== */
    .opt-container {
        background-color: #181b21;
        border-radius: 12px;
        border: 1px solid #333;
        border-left: 3px solid #3498db;
        font-family: 'Segoe UI', sans-serif;
        overflow: hidden;
    }
    
    /* 标题区 */
    .opt-header-box {
        padding: 15px;
        border-bottom: 1px solid #333;
    }
    .opt-title { font-size: 18px; font-weight: bold; color: #fff; margin: 0; }
    .opt-sub { font-size: 12px; color: #888; margin-top: 5px; }
    
    /* 表头 */
    .opt-table-header {
        display: flex;
        background-color: #1e2126;
        color: #888;
        font-size: 12px;
        padding: 8px 10px;
        border-bottom: 1px solid #333;
    }
    
    /* 数据行 */
    .opt-row {
        display: flex;
        align-items: center;
        padding: 12px 10px;
        border-bottom: 1px solid #2b2b2b;
        transition: background 0.1s;
    }
    .opt-row:last-child { border-bottom: none; }
    .opt-row:hover { background-color: #262a33; }
    
    /* 列宽布局 */
    .col-period { width: 15%; }
    .col-price  { width: 25%; }
    .col-dist   { width: 20%; text-align: right; }
    .col-ratio  { width: 25%; text-align: right; }
    .col-iv     { width: 15%; text-align: right; color: #666; font-size: 11px;}
    
    /* 文本样式 */
    .text-main { font-size: 14px; font-weight: bold; color: #fff; margin-bottom: 2px; }
    .text-sub  { font-size: 11px; color: #666; }
    
    /* 颜色类 */
    .dist-active { color: #00b894; font-weight: bold; }
    .dist-gray   { color: #666; }
    
    .tag-ratio {
        display: inline-block; padding: 3px 8px; border-radius: 4px; 
        font-size: 12px; font-weight: bold;
    }
    .tag-red    { background: rgba(231, 76, 60, 0.2); color: #e74c3c; }
    .tag-green  { background: rgba(0, 184, 148, 0.2); color: #00b894; }
    .tag-yellow { background: rgba(241, 196, 15, 0.2); color: #f1c40f; }

</style>
""", unsafe_allow_html=True)

# --- 3. 数据处理函数 ---
@st.cache_data(ttl=3600)
def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="2y")
        if df.empty: return None

        dates = df.index.strftime('%Y-%m-%d').tolist()
        kline_data = df[['Open', 'Close', 'Low', 'High']].values.tolist()

        global_min = df['Low'].min() * 0.95
        global_max = df['High'].max() * 1.05
        
        df['bin'] = pd.cut(df['Close'], bins=80)
        profile = df.groupby('bin', observed=False)['Volume'].sum()
        chip_prices = [str(round(b.mid, 2)) for b in profile.index]
        chip_volumes = [int(v) for v in profile.values]
        current_price = round(df['Close'].iloc[-1], 2)
        
        return {
            "dates": dates, "kline": kline_data, 
            "chip_prices": chip_prices, "chip_volumes": chip_volumes, 
            "current_price": current_price, "min_axis": global_min, "max_axis": global_max
        }
    except: return None

def get_option_chain_data(stock, current_price, target_strike):
    if not stock: return []
    try:
        expirations = stock.options
        if not expirations: return []
        
        # --- 更新：增加了您指定的所有月份 ---
        periods = [
            {"label": "1周", "days": 7},
            {"label": "2周", "days": 14},
            {"label": "1月", "days": 30},
            {"label": "2月", "days": 60},  # New
            {"label": "3月", "days": 90},
            {"label": "4月", "days": 120}, # New
            {"label": "5月", "days": 150}, # New
            {"label": "6月", "days": 180},
            {"label": "7月", "days": 210}, # New
            {"label": "8月", "days": 240}, # New
            {"label": "9月", "days": 270}, # New
            {"label": "10月", "days": 300},# New
            {"label": "11月", "days": 330},# New
            {"label": "1年", "days": 365}
        ]
        
        results = []
        now = datetime.now()
        exp_dates = []
        for date_str in expirations:
            d = datetime.strptime(date_str, "%Y-%m-%d")
            diff = (d - now).days
            if diff > 0: exp_dates.append({"date_str": date_str, "diff": diff})

        if not exp_dates: return []

        for p in periods:
            target_days = p["days"]
            # 寻找时间差最小的日期
            closest = min(exp_dates, key=lambda x: abs(x["diff"] - target_days))
            
            # 简单的去重逻辑：如果这个到期日已经被上一个周期选过了，且时间差比较大，可以考虑跳过
            # 但为了展示完整性，这里允许重复（例如4月和5月可能都匹配到同一个远期合约）
            
            try:
                opt = stock.option_chain(closest["date_str"])
                calls = opt.calls
                calls['abs_diff'] = abs(calls['strike'] - float(target_strike))
                row = calls.loc[calls['abs_diff'].idxmin()]
                
                results.append({
                    "period": p['label'],
                    "date": closest["date_str"],
                    "price": row['lastPrice'],
                    "strike": row['strike'],
                    "diff_pct": ((row['strike'] / current_price) - 1) * 100,
                    "ratio": (row['lastPrice'] / current_price) * 100,
                    "iv": row['impliedVolatility'] * 100
                })
            except: pass
        
        # 可选：如果需要对结果按天数排序或去重，可以在这里处理
        return results
    except: return []

# --- 4. HTML 生成器 ---
def generate_html_table(data_list, target_price):
    if not data_list:
        return "<div style='padding:20px; text-align:center; color:#666;'>暂无数据</div>"

    rows_html = ""
    for item in data_list:
        # 颜色逻辑
        ratio_cls = "tag-yellow"
        if item['ratio'] < 5: ratio_cls = "tag-green"
        if item['ratio'] > 15: ratio_cls = "tag-red"
        
        dist_cls = "dist-active" if item['diff_pct'] > 0 else "dist-gray"
        
        rows_html += f"""
<div class="opt-row">
<div class="col-period">
<div class="text-main">{item['period']}</div>
<div class="text-sub">{item['date']}</div>
</div>
<div class="col-price">
<div class="text-main">${item['price']:.2f}</div>
<div class="text-sub">Strike: {item['strike']}</div>
</div>
<div class="col-dist {dist_cls}" style="font-weight:bold; font-size:13px;">
{item['diff_pct']:+.2f}%
</div>
<div class="col-ratio">
<span class="tag-ratio {ratio_cls}">{item['ratio']:.2f}%</span>
</div>
<div class="col-iv">
{item['iv']:.1f}%
</div>
</div>"""

    full_html = f"""
<div class="opt-container">
<div class="opt-header-box">
<h3 class="opt-title">Call 期权链分析</h3>
<div class="opt-sub">目标行权价: ${target_price}</div>
</div>
<div class="opt-table-header">
<div class="col-period">周期</div>
<div class="col-price">Call价格</div>
<div class="col-dist">距现价</div>
<div class="col-ratio">成本比</div>
<div class="col-iv">IV</div>
</div>
<div class="opt-body">
{rows_html}
</div>
</div>
"""
    return full_html

# --- 5. 主逻辑 ---
with st.sidebar:
    st.markdown("### 🛠 参数设置")
    ticker = st.text_input("股票代码", value="TSLA").upper()
    target_price = st.number_input("目标行权价", value=530.0, step=0.5)
    run_btn = st.button("开始分析", type="primary")

if run_btn or ticker:
    with st.spinner('🚀 正在拉取数据...'):
        chip_data = get_stock_data(ticker)
        stock_obj = yf.Ticker(ticker)
        
    if chip_data:
        col_chart, col_table = st.columns([3, 1.2])
        
        with col_chart:
            bar_data = []
            cp = chip_data['current_price']
            for p_str, vol in zip(chip_data['chip_prices'], chip_data['chip_volumes']):
                color = '#e74c3c' if float(p_str) < cp else '#00b894'
                bar_data.append({"value": vol, "itemStyle": {"color": color}})

            options = {
                "backgroundColor": "#181b21",
                "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross"}, "backgroundColor":"rgba(0,0,0,0.8)"},
                "grid": [
                    {"left": "2%", "right": "35%", "top": "10%", "bottom": "10%"},
                    {"left": "66%", "right": "2%", "top": "10%", "bottom": "10%"}
                ],
                "xAxis": [
                    {"type": "category", "data": chip_data['dates'], "gridIndex": 0, "axisLine": {"lineStyle": {"color": "#555"}}},
                    {"type": "value", "gridIndex": 1, "splitLine": {"show": False}, "axisLabel": {"show": False}}
                ],
                "yAxis": [
                    {
                        "type": "value", "gridIndex": 0, "position": "right", 
                        "scale": True, "min": chip_data['min_axis'], "max": chip_data['max_axis'],
                        "splitLine": {"lineStyle": {"color": "#333"}}, "axisLabel": {"color": "#ccc", "margin": 10}
                    },
                    {"type": "category", "gridIndex": 1, "data": chip_data['chip_prices'], "show": False}
                ],
                "dataZoom": [{"type": "inside", "xAxisIndex": 0, "start": 60, "end": 100}],
                "series": [
                    {
                        "name": "股价", "type": "candlestick", "data": chip_data['kline'], 
                        "itemStyle": {"color": "#00b894", "color0": "#e74c3c", "borderColor": "#00b894", "borderColor0": "#e74c3c"},
                        "markLine": {
                            "symbol": "none", "silent": True,
                            "data": [
                                {"yAxis": target_price, "label": {"formatter": f"Target: {target_price}", "position": "end", "color": "#f1c40f"}, "lineStyle": {"color": "#f1c40f", "type": "dashed"}},
                                {"yAxis": chip_data['current_price'], "label": {"formatter": f"Current: {chip_data['current_price']}", "position": "end", "color": "#fff"}, "lineStyle": {"color": "#fff", "type": "dashed"}}
                            ]
                        }
                    },
                    {"name": "筹码", "type": "bar", "xAxisIndex": 1, "yAxisIndex": 1, "data": bar_data, "barWidth": "60%", "itemStyle": {"opacity": 0.6}}
                ]
            }
            st_echarts(options=options, height="600px")

        with col_table:
            # 获取数据
            opt_data = get_option_chain_data(stock_obj, chip_data['current_price'], target_price)
            # 生成 HTML
            html_code = generate_html_table(opt_data, target_price)
            # 渲染
            st.markdown(html_code, unsafe_allow_html=True)

    else:
        st.error("无法获取数据")
