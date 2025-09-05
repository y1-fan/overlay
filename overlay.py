import dash
from dash import dcc, html, Input, Output, State, ALL
import pandas as pd
import plotly.graph_objs as go
import os
import uuid
import subprocess
import sys
import tempfile
import json

# --- App Initialization ---
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "基金组合回测"

# --- Modern UI Styles ---
COLORS = {
    'primary': '#2E86C1',      # 主要蓝色
    'secondary': '#5DADE2',    # 次要蓝色
    'success': '#58D68D',      # 成功绿色
    'danger': '#EC7063',       # 危险红色
    'warning': '#F7DC6F',      # 警告黄色
    'light': '#F8F9FA',        # 浅色背景
    'dark': '#2C3E50',         # 深色文字
    'white': '#FFFFFF',        # 白色
    'border': '#E5E8E8',       # 边框色
    'shadow': 'rgba(0,0,0,0.1)' # 阴影色
}

BUTTON_STYLE = {
    'borderRadius': '8px',
    'border': 'none',
    'padding': '10px 20px',
    'fontWeight': '600',
    'fontSize': '14px',
    'cursor': 'pointer',
    'transition': 'all 0.3s ease',
    'boxShadow': f'0 2px 4px {COLORS["shadow"]}',
    'fontFamily': '"Segoe UI", Tahoma, Geneva, Verdana, sans-serif'
}

PRIMARY_BUTTON_STYLE = {
    **BUTTON_STYLE,
    'backgroundColor': COLORS['primary'],
    'color': COLORS['white']
}

DANGER_BUTTON_STYLE = {
    **BUTTON_STYLE,
    'backgroundColor': COLORS['danger'],
    'color': COLORS['white'],
    'padding': '6px 12px',
    'fontSize': '12px'
}

INPUT_STYLE = {
    'borderRadius': '6px',
    'border': f'2px solid {COLORS["border"]}',
    'padding': '8px 12px',
    'fontSize': '15px',
    'fontFamily': '"Segoe UI", Tahoma, Geneva, Verdana, sans-serif',
    'transition': 'border-color 0.3s ease',
    'outline': 'none',
    'height': '38px',
    'boxSizing': 'border-box'
}

DROPDOWN_STYLE = {
    'fontSize': '16px',
    'fontFamily': '"Segoe UI", Tahoma, Geneva, Verdana, sans-serif'
}

CARD_STYLE = {
    'backgroundColor': COLORS['white'],
    'borderRadius': '12px',
    'padding': '24px',
    'marginBottom': '20px',
    'boxShadow': f'0 4px 12px {COLORS["shadow"]}',
    'border': f'1px solid {COLORS["border"]}',
    'transition': 'transform 0.2s ease, box-shadow 0.2s ease'
}

# --- Helper Functions ---
def get_available_data_files():
    """Scans the directory for available data files (CSV)."""
    try:
        return [f for f in os.listdir('.') if f.endswith('.csv')]
    except FileNotFoundError:
        return []

def execute_custom_script(script_name, fund_code):
    """
    执行自定义脚本获取基金数据
    :param script_name: 脚本名称（不含扩展名）
    :param fund_code: 基金代码
    :return: DataFrame 或 None
    """
    try:
        # 构建脚本路径
        script_path = f"{script_name}.py"
        if not os.path.exists(script_path):
            print(f"脚本文件 {script_path} 不存在")
            return None
        

        # 执行脚本，优先用 utf-8，失败时自动回退 gbk
        cmd = [sys.executable, script_path, str(fund_code)]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, encoding='utf-8')
        except UnicodeDecodeError:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, encoding='gbk')

        if result.returncode == 0:
            # 解析CSV数据
            from io import StringIO
            csv_data = result.stdout.strip()
            if csv_data:
                try:
                    df = pd.read_csv(StringIO(csv_data))
                    print(f"脚本 {script_name} 执行成功，获得 {len(df)} 条数据")
                    return df
                except Exception as e:
                    print(f"CSV解析失败: {e}")
                    return None
            else:
                print(f"脚本 {script_name} 返回空数据")
                return None
        else:
            print(f"脚本执行失败: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        print(f"脚本 {script_name} 执行超时")
        return None
    except Exception as e:
        print(f"执行脚本时出错: {e}")
        return None

def get_available_scripts():
    """获取可用的自定义脚本"""
    try:
        scripts = []
        for f in os.listdir('.'):
            if f.endswith('.py') and f != 'overlay.py' and f != '__pycache__':
                # 去掉扩展名
                script_name = f[:-3]
                scripts.append(script_name)
        return scripts
    except FileNotFoundError:
        return []

def save_fund_data_individually(portfolios):
    """
    按条目分开保存基金数据到本地CSV文件，便于后续重新组合
    :param portfolios: 组合数据字典
    :return: 保存状态信息
    """
    saved_files = []
    errors = []
    
    # 按条目遍历所有基金数据
    for p_id, p_data in portfolios.items():
        portfolio_name = p_data.get('name', f'组合_{p_id[:8]}')
        
        for fund_id, fund_data in p_data['funds'].items():
            fund_name = fund_data.get('fund-name', f'基金_{fund_id[:8]}')
            data_source = fund_data.get('fund-data')
            fund_code = fund_data.get('fund-code')
            fund_share = fund_data.get('fund-share', 0)
            
            if not data_source:
                continue
                
            df = None
            source_info = ""
            
            try:
                # 处理脚本数据源
                if data_source.startswith('script:'):
                    script_name = data_source[7:]
                    if fund_code:
                        print(f"正在获取数据：{fund_name} ({fund_code})")
                        df = execute_custom_script(script_name, fund_code)
                        source_info = f"{script_name}_{fund_code}"
                    else:
                        continue
                        
                # 处理CSV文件数据源
                elif os.path.exists(data_source):
                    print(f"正在复制数据：{fund_name} (来源: {data_source})")
                    df = pd.read_csv(data_source)
                    source_info = f"文件_{os.path.splitext(os.path.basename(data_source))[0]}"
                
                if df is not None and not df.empty:
                    # 生成更清晰的文件名，不包含组合信息
                    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
                    safe_fund_name = "".join(c for c in fund_name if c.isalnum() or c in (' ', '-', '_')).strip()
                    
                    # 新的命名方式：基金数据_[基金名称]_[数据源]_[时间戳]
                    if fund_code:
                        filename = f"基金数据_{safe_fund_name}_{fund_code}_{timestamp}.csv"
                    else:
                        filename = f"基金数据_{safe_fund_name}_{source_info}_{timestamp}.csv"
                    
                    # 确保数据格式标准化
                    if 'time' in df.columns:
                        # 已经是标准格式
                        standardized_df = df.copy()
                    elif 'FSRQ' in df.columns and 'DWJZ' in df.columns:
                        # 转换为标准格式
                        standardized_df = df.rename(columns={'FSRQ': 'time', 'DWJZ': 'nav'})
                        standardized_df = standardized_df[['time', 'nav']]
                    else:
                        # 尝试猜测列名
                        time_col = next((col for col in df.columns if 'time' in col.lower() or 'date' in col.lower()), None)
                        value_col = next((col for col in df.columns if col != time_col and df[col].dtype in ['float64', 'int64']), None)
                        if time_col and value_col:
                            standardized_df = df[[time_col, value_col]].copy()
                            standardized_df.columns = ['time', 'nav']
                        else:
                            standardized_df = df.copy()
                    
                    # 保存文件
                    standardized_df.to_csv(filename, index=False, encoding='utf-8-sig')
                    
                    saved_files.append({
                        'filename': filename,
                        'fund_name': fund_name,
                        'fund_code': fund_code or 'N/A',
                        'source': source_info,
                        'share': fund_share,
                        'from_portfolio': portfolio_name,
                        'rows': len(standardized_df)
                    })
                    
            except Exception as e:
                errors.append(f"{fund_name} ({fund_code or 'N/A'}): {str(e)}")
    
    return saved_files, errors

def align_time_series_data(fund_dfs, portfolio_name):
    """
    统一组合中所有基金的时间区间，以最晚开始时间为准
    :param fund_dfs: 基金数据列表
    :param portfolio_name: 组合名称
    :return: 对齐后的基金数据列表和时间统计信息
    """
    if not fund_dfs:
        return fund_dfs, None
    
    # 收集所有基金的时间范围信息
    time_info = []
    for fund in fund_dfs:
        df = fund['df']
        if not df.empty:
            start_time = df.index.min()
            end_time = df.index.max()
            fund_id = df.columns[0]
            time_info.append({
                'fund_id': fund_id,
                'start_time': start_time,
                'end_time': end_time,
                'data_points': len(df)
            })
    
    if not time_info:
        return fund_dfs, None
    
    # 找到最晚的开始时间
    latest_start = max(info['start_time'] for info in time_info)
    earliest_end = min(info['end_time'] for info in time_info)
    
    # 检查是否需要对齐
    needs_alignment = any(info['start_time'] < latest_start for info in time_info)
    
    if needs_alignment:
        try:
            print(f"组合 '{portfolio_name}' 检测到时间不统一，正在对齐到最晚开始时间: {latest_start.strftime('%Y-%m-%d')}")
        except Exception:
            pass
        
        # 对齐所有基金数据到统一时间区间
        aligned_fund_dfs = []
        for fund in fund_dfs:
            df = fund['df']
            if not df.empty:
                # 截取到统一的时间区间
                aligned_df = df[df.index >= latest_start]
                if not aligned_df.empty:
                    # 重新归一化（基于新的起始点）
                    fund_id = aligned_df.columns[0]
                    first_value = aligned_df[fund_id].iloc[0]
                    if first_value != 0:
                        aligned_df[fund_id] = aligned_df[fund_id] / first_value
                    
                    aligned_fund_dfs.append({
                        'df': aligned_df,
                        'share': fund['share']
                    })
                    
                    original_points = len(df)
                    aligned_points = len(aligned_df)
                    try:
                        print(f"{fund_id}: {original_points} -> {aligned_points} 个数据点")
                    except Exception:
                        pass
        
        time_stats = {
            'aligned': True,
            'latest_start': latest_start,
            'earliest_end': earliest_end,
            'original_count': len(fund_dfs),
            'aligned_count': len(aligned_fund_dfs)
        }
        
        return aligned_fund_dfs, time_stats
    else:
        try:
            print(f"组合 '{portfolio_name}' 时间区间已统一，无需对齐")
        except Exception:
            pass
        time_stats = {
            'aligned': False,
            'latest_start': latest_start,
            'earliest_end': earliest_end,
            'original_count': len(fund_dfs),
            'aligned_count': len(fund_dfs)
        }
        return fund_dfs, time_stats

def calculate_investment_metrics(nav_series, portfolio_name):
    """
    计算投资组合的关键指标
    :param nav_series: 净值序列 (pandas Series)
    :param portfolio_name: 组合名称
    :return: 投资指标字典
    """
    try:
        print(f"开始计算 {portfolio_name} 的投资指标")
    except Exception:
        pass
    
    if nav_series.empty or len(nav_series) < 2:
        try:
            print(f"{portfolio_name}: 数据不足，需要至少2个数据点")
        except Exception:
            pass
        return None
    
    # 检查是否有NaN值
    if nav_series.isnull().any():
        try:
            print(f"{portfolio_name}: 发现NaN值，进行清理")
        except Exception:
            pass
        nav_series = nav_series.dropna()
        if len(nav_series) < 2:
            try:
                print(f"{portfolio_name}: 清理NaN后数据不足")
            except Exception:
                pass
            return None
    
    # 计算日收益率
    returns = nav_series.pct_change().dropna()
    
    if returns.empty:
        try:
            print(f"{portfolio_name}: 无法计算收益率")
        except Exception:
            pass
        return None
    
    try:
        print(f"{portfolio_name}: 数据点={len(nav_series)}, 收益率点={len(returns)}")
    except Exception:
        pass
    
    # 时间范围
    start_date = nav_series.index[0]
    end_date = nav_series.index[-1]
    days = (end_date - start_date).days
    years = days / 365.25
    
    # 基础指标
    total_return = (nav_series.iloc[-1] / nav_series.iloc[0] - 1) * 100
    
    # 年化收益率
    if years > 0:
        annualized_return = ((nav_series.iloc[-1] / nav_series.iloc[0]) ** (1/years) - 1) * 100
    else:
        annualized_return = 0
    
    # 波动率 (年化)
    volatility = returns.std() * (252 ** 0.5) * 100  # 假设252个交易日/年
    
    # 最大回撤
    cumulative = nav_series / nav_series.cummax()
    max_drawdown = (cumulative.min() - 1) * 100
    
    # 夏普比率 (假设无风险利率为3%)
    risk_free_rate = 0.03
    if volatility > 0:
        sharpe_ratio = (annualized_return / 100 - risk_free_rate) / (volatility / 100)
        try:
            print(sharpe_ratio)
        except Exception:
            pass
    else:
        sharpe_ratio = 0
    
    # Calmar比率 (年化收益率 / 最大回撤绝对值)
    if max_drawdown < 0:
        calmar_ratio = (annualized_return / 100) / abs(max_drawdown / 100)
    else:
        calmar_ratio = 0
    
    # 胜率 (正收益交易日占比)
    win_rate = (returns > 0).sum() / len(returns) * 100
    
    # 最大连续下跌天数
    nav_changes = nav_series.diff()
    consecutive_down = 0
    max_consecutive_down = 0
    for change in nav_changes:
        if pd.isna(change):
            continue
        if change < 0:
            consecutive_down += 1
            max_consecutive_down = max(max_consecutive_down, consecutive_down)
        else:
            consecutive_down = 0
    
    # VAR (95%置信度的在险价值)
    var_95 = returns.quantile(0.05) * 100
    
    metrics = {
        'portfolio_name': portfolio_name,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'days': days,
        'total_return': round(total_return, 2),
        'annualized_return': round(annualized_return, 2),
        'volatility': round(volatility, 2),
        'max_drawdown': round(max_drawdown, 2),
        'sharpe_ratio': round(sharpe_ratio, 3),
        'calmar_ratio': round(calmar_ratio, 3),
        'win_rate': round(win_rate, 2),
        'max_consecutive_down': max_consecutive_down,
        'var_95': round(var_95, 2),
        'final_nav': round(nav_series.iloc[-1], 4)
    }
    
    try:
        print(f"{portfolio_name}: 计算完成，总收益={total_return:.2f}%, 年化收益={annualized_return:.2f}%")
    except Exception:
        pass
    return metrics

def create_analytics_table(metrics_list):
    """
    创建投资分析数据表
    :param metrics_list: 投资指标列表
    :return: HTML表格组件
    """
    try:
        print(f"create_analytics_table 接收到 {len(metrics_list) if metrics_list else 0} 个指标数据")
    except Exception:
        pass
    
    if not metrics_list:
        try:
            print("metrics_list 为空，返回暂无数据提示")
        except Exception:
            pass
        return html.Div("暂无数据", style={'textAlign': 'center', 'color': COLORS['secondary']})
    
    # 详细打印每个指标数据
    for i, metrics in enumerate(metrics_list):
        try:
            print(f"指标数据 {i+1}: 组合名={metrics.get('portfolio_name', 'N/A')}, 总收益={metrics.get('total_return', 'N/A')}%")
        except Exception:
            pass
    
    # 表头
    header = html.Thead([
        html.Tr([
            html.Th("组合名称", style={'padding': '12px', 'backgroundColor': COLORS['primary'], 'color': 'white', 'border': 'none', 'textAlign': 'center'}),
            html.Th("期间", style={'padding': '12px', 'backgroundColor': COLORS['primary'], 'color': 'white', 'border': 'none', 'textAlign': 'center'}),
            html.Th("总收益率", style={'padding': '12px', 'backgroundColor': COLORS['primary'], 'color': 'white', 'border': 'none', 'textAlign': 'center'}),
            html.Th("年化收益率", style={'padding': '12px', 'backgroundColor': COLORS['primary'], 'color': 'white', 'border': 'none', 'textAlign': 'center'}),
            html.Th("年化波动率", style={'padding': '12px', 'backgroundColor': COLORS['primary'], 'color': 'white', 'border': 'none', 'textAlign': 'center'}),
            html.Th("最大回撤", style={'padding': '12px', 'backgroundColor': COLORS['primary'], 'color': 'white', 'border': 'none', 'textAlign': 'center'}),
            html.Th("夏普比率", style={'padding': '12px', 'backgroundColor': COLORS['primary'], 'color': 'white', 'border': 'none', 'textAlign': 'center'}),
            html.Th("Calmar比率", style={'padding': '12px', 'backgroundColor': COLORS['primary'], 'color': 'white', 'border': 'none', 'textAlign': 'center'}),
            html.Th("胜率", style={'padding': '12px', 'backgroundColor': COLORS['primary'], 'color': 'white', 'border': 'none', 'textAlign': 'center'}),
            html.Th("VaR(95%)", style={'padding': '12px', 'backgroundColor': COLORS['primary'], 'color': 'white', 'border': 'none', 'textAlign': 'center'})
        ])
    ])
    
    # 表格行
    rows = []
    for i, metrics in enumerate(metrics_list):
        # 根据指标好坏设置颜色
        return_color = COLORS['success'] if metrics['total_return'] > 0 else COLORS['danger']
        sharpe_color = COLORS['success'] if metrics['sharpe_ratio'] > 1 else (COLORS['warning'] if metrics['sharpe_ratio'] > 0.5 else COLORS['danger'])
        drawdown_color = COLORS['success'] if metrics['max_drawdown'] > -10 else (COLORS['warning'] if metrics['max_drawdown'] > -20 else COLORS['danger'])

        row_style = {'backgroundColor': COLORS['light'] if i % 2 == 0 else COLORS['white'], 'textAlign': 'center'}

        row = html.Tr([
            html.Td(metrics['portfolio_name'], style={'padding': '10px', 'fontWeight': '600', **row_style}),
            html.Td(f"{metrics['start_date']} 至 {metrics['end_date']} ({metrics['days']}天)", 
                style={'padding': '10px', 'fontSize': '12px', **row_style}),
            html.Td(f"{metrics['total_return']:+.2f}%", 
                style={'padding': '10px', 'color': return_color, 'fontWeight': '600', **row_style}),
            html.Td(f"{metrics['annualized_return']:+.2f}%", 
                style={'padding': '10px', 'color': return_color, 'fontWeight': '600', **row_style}),
            html.Td(f"{metrics['volatility']:.2f}%", 
                style={'padding': '10px', **row_style}),
            html.Td(f"{metrics['max_drawdown']:.2f}%", 
                style={'padding': '10px', 'color': drawdown_color, 'fontWeight': '600', **row_style}),
            html.Td(f"{metrics['sharpe_ratio']:.3f}", 
                style={'padding': '10px', 'color': sharpe_color, 'fontWeight': '600', **row_style}),
            html.Td(f"{metrics['calmar_ratio']:.3f}", 
                style={'padding': '10px', **row_style}),
            html.Td(f"{metrics['win_rate']:.1f}%", 
                style={'padding': '10px', **row_style}),
            html.Td(f"{metrics['var_95']:.2f}%", 
                style={'padding': '10px', **row_style})
        ])
        rows.append(row)
    
    table = html.Table([header, html.Tbody(rows)], style={
        'width': '100%',
        'borderCollapse': 'collapse',
        'boxShadow': f'0 2px 8px {COLORS["shadow"]}',
        'borderRadius': '8px',
        'overflow': 'hidden'
    })
    
    # 添加指标说明
    legend = html.Div([
        html.H4("📊 指标说明", style={'color': COLORS['dark'], 'marginTop': '20px', 'marginBottom': '10px'}),
        html.Ul([
            html.Li("夏普比率：>1优秀，0.5-1良好，<0.5需改进", style={'margin': '5px 0'}),
            html.Li("最大回撤：<-10%警戒，<-20%高风险", style={'margin': '5px 0'}),
            html.Li("Calmar比率：年化收益率与最大回撤比值，越高越好", style={'margin': '5px 0'}),
            html.Li("VaR(95%)：95%置信度下的最大可能单日损失", style={'margin': '5px 0'})
        ], style={'fontSize': '12px', 'color': COLORS['secondary'], 'paddingLeft': '20px'})
    ])
    
    try:
        print(f"create_analytics_table 返回完整表格组件，包含 {len(metrics_list)} 个组合的数据")
    except Exception:
        pass
    return html.Div([table, legend])

# --- App Layout ---
# Create initial base portfolio that cannot be deleted
initial_portfolio_id = 'base-portfolio'
initial_fund_id = str(uuid.uuid4())

app.layout = html.Div([
    # --- Header Section ---
    html.Div([
        html.H1("📊 基金组合回测工具", style={
            'textAlign': 'center',
            'color': COLORS['dark'],
            'marginBottom': '10px',
            'fontSize': '2.5rem',
            'fontWeight': '700',
            'fontFamily': '"Segoe UI", Tahoma, Geneva, Verdana, sans-serif'
        }),
        html.P("智能化投资组合分析与回测平台", style={
            'textAlign': 'center',
            'color': COLORS['secondary'],
            'fontSize': '1.1rem',
            'marginBottom': '30px',
            'fontFamily': '"Segoe UI", Tahoma, Geneva, Verdana, sans-serif'
        })
    ], style={
        'background': f'linear-gradient(135deg, {COLORS["light"]} 0%, {COLORS["white"]} 100%)',
        'padding': '40px 20px',
        'marginBottom': '30px',
        'borderRadius': '0 0 20px 20px',
        'boxShadow': f'0 4px 20px {COLORS["shadow"]}'
    }),

    # --- Controls Section ---
    html.Div([
        html.Button('➕ 添加新组合', 
                   id='add-portfolio-btn', 
                   n_clicks=0, 
                   style={**PRIMARY_BUTTON_STYLE, 'marginBottom': '20px'})
    ], style={
        'textAlign': 'center',
        'marginBottom': '30px'
    }),

    # --- Portfolios Container ---
    html.Div(id='portfolios-container', children=[
        # Initial base portfolio
        html.Div([
            html.Div([
                html.Div([
                    html.Span("🏛️", style={'fontSize': '1.5rem', 'marginRight': '10px'}),
                    dcc.Input(
                        id={'type': 'portfolio-name', 'portfolio_id': initial_portfolio_id},
                        value='基础组合',
                        placeholder='组合名称',
                        style={
                            **INPUT_STYLE,
                            'width': '250px',
                            'fontWeight': '600',
                            'fontSize': '16px',
                            'border': f'2px solid {COLORS["primary"]}'
                        }
                    ),
                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '20px'}),
            ]),
            html.Div([], id={'type': 'funds-container', 'portfolio_id': initial_portfolio_id}),
            html.Button('➕ 添加基金', 
                       id={'type': 'add-fund-btn', 'portfolio_id': initial_portfolio_id}, 
                       n_clicks=0, 
                       style={**PRIMARY_BUTTON_STYLE, 'marginTop': '15px'}),
            html.Div(id={'type': 'share-feedback', 'portfolio_id': initial_portfolio_id}, 
                    style={
                        'color': COLORS['danger'], 
                        'marginTop': '10px', 
                        'fontWeight': '600',
                        'fontSize': '14px',
                        'textAlign': 'center',
                        'padding': '8px',
                        'borderRadius': '6px',
                        'backgroundColor': f'{COLORS["light"]}'
                    })
        ], id={'type': 'portfolio-card', 'portfolio_id': initial_portfolio_id}, 
           style=CARD_STYLE)
    ], style={'maxWidth': '1200px', 'margin': '0 auto', 'padding': '0 20px'}),

    # --- Chart Section ---
    html.Div([
        html.H2("📈 组合回测净值曲线", style={
            'textAlign': 'center',
            'color': COLORS['dark'],
            'marginBottom': '20px',
            'fontSize': '1.8rem',
            'fontWeight': '600',
            'fontFamily': '"Segoe UI", Tahoma, Geneva, Verdana, sans-serif'
        }),
        html.Div([
            html.Button(
                '⏳ 生成图表',
                id='generate-chart-btn',
                n_clicks=0,
                style={**PRIMARY_BUTTON_STYLE, 'marginBottom': '20px', 'marginRight': '15px'}
            ),
            html.Button(
                '💾 保存当前数据',
                id='save-data-btn',
                n_clicks=0,
                style={
                    **BUTTON_STYLE,
                    'backgroundColor': COLORS['success'],
                    'color': COLORS['white'],
                    'marginBottom': '20px',
                    'marginRight': '15px'
                }
            ),
            html.Button(
                '📊 智能归一化',
                id='normalize-chart-btn',
                n_clicks=0,
                style={
                    **BUTTON_STYLE,
                    'backgroundColor': COLORS['warning'],
                    'color': COLORS['dark'],
                    'marginBottom': '20px'
                },
                title='以最晚开始的组合时间为基准，重新归一化所有组合净值'
            )
        ], style={'textAlign': 'center'}),
        html.Div(
            id='save-status',
            style={
                'textAlign': 'center',
                'marginBottom': '20px',
                'fontSize': '14px',
                'fontWeight': '600'
            }
        ),
        html.Div(
            id='graph-container',
            children=[],
            style={
                'display': 'none',
                'maxWidth': '1300px',
                'margin': '0 auto',
                'backgroundColor': COLORS['white'],
                'borderRadius': '16px',
                'boxShadow': f'0 4px 16px {COLORS["shadow"]}',
                'padding': '32px 24px 24px 24px',
            }
        ),
        
        # --- Investment Analytics Section ---
        html.Div(
            id='analytics-section',
            children=[],
            style={
                **CARD_STYLE,
                'maxWidth': '1200px',
                'margin': '32px auto 0 auto',
                'marginLeft': 'auto',
                'marginRight': 'auto',
                'display': 'none',
                'backgroundColor': COLORS['light'],
                'boxShadow': f'0 2px 8px {COLORS["shadow"]}',
                'padding': '28px 18px 18px 18px',
            }
        ),
    ], style={
        **CARD_STYLE,
        'maxWidth': '1200px',
        'margin': '30px auto 0 auto',
        'marginLeft': 'auto',
        'marginRight': 'auto'
    }),

], style={
    'fontFamily': '"Segoe UI", Tahoma, Geneva, Verdana, sans-serif',
    'backgroundColor': f'{COLORS["light"]}',
    'minHeight': '100vh',
    'paddingBottom': '40px'
})


# --- UI Generation Functions ---
def create_fund_entry(portfolio_id, fund_id):
    """Creates the UI for a single fund entry."""
    available_files = get_available_data_files()
    available_scripts = get_available_scripts()
    
    data_source_options = (
        [{'label': f'📁 {f}', 'value': f} for f in available_files] +
        [{'label': f'🔧 脚本: {s}', 'value': f'script:{s}'} for s in available_scripts]
    )
    
    return html.Div([
        # 第一行：基金名称、份额、数据源
        html.Div([
            dcc.Input(
                id={'type': 'fund-name', 'portfolio_id': portfolio_id, 'fund_id': fund_id},
                placeholder='💼 条目名',
                style={
                    **INPUT_STYLE, 
                    'width': '180px', 
                    'marginRight': '8px'
                }
            ),
            dcc.Input(
                id={'type': 'fund-share', 'portfolio_id': portfolio_id, 'fund_id': fund_id},
                type='number',
                placeholder='📊 份额 (%)',
                min=0,
                max=100,
                step=0.01,
                style={
                    **INPUT_STYLE, 
                    'width': '150px', 
                    'marginRight': '8px'
                }
            ),
            html.Div([
                dcc.Dropdown(
                    id={'type': 'fund-data', 'portfolio_id': portfolio_id, 'fund_id': fund_id},
                    options=data_source_options,
                    placeholder='📂 选择数据源',
                    style={**DROPDOWN_STYLE, 'width': '100%'},
                    className='modern-dropdown'
                )
            ], style={
                'flex': '1', 
                'marginRight': '8px'
            }),
            html.Button('🗑️', 
                       id={'type': 'remove-fund-btn', 'portfolio_id': portfolio_id, 'fund_id': fund_id}, 
                       n_clicks=0, 
                       title="删除此基金",
                       style={
                           **DANGER_BUTTON_STYLE,
                           'width': '36px',
                           'height': '36px',
                           'borderRadius': '50%',
                           'display': 'flex',
                           'alignItems': 'center',
                           'justifyContent': 'center',
                           'fontSize': '14px',
                           'flexShrink': '0'
                       })
        ], style={
            'display': 'flex', 
            'alignItems': 'center', 
            'marginBottom': '8px'
        }),
        
        # 第二行：可选参数（仅在选择脚本时显示）
        html.Div([
            dcc.Input(
                id={'type': 'fund-code', 'portfolio_id': portfolio_id, 'fund_id': fund_id},
                placeholder='🔢 可选参数',
                style={
                    **INPUT_STYLE, 
                    'width': '200px',
                    'marginRight': '8px',
                    'display': 'none'  # 默认隐藏
                }
            ),
            html.Span(
                "填入基金代码或其他所需参数",
                style={
                    'fontSize': '12px',
                    'color': COLORS['secondary'],
                    'fontStyle': 'italic',
                    'display': 'none'  # 默认隐藏
                },
                id={'type': 'param-hint', 'portfolio_id': portfolio_id, 'fund_id': fund_id}
            ),
            html.Div(
                id={'type': 'script-status', 'portfolio_id': portfolio_id, 'fund_id': fund_id},
                style={'marginLeft': '10px', 'fontSize': '12px', 'color': COLORS['secondary']}
            )
        ], style={'display': 'flex', 'alignItems': 'center'}, 
           id={'type': 'fund-code-row', 'portfolio_id': portfolio_id, 'fund_id': fund_id})
        
    ], id=f"fund-entry-{fund_id}", style={
        'marginBottom': '10px',
        'padding': '12px',
        'backgroundColor': COLORS['white'],
        'borderRadius': '8px',
        'border': f'1px solid {COLORS["border"]}',
        'boxShadow': f'0 2px 4px {COLORS["shadow"]}',
        'transition': 'transform 0.2s ease'
    })

def create_portfolio_card(portfolio_id, n_clicks):
    """Creates the UI for a single portfolio card."""
    initial_fund_id = str(uuid.uuid4())
    
    return html.Div([
        html.Div([
            html.Div([
                html.Span("📈", style={'fontSize': '1.5rem', 'marginRight': '10px'}),
                dcc.Input(
                    id={'type': 'portfolio-name', 'portfolio_id': portfolio_id},
                    value=f'投资组合 {n_clicks}' if portfolio_id != 'base-portfolio' else '基础组合',
                    placeholder='组合名称',
                    style={
                        **INPUT_STYLE,
                        'width': '250px',
                        'fontWeight': '600',
                        'fontSize': '16px',
                        'marginRight': '15px',
                        'border': f'2px solid {COLORS["secondary"]}'
                    }
                ),
            ], style={'display': 'flex', 'alignItems': 'center', 'flex': '1'}),
            html.Button('🗑️ 删除组合', 
                       id={'type': 'remove-portfolio-btn', 'portfolio_id': portfolio_id}, 
                       n_clicks=0,
                       style={
                           **DANGER_BUTTON_STYLE,
                           'display': 'inline-flex',
                           'alignItems': 'center',
                           'gap': '5px'
                       })
        ], style={
            'display': 'flex', 
            'alignItems': 'center', 
            'justifyContent': 'space-between',
            'marginBottom': '20px',
            'paddingBottom': '15px',
            'borderBottom': f'2px solid {COLORS["border"]}'
        }),
        
        html.Div([
            html.H4('💰 基金配置', style={
                'color': COLORS['dark'],
                'marginBottom': '15px',
                'fontSize': '1.1rem',
                'fontWeight': '600'
            }),
            html.Div([create_fund_entry(portfolio_id, initial_fund_id)], 
                    id={'type': 'funds-container', 'portfolio_id': portfolio_id})
        ]),
        
        html.Div([
            html.Button('➕ 添加基金', 
                       id={'type': 'add-fund-btn', 'portfolio_id': portfolio_id}, 
                       n_clicks=0, 
                       style={**PRIMARY_BUTTON_STYLE, 'marginTop': '15px'}),
            html.Div(id={'type': 'share-feedback', 'portfolio_id': portfolio_id}, 
                    style={
                        'color': COLORS['danger'], 
                        'marginTop': '15px', 
                        'fontWeight': '600',
                        'fontSize': '14px',
                        'textAlign': 'center',
                        'padding': '8px',
                        'borderRadius': '6px',
                        'backgroundColor': f'{COLORS["light"]}'
                    })
        ], style={'textAlign': 'center'})
        
    ], id={'type': 'portfolio-card', 'portfolio_id': portfolio_id}, 
       style={
           **CARD_STYLE,
           'position': 'relative',
           'overflow': 'hidden'
       })


# --- Callbacks ---

# Callback to save current portfolio data to local CSV files
@app.callback(
    Output('save-status', 'children'),
    Output('save-status', 'style'),
    Input('save-data-btn', 'n_clicks'),
    State({'type': 'fund-name', 'portfolio_id': ALL, 'fund_id': ALL}, 'value'),
    State({'type': 'fund-share', 'portfolio_id': ALL, 'fund_id': ALL}, 'value'),
    State({'type': 'fund-data', 'portfolio_id': ALL, 'fund_id': ALL}, 'value'),
    State({'type': 'fund-code', 'portfolio_id': ALL, 'fund_id': ALL}, 'value'),
    State({'type': 'portfolio-name', 'portfolio_id': ALL}, 'value'),
    prevent_initial_call=True
)
def save_data_to_csv(n_clicks, fund_names, fund_shares, fund_datas, fund_codes, portfolio_names):
    """保存当前组合数据到本地CSV文件"""
    if n_clicks is None or n_clicks == 0:
        return "", {'display': 'none'}
    
    import dash
    ctx = dash.callback_context
    
    # Parse all inputs into a structured dictionary (same logic as generate chart)
    portfolios = {}
    portfolio_names_dict = {}
    
    # Get portfolio names
    if hasattr(ctx, "states_list") and len(ctx.states_list) > 4:
        for i, value in enumerate(portfolio_names):
            if value is not None and value != "":
                state_id = ctx.states_list[4][i]['id']
                portfolio_id = state_id['portfolio_id']
                portfolio_names_dict[portfolio_id] = value

    # Process fund inputs
    fund_inputs = [
        (fund_names, 0),
        (fund_shares, 1),
        (fund_datas, 2),
        (fund_codes, 3)
    ]
    
    for arr, state_idx in fund_inputs:
        if hasattr(ctx, "states_list") and len(ctx.states_list) > state_idx:
            for i, value in enumerate(arr):
                if value is None or value == "":
                    continue
                state_id = ctx.states_list[state_idx][i]['id']
                input_type = state_id['type']
                portfolio_id = state_id['portfolio_id']
                fund_id = state_id['fund_id']
                
                if portfolio_id not in portfolios:
                    portfolios[portfolio_id] = {
                        'funds': {},
                        'name': portfolio_names_dict.get(portfolio_id, f"组合 {len(portfolios) + 1}")
                    }
                if fund_id not in portfolios[portfolio_id]['funds']:
                    portfolios[portfolio_id]['funds'][fund_id] = {}
                portfolios[portfolio_id]['funds'][fund_id][input_type] = value
                if portfolio_id in portfolio_names_dict:
                    portfolios[portfolio_id]['name'] = portfolio_names_dict[portfolio_id]
    
    # Save data to CSV files (按条目分开保存)
    saved_files, errors = save_fund_data_individually(portfolios)
    
    # Prepare status message
    if saved_files:
        message_parts = ["✅ 基金数据按条目保存成功！"]
        message_parts.append(f"📁 已保存 {len(saved_files)} 个基金数据文件：")
        for file_info in saved_files:
            fund_info = f"{file_info['fund_name']} ({file_info['fund_code']})"
            if file_info['share']:
                fund_info += f" - 份额: {file_info['share']}%"
            message_parts.append(f"• {file_info['filename']}")
            message_parts.append(f"  └─ {fund_info} | {file_info['rows']} 行数据")
        
        if errors:
            message_parts.append("⚠️ 部分保存失败：")
            for error in errors:
                message_parts.append(f"• {error}")
        
        message = html.Div([
            html.P(part, style={'margin': '2px 0'}) for part in message_parts
        ])
        style = {
            'textAlign': 'center',
            'marginBottom': '20px',
            'fontSize': '14px',
            'fontWeight': '600',
            'color': COLORS['success'],
            'backgroundColor': f'{COLORS["light"]}',
            'padding': '15px',
            'borderRadius': '8px',
            'border': f'2px solid {COLORS["success"]}'
        }
    else:
        message = "❌ 没有可保存的数据或保存失败"
        style = {
            'textAlign': 'center',
            'marginBottom': '20px',
            'fontSize': '14px',
            'fontWeight': '600',
            'color': COLORS['danger'],
            'backgroundColor': f'{COLORS["light"]}',
            'padding': '15px',
            'borderRadius': '8px',
            'border': f'2px solid {COLORS["danger"]}'
        }
    
    return message, style

# Callback for intelligent normalization based on latest start time across all portfolios
@app.callback(
    Output('graph-container', 'children', allow_duplicate=True),
    Output('graph-container', 'style', allow_duplicate=True),
    Output('analytics-section', 'children', allow_duplicate=True),
    Output('analytics-section', 'style', allow_duplicate=True),
    Input('normalize-chart-btn', 'n_clicks'),
    State({'type': 'fund-name', 'portfolio_id': ALL, 'fund_id': ALL}, 'value'),
    State({'type': 'fund-share', 'portfolio_id': ALL, 'fund_id': ALL}, 'value'),
    State({'type': 'fund-data', 'portfolio_id': ALL, 'fund_id': ALL}, 'value'),
    State({'type': 'fund-code', 'portfolio_id': ALL, 'fund_id': ALL}, 'value'),
    State({'type': 'portfolio-name', 'portfolio_id': ALL}, 'value'),
    prevent_initial_call=True
)
def generate_normalized_chart(n_clicks, fund_names, fund_shares, fund_datas, fund_codes, portfolio_names):
    """智能归一化：以最晚开始的组合时间为基准，重新归一化所有组合净值"""
    if n_clicks is None or n_clicks == 0:
        return [], {'display': 'none'}, [], {'display': 'none'}
    
    import dash
    ctx = dash.callback_context
    
    # Parse all inputs into a structured dictionary (复用现有逻辑)
    portfolios = {}
    portfolio_names_dict = {}
    
    # Get portfolio names
    if hasattr(ctx, "states_list") and len(ctx.states_list) > 4:
        for i, value in enumerate(portfolio_names):
            if value is not None and value != "":
                state_id = ctx.states_list[4][i]['id']
                portfolio_id = state_id['portfolio_id']
                portfolio_names_dict[portfolio_id] = value

    # Process fund inputs
    fund_inputs = [
        (fund_names, 0),
        (fund_shares, 1),
        (fund_datas, 2),
        (fund_codes, 3)
    ]
    
    for arr, state_idx in fund_inputs:
        if hasattr(ctx, "states_list") and len(ctx.states_list) > state_idx:
            for i, value in enumerate(arr):
                if value is None or value == "":
                    continue
                state_id = ctx.states_list[state_idx][i]['id']
                input_type = state_id['type']
                portfolio_id = state_id['portfolio_id']
                fund_id = state_id['fund_id']
                
                if portfolio_id not in portfolios:
                    portfolios[portfolio_id] = {
                        'funds': {},
                        'name': portfolio_names_dict.get(portfolio_id, f"组合 {len(portfolios) + 1}")
                    }
                if fund_id not in portfolios[portfolio_id]['funds']:
                    portfolios[portfolio_id]['funds'][fund_id] = {}
                portfolios[portfolio_id]['funds'][fund_id][input_type] = value
                if portfolio_id in portfolio_names_dict:
                    portfolios[portfolio_id]['name'] = portfolio_names_dict[portfolio_id]

    # Process data for all portfolios and collect time ranges
    portfolio_data = []
    global_latest_start = None
    portfolio_nav_data = {}  # 存储净值数据用于分析
    
    for p_id, p_data in portfolios.items():
        portfolio_name = p_data.get('name')
        fund_dfs = []
        
        for fund_id, fund_data in p_data['funds'].items():
            share = fund_data.get('fund-share')
            data_source = fund_data.get('fund-data')
            fund_code = fund_data.get('fund-code')
            
            if not data_source or share is None:
                continue
                
            df = None
            # 处理不同的数据源 (复用现有逻辑)
            if data_source.startswith('script:'):
                script_name = data_source[7:]
                if fund_code:
                    df = execute_custom_script(script_name, fund_code)
                    if df is not None and 'time' in df.columns:
                        df['time'] = pd.to_datetime(df['time'])
                        df = df.set_index('time')
                        value_cols = [col for col in df.columns if df[col].dtype in ['float64', 'int64']]
                        if value_cols:
                            value_col = value_cols[0]
                            # 不在这里归一化，稍后统一处理
                            df.rename(columns={value_col: fund_id}, inplace=True)
                            fund_dfs.append({'df': df[[fund_id]], 'share': share})
            elif os.path.exists(data_source):
                try:
                    df = pd.read_csv(data_source)
                    if 'time' in df.columns:
                        value_col = next((col for col in df.columns if col.lower() != 'time'), None)
                        if value_col:
                            df['time'] = pd.to_datetime(df['time'])
                            df = df.set_index('time')
                            df.rename(columns={value_col: fund_id}, inplace=True)
                            fund_dfs.append({'df': df[[fund_id]], 'share': share})
                    elif 'FSRQ' in df.columns and 'DWJZ' in df.columns:
                        df = df.rename(columns={'FSRQ': 'time', 'DWJZ': 'nav'})
                        df['time'] = pd.to_datetime(df['time'])
                        df = df.set_index('time')
                        df = df.sort_index()
                        df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
                        df = df.dropna()
                        df.rename(columns={'nav': fund_id}, inplace=True)
                        fund_dfs.append({'df': df[[fund_id]], 'share': share})
                except Exception as e:
                    print(f"Error processing file {data_source}: {e}")
                    continue
        
        if fund_dfs:
            # 获取这个组合的时间范围
            combined_df = pd.concat([f['df'] for f in fund_dfs], axis=1)
            combined_df = combined_df.sort_index()
            portfolio_start = combined_df.index.min()
            
            # 更新全局最晚开始时间
            if global_latest_start is None or portfolio_start > global_latest_start:
                global_latest_start = portfolio_start
            
            portfolio_data.append({
                'portfolio_id': p_id,
                'portfolio_name': portfolio_name,
                'fund_dfs': fund_dfs,
                'start_time': portfolio_start
            })
    
    if not portfolio_data or global_latest_start is None:
        return [], {'display': 'none'}
    
    print(f"🎯 智能归一化：使用全局最晚开始时间 {global_latest_start.strftime('%Y-%m-%d')} 作为基准")
    
    # 基于全局最晚开始时间重新处理所有组合
    traces = []
    for pdata in portfolio_data:
        fund_dfs = pdata['fund_dfs']
        portfolio_name = pdata['portfolio_name']
        
        # 截取到全局最晚开始时间并归一化
        normalized_fund_dfs = []
        for fund in fund_dfs:
            df = fund['df']
            fund_id = df.columns[0]
            
            # 截取到全局最晚开始时间
            truncated_df = df[df.index >= global_latest_start]
            if not truncated_df.empty:
                # 以全局最晚开始时间点的值为基准归一化
                first_value = truncated_df[fund_id].iloc[0]
                if first_value != 0:
                    truncated_df = truncated_df.copy()
                    truncated_df[fund_id] = truncated_df[fund_id] / first_value
                normalized_fund_dfs.append({
                    'df': truncated_df,
                    'share': fund['share']
                })
        
        if normalized_fund_dfs:
            # 计算组合净值
            combined_df = pd.concat([f['df'] for f in normalized_fund_dfs], axis=1)
            combined_df = combined_df.sort_index()
            combined_df.ffill(inplace=True)
            combined_df.bfill(inplace=True)
            
            nav = pd.Series(0.0, index=combined_df.index)
            for fund in normalized_fund_dfs:
                fund_id = fund['df'].columns[0]
                if fund_id in combined_df.columns and not combined_df[fund_id].isnull().all():
                    nav += combined_df[fund_id] * (fund['share'] / 100.0)
            
            if not nav.empty and nav.notna().any():
                # 添加标记表示这是智能归一化的结果
                chart_name = f"{portfolio_name} (归一化至 {global_latest_start.strftime('%Y-%m-%d')})"
                traces.append(go.Scatter(
                    x=nav.index,
                    y=nav,
                    mode='lines',
                    name=chart_name,
                    line=dict(dash='dot' if len(traces) % 2 == 1 else 'solid')  # 交替使用虚线和实线
                ))
                
                # 保存净值数据用于投资分析
                try:
                    print(f"智能归一化保存组合净值数据: {portfolio_name}, 数据点: {len(nav)}")
                except Exception:
                    pass
                portfolio_nav_data[portfolio_name] = nav
    
    # Create Figure
    figure = go.Figure(
        data=traces,
        layout=go.Layout(
            title='智能归一化组合对比 - 基于最晚开始时间',
            xaxis={'title': '时间'},
            yaxis={'title': '组合净值 (智能归一化)'},
            hovermode='x unified',
            template='plotly_white',
            legend_title_text='组合',
            margin=dict(l=40, r=40, t=60, b=40)
        )
    )

    graph_component = dcc.Graph(
        figure=figure,
        style={'height': '600px'}
    ) if traces else []

    # Calculate investment analytics for normalized data
    analytics_data = []
    if portfolio_nav_data:
        try:
            print(f"智能归一化：开始计算投资分析，共有 {len(portfolio_nav_data)} 个组合")
        except Exception:
            pass
        # 统一用所有组合净值序列的交集时间区间
        nav_series_list = list(portfolio_nav_data.values())
        if nav_series_list:
            # 取所有净值序列的时间索引交集
            common_index = nav_series_list[0].index
            for s in nav_series_list[1:]:
                common_index = common_index.intersection(s.index)
            print(f"  统一分析区间: {common_index.min().strftime('%Y-%m-%d')} ~ {common_index.max().strftime('%Y-%m-%d')}, 共 {len(common_index)} 天")
            for portfolio_name, nav_series in portfolio_nav_data.items():
                nav_common = nav_series.loc[common_index]
                print(f"  计算归一化组合: {portfolio_name}, 数据点: {len(nav_common)}")
                metrics = calculate_investment_metrics(nav_common, f"{portfolio_name} (归一化)")
                if metrics:
                    try:
                        print(f"{portfolio_name} 归一化分析完成")
                    except Exception:
                        pass
                    analytics_data.append(metrics)
                else:
                    try:
                        print(f"{portfolio_name} 归一化分析失败")
                    except Exception:
                        pass
    else:
        try:
            print("智能归一化：没有组合净值数据用于分析")
        except Exception:
            pass
    
    try:
        print(f"智能归一化投资分析结果：{len(analytics_data)} 个组合")
    except Exception:
        pass
    
    # Create analytics table
    analytics_component = create_analytics_table(analytics_data) if analytics_data else html.Div("暂无投资分析数据", style={'textAlign': 'center', 'color': 'gray', 'padding': '20px'})
    analytics_style = {'display': 'block', 'maxWidth': '1200px', 'margin': '20px auto 0 auto'}

    graph_style = {'display': 'block' if traces else 'none'}
    
    return graph_component, graph_style, analytics_component, analytics_style

# Callback to show/hide fund code input based on data source selection
@app.callback(
    [Output({'type': 'fund-code', 'portfolio_id': ALL, 'fund_id': ALL}, 'style'),
     Output({'type': 'param-hint', 'portfolio_id': ALL, 'fund_id': ALL}, 'style')],
    Input({'type': 'fund-data', 'portfolio_id': ALL, 'fund_id': ALL}, 'value'),
    prevent_initial_call=True
)
def toggle_fund_code_visibility(data_sources):
    """根据数据源选择显示或隐藏基金代码输入框和提示文本"""
    input_styles = []
    hint_styles = []
    
    for data_source in data_sources:
        if data_source and data_source.startswith('script:'):
            # 如果选择的是脚本，显示参数输入框和提示
            input_style = {
                **INPUT_STYLE, 
                'width': '200px',
                'marginRight': '8px',
                'display': 'block'
            }
            hint_style = {
                'fontSize': '12px',
                'color': COLORS['secondary'],
                'fontStyle': 'italic',
                'display': 'inline'
            }
        else:
            # 否则隐藏参数输入框和提示
            input_style = {
                **INPUT_STYLE, 
                'width': '200px',
                'marginRight': '8px',
                'display': 'none'
            }
            hint_style = {
                'fontSize': '12px',
                'color': COLORS['secondary'],
                'fontStyle': 'italic',
                'display': 'none'
            }
        input_styles.append(input_style)
        hint_styles.append(hint_style)
    
    return input_styles, hint_styles

# Callback to add a new portfolio card
@app.callback(
    Output('portfolios-container', 'children'),
    Input('add-portfolio-btn', 'n_clicks'),
    Input({'type': 'remove-portfolio-btn', 'portfolio_id': ALL}, 'n_clicks'),
    State('portfolios-container', 'children'),
    prevent_initial_call=True
)
def manage_portfolios(add_clicks, remove_clicks, children):
    ctx = dash.callback_context
    if not ctx.triggered:
        return children

    triggered_id_str = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Handle add portfolio button
    if triggered_id_str == 'add-portfolio-btn':
        new_portfolio_id = str(uuid.uuid4())
        new_card = create_portfolio_card(new_portfolio_id, add_clicks)
        children.append(new_card)
        return children
    
    # Handle remove portfolio button
    try:
        triggered_id = eval(triggered_id_str)
        if triggered_id['type'] == 'remove-portfolio-btn':
            portfolio_id_to_remove = triggered_id['portfolio_id']
            
            # Remove the portfolio with the specified ID
            updated_children = [
                child for child in children 
                if child['props']['id']['portfolio_id'] != portfolio_id_to_remove
            ]
            return updated_children
    except:
        # If parsing fails, return original children
        pass
    
    return children

# Callback to add or remove a fund entry in a portfolio
@app.callback(
    Output({'type': 'funds-container', 'portfolio_id': ALL}, 'children'),
    Input({'type': 'add-fund-btn', 'portfolio_id': ALL}, 'n_clicks'),
    Input({'type': 'remove-fund-btn', 'portfolio_id': ALL, 'fund_id': ALL}, 'n_clicks'),
    State({'type': 'funds-container', 'portfolio_id': ALL}, 'children'),
    prevent_initial_call=False  # 允许初始调用
)
def manage_funds(add_clicks, remove_clicks, fund_containers):
    ctx = dash.callback_context
    
    # 处理初始化情况
    if not ctx.triggered or ctx.triggered[0]['prop_id'] == '.':
        # 初始化时，为每个空的容器添加基金条目
        for i, container in enumerate(fund_containers):
            if container is None or len(container) == 0:
                # 获取对应的 portfolio_id
                state_id = ctx.states_list[0][i]['id']
                portfolio_id = state_id['portfolio_id']
                
                # 为每个组合创建初始基金条目
                new_fund_id = str(uuid.uuid4())
                fund_containers[i] = [create_fund_entry(portfolio_id, new_fund_id)]
        return fund_containers

    triggered_id_str = ctx.triggered[0]['prop_id'].split('.')[0]
    triggered_id = eval(triggered_id_str)
    portfolio_id = triggered_id['portfolio_id']

    # Find the index of the container that was triggered
    triggered_index = -1
    # The state for fund_containers is the first and only State, so it's at index 0.
    for i, state_id in enumerate(ctx.states_list[0]):
        if state_id['id']['portfolio_id'] == portfolio_id:
            triggered_index = i
            break
    
    if triggered_index == -1:
        return fund_containers

    # Check if an "add" button was clicked
    if triggered_id['type'] == 'add-fund-btn':
        # We need to find which add button was clicked.
        # The n_clicks for the button that was just clicked will be greater than 0.
        # This check is important to prevent adding a fund on app start.
        if sum(c for c in add_clicks if c is not None) > 0:
            new_fund_id = str(uuid.uuid4())
            new_fund_ui = create_fund_entry(portfolio_id, new_fund_id)
            # Ensure the container is a list
            if fund_containers[triggered_index] is None:
                fund_containers[triggered_index] = []
            fund_containers[triggered_index].append(new_fund_ui)

    # Check if a "remove" button was clicked
    elif triggered_id['type'] == 'remove-fund-btn':
        fund_id_to_remove = triggered_id['fund_id']
        
        # Filter out the fund to be removed from the specific portfolio's container
        current_funds = fund_containers[triggered_index]
        if current_funds:
            updated_funds = [
                fund for fund in current_funds 
                if fund['props']['id'] != f"fund-entry-{fund_id_to_remove}"
            ]
            fund_containers[triggered_index] = updated_funds

    return fund_containers


@app.callback(
    Output('graph-container', 'children'),
    Output('graph-container', 'style'),
    Output('analytics-section', 'children'),
    Output('analytics-section', 'style'),
    Output({'type': 'share-feedback', 'portfolio_id': ALL}, 'children'),
    Input('generate-chart-btn', 'n_clicks'),
    State({'type': 'fund-name', 'portfolio_id': ALL, 'fund_id': ALL}, 'value'),
    State({'type': 'fund-share', 'portfolio_id': ALL, 'fund_id': ALL}, 'value'),
    State({'type': 'fund-data', 'portfolio_id': ALL, 'fund_id': ALL}, 'value'),
    State({'type': 'fund-code', 'portfolio_id': ALL, 'fund_id': ALL}, 'value'),
    State({'type': 'portfolio-name', 'portfolio_id': ALL}, 'value'),
    State('portfolios-container', 'children')
)
def update_graph_and_feedback(n_clicks, fund_names, fund_shares, fund_datas, fund_codes, portfolio_names, portfolios_container):
    import dash
    ctx = dash.callback_context
    if not ctx.triggered or n_clicks is None or n_clicks == 0:
        # 初始或未点击时隐藏图表和分析
        return [], {'display': 'none'}, [], {'display': 'none'}, ["" for _ in portfolio_names]

    # --- 1. Parse all inputs into a structured dictionary ---

    portfolios = {}
    portfolio_names_dict = {}
    # 修复：通过 ctx.states_list 获取 portfolio_id
    if hasattr(ctx, "states_list") and len(ctx.states_list) > 4:
        for i, value in enumerate(portfolio_names):
            if value is not None and value != "":
                state_id = ctx.states_list[4][i]['id']
                portfolio_id = state_id['portfolio_id']
                portfolio_names_dict[portfolio_id] = value

    # 修复：通过 states_list 获取 fund 输入的 id 信息
    fund_inputs = [
        (fund_names, 0),
        (fund_shares, 1),
        (fund_datas, 2),
        (fund_codes, 3)
    ]
    for arr, state_idx in fund_inputs:
        if hasattr(ctx, "states_list") and len(ctx.states_list) > state_idx:
            for i, value in enumerate(arr):
                if value is None or value == "":
                    continue
                state_id = ctx.states_list[state_idx][i]['id']
                input_type = state_id['type']
                portfolio_id = state_id['portfolio_id']
                fund_id = state_id['fund_id']
                # 赋值
                if portfolio_id not in portfolios:
                    portfolios[portfolio_id] = {
                        'funds': {},
                        'name': portfolio_names_dict.get(portfolio_id, f"组合 {len(portfolios) + 1}")
                    }
                if fund_id not in portfolios[portfolio_id]['funds']:
                    portfolios[portfolio_id]['funds'][fund_id] = {}
                portfolios[portfolio_id]['funds'][fund_id][input_type] = value
                if portfolio_id in portfolio_names_dict:
                    portfolios[portfolio_id]['name'] = portfolio_names_dict[portfolio_id]

    # --- 2. Process data and calculate portfolio values ---
    traces = []
    feedback_messages = {}
    portfolio_nav_data = {}  # 存储每个组合的净值数据用于分析
    
    for p_id, p_data in portfolios.items():
        total_share = 0
        fund_dfs = []
        portfolio_name = p_data.get('name')
        unique_portfolio_key = f"{portfolio_name} [{p_id[:8]}]"
        for fund_id, fund_data in p_data['funds'].items():
            share = fund_data.get('fund-share')
            data_source = fund_data.get('fund-data')
            fund_code = fund_data.get('fund-code')
            fund_name = fund_data.get('fund-name') or f"基金-{fund_id[:4]}"
            if share is not None:
                total_share += share
            df = None
            # 处理不同的数据源
            if data_source:
                if data_source.startswith('script:'):
                    script_name = data_source[7:]
                    if fund_code:
                        print(f"正在执行脚本 {script_name} 获取基金 {fund_code} 数据...")
                        df = execute_custom_script(script_name, fund_code)
                        if df is not None and 'time' in df.columns:
                            df['time'] = pd.to_datetime(df['time'])
                            df = df.set_index('time')
                            value_cols = [col for col in df.columns if df[col].dtype in ['float64', 'int64']]
                            if value_cols:
                                value_col = value_cols[0]
                                df[value_col] = df[value_col] / df[value_col].iloc[0]
                                df.rename(columns={value_col: fund_id}, inplace=True)
                                fund_dfs.append({'df': df[[fund_id]], 'share': share or 0})
                                print(f"脚本数据处理成功: {len(df)} 条记录")
                            else:
                                print(f"脚本返回的数据中没有找到数值列")
                        else:
                            print(f"脚本 {script_name} 执行失败或返回数据格式不正确")
                    else:
                        print(f"使用脚本 {script_name} 但未提供基金代码")
                elif os.path.exists(data_source):
                    try:
                        df = pd.read_csv(data_source)
                        if 'time' in df.columns:
                            value_col = next((col for col in df.columns if col.lower() != 'time'), None)
                            if value_col:
                                df['time'] = pd.to_datetime(df['time'])
                                df = df.set_index('time')
                                df[value_col] = df[value_col] / df[value_col].iloc[0]
                                df.rename(columns={value_col: fund_id}, inplace=True)
                                fund_dfs.append({'df': df[[fund_id]], 'share': share or 0})
                        elif 'FSRQ' in df.columns and 'DWJZ' in df.columns:
                            df = df.rename(columns={'FSRQ': 'time', 'DWJZ': 'nav'})
                            df['time'] = pd.to_datetime(df['time'])
                            df = df.set_index('time')
                            df = df.sort_index()
                            df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
                            df = df.dropna()
                            df['nav'] = df['nav'] / df['nav'].iloc[0]
                            df.rename(columns={'nav': fund_id}, inplace=True)
                            fund_dfs.append({'df': df[[fund_id]], 'share': share or 0})
                    except Exception as e:
                        print(f"Error processing file {data_source}: {e}")
                        continue
        if round(total_share, 2) != 100 and total_share > 0:
            feedback_messages[p_id] = f"份额总和为 {total_share}%, 不等于 100%！"
        else:
            feedback_messages[p_id] = ""
        
        if fund_dfs:
            # 新增：时间区间对齐处理
            aligned_fund_dfs, time_stats = align_time_series_data(fund_dfs, portfolio_name)
            
            if aligned_fund_dfs:
                combined_df = pd.concat([f['df'] for f in aligned_fund_dfs], axis=1)
                combined_df = combined_df.sort_index()
                combined_df.ffill(inplace=True)
                combined_df.bfill(inplace=True)
                nav = pd.Series(0.0, index=combined_df.index)
                for fund in aligned_fund_dfs:
                    fund_id = fund['df'].columns[0]
                    if fund_id in combined_df.columns and not combined_df[fund_id].isnull().all():
                        nav += combined_df[fund_id] * (fund['share'] / 100.0)
                if not nav.empty and nav.notna().any():
                    # 生成图表名称，包含时间信息
                    chart_name = portfolio_name
                    if time_stats and time_stats['aligned']:
                        start_date = time_stats['latest_start'].strftime('%Y-%m-%d')
                        chart_name += f" (对齐至 {start_date})"
                    
                    traces.append(go.Scatter(
                        x=nav.index,
                        y=nav,
                        mode='lines',
                        name=chart_name
                    ))
                    
                    # 保存净值数据用于投资分析
                    try:
                        print(f"保存组合净值数据: {unique_portfolio_key}, 数据点: {len(nav)}")
                    except Exception:
                        pass
                    portfolio_nav_data[unique_portfolio_key] = nav
                    
                    # 更新反馈信息，包含时间对齐状态
                    if time_stats and time_stats['aligned']:
                        alignment_info = f"已对齐至 {time_stats['latest_start'].strftime('%Y-%m-%d')}"
                        if feedback_messages[p_id]:
                            feedback_messages[p_id] += f" | {alignment_info}"
                        else:
                            feedback_messages[p_id] = alignment_info
    # --- 3. Prepare outputs ---
    # Create Figure and wrap it in dcc.Graph
    figure = go.Figure(
        data=traces,
        layout=go.Layout(
            xaxis={'title': '时间'},
            yaxis={'title': '组合净值 (归一化)'},
            hovermode='x unified',
            template='plotly_white',
            legend_title_text='组合',
            margin=dict(l=40, r=40, t=40, b=40)
        )
    )

    # Wrap the figure in a dcc.Graph component
    graph_component = dcc.Graph(
        figure=figure,
        style={'height': '600px'}
    ) if traces else []

    # --- 4. Calculate investment analytics ---
    analytics_data = []
    try:
        print(f"调试：portfolio_nav_data 包含 {len(portfolio_nav_data)} 个组合")
    except Exception:
        pass
    if portfolio_nav_data:
        try:
            print(f"开始计算投资分析，共有 {len(portfolio_nav_data)} 个组合")
        except Exception:
            pass
        for unique_portfolio_key, nav_series in portfolio_nav_data.items():
            try:
                print(f"计算组合: {unique_portfolio_key}, 数据点: {len(nav_series)}")
            except Exception:
                pass
            metrics = calculate_investment_metrics(nav_series, unique_portfolio_key)
            if metrics:
                try:
                    print(f"{unique_portfolio_key} 分析完成")
                except Exception:
                    pass
                analytics_data.append(metrics)
            else:
                try:
                    print(f"{unique_portfolio_key} 分析失败")
                except Exception:
                    pass
    else:
        try:
            print("没有组合净值数据用于分析")
        except Exception:
            pass
        try:
            print(f"调试：portfolio_nav_data 详情: {portfolio_nav_data}")
        except Exception:
            pass
    
    try:
        print(f"投资分析结果：{len(analytics_data)} 个组合")
    except Exception:
        pass
    
    # Create analytics table
    analytics_component = create_analytics_table(analytics_data) if analytics_data else html.Div("暂无投资分析数据", style={'textAlign': 'center', 'color': 'gray', 'padding': '20px'})
    analytics_style = {'display': 'block', 'maxWidth': '1200px', 'margin': '20px auto 0 auto'}

    # Match feedback messages to the correct output components
    output_feedback_list = []
    all_feedback_ids = [out['id']['portfolio_id'] for out in ctx.outputs_list[4]]
    for p_id in all_feedback_ids:
        output_feedback_list.append(feedback_messages.get(p_id, ""))

    graph_style = {'display': 'block' if traces else 'none'}

    # 直接将分析内容作为 analytics-section 的 children 输出
    return graph_component, graph_style, [analytics_component], analytics_style, output_feedback_list


# --- Custom CSS Styles ---
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            /* Custom dropdown styles - 优化垂直居中和clear按钮定位 */
            .Select-control {
                display: flex !important;
                align-items: center !important;
                border: 2px solid #E5E8E8 !important;
                border-radius: 6px !important;
                box-shadow: none !important;
                transition: border-color 0.3s ease !important;
                font-size: 14px !important;
                font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif !important;
                height: 38px !important;
                min-height: 38px !important;
                box-sizing: border-box !important;
                position: relative !important;
            }
            .Select-control:hover {
                border-color: #2E86C1 !important;
            }
            .Select-control.is-focused {
                border-color: #2E86C1 !important;
                box-shadow: 0 0 0 3px rgba(46, 134, 193, 0.1) !important;
            }
            
            /* 修复value区域的布局 */
            .Select-value {
                height: 100% !important;
                display: flex !important;
                align-items: center !important;
                font-size: 16px !important;
                font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif !important;
                padding: 8px 12px !important;
                margin: 0 !important;
                line-height: 18px !important;
                flex: 1 !important;
                padding-right: 60px !important; /* 为clear按钮和箭头留出空间 */
            }
            
            .Select-placeholder,
            .Select-input {
                height: 100% !important;
                display: flex !important;
                align-items: center !important;
                font-size: 15px !important;
                font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif !important;
                padding: 8px 12px !important;
                margin: 0 !important;
                line-height: 18px !important;
                flex: 1 !important;
                padding-right: 60px !important; /* 为clear按钮和箭头留出空间 */
            }
            
            .Select-value-label {
                font-size: 15px !important;
                font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif !important;
                color: #2C3E50 !important;
                flex: 1 !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                white-space: nowrap !important;
            }
            .Select-input > input {
                font-size: 15px !important;
                font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif !important;
                padding: 0 !important;
                margin: 0 !important;
                border: none !important;
                outline: none !important;
                background: transparent !important;
                width: 100% !important;
                line-height: 18px !important;
            }
            .Select-option {
                display: flex !important;
                align-items: center !important;
                height: 38px !important;
                font-size: 15px !important;
                font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif !important;
                padding: 8px 12px !important;
                line-height: 18px !important;
            }
            .Select-clear-zone {
                width: 24px !important;
                height: 24px !important;
                position: absolute !important;
                right: 32px !important; /* 在箭头左侧 */
                top: 50% !important;
                transform: translateY(-50%) !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                cursor: pointer !important;
                z-index: 1 !important;
            }
            
            .Select-clear {
                font-size: 16px !important;
                color: #7B7D7D !important;
                line-height: 1 !important;
                display: block !important;
            }
            
            .Select-clear:hover {
                color: #EC7063 !important;
            }
            
            .Select-input > input {
                font-size: 14px !important;
                font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif !important;
                padding: 0 !important;
                margin: 0 !important;
                border: none !important;
                outline: none !important;
                background: transparent !important;
                width: 100% !important;
                line-height: 18px !important;
            }
            .Select-option {
                display: flex !important;
                align-items: center !important;
                height: 38px !important;
                font-size: 14px !important;
                font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif !important;
                padding: 8px 12px !important;
                line-height: 18px !important;
            }
            
            /* 箭头区域 */
            .Select-arrow-zone {
                width: 30px !important;
                position: absolute !important;
                right: 0 !important;
                top: 0 !important;
                height: 100% !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }
            .Select-arrow {
                border-color: #7B7D7D transparent transparent !important;
                border-width: 5px 5px 0 !important;
                border-style: solid !important;
                display: block !important;
            }
            
            /* Input focus effects */
            input:focus {
                border-color: #2E86C1 !important;
                box-shadow: 0 0 0 3px rgba(46, 134, 193, 0.1) !important;
            }
            
            /* Button hover effects */
            button:hover {
                transform: translateY(-2px) !important;
                box-shadow: 0 4px 8px rgba(0,0,0,0.15) !important;
            }
            
            /* Card hover effects */
            .portfolio-card:hover {
                transform: translateY(-2px) !important;
                box-shadow: 0 8px 24px rgba(0,0,0,0.12) !important;
            }
            
            /* Loading indicator */
            ._dash-loading {
                color: #2E86C1 !important;
            }
            
            /* Plotly graph styling */
            .js-plotly-plot .plotly .modebar {
                background: rgba(248, 249, 250, 0.9) !important;
                border-radius: 8px !important;
                margin: 10px !important;
            }
            
            /* Scrollbar styling */
            ::-webkit-scrollbar {
                width: 8px;
            }
            ::-webkit-scrollbar-track {
                background: #F8F9FA;
            }
            ::-webkit-scrollbar-thumb {
                background: #2E86C1;
                border-radius: 4px;
            }
            ::-webkit-scrollbar-thumb:hover {
                background: #5DADE2;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''


if __name__ == '__main__':
    app.run(debug=True, port=8051)
