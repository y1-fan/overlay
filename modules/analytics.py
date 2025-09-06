"""
分析模块 - 处理时间序列对齐、投资指标计算、表格生成等功能
"""

import pandas as pd
from dash import html
from modules.config import COLORS

# 安全的日志函数
def safe_print(*args):
    """安全的打印函数，避免Windows编码问题"""
    try:
        if __debug__:
            message = ' '.join(str(arg) for arg in args)
            safe_message = ''.join(c if ord(c) < 128 else '?' for c in message)
            safe_print(safe_message[:200])
    except:
        pass


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
            date_str = latest_start.strftime('%Y-%m-%d')
            safe_print("组合 '{}' 检测到时间不统一，正在对齐到最晚开始时间: {}".format(portfolio_name, date_str))
        except Exception:
            safe_print("组合检测到时间不统一，正在对齐")
        
        # 对齐所有基金数据到统一时间区间
        aligned_fund_dfs = []
        for fund in fund_dfs:
            df = fund['df']
            if not df.empty:
                # 截取到统一的时间区间
                aligned_df = df[df.index >= latest_start]
                if not aligned_df.empty:
                    aligned_fund_dfs.append({
                        'df': aligned_df,
                        'share': fund['share']
                    })
                    
                    original_points = len(df)
                    aligned_points = len(aligned_df)
                    try:
                        fund_id = aligned_df.columns[0]
                        safe_print("{}: {} -> {} 个数据点".format(fund_id, original_points, aligned_points))
                    except Exception:
                        pass
        
        # 在所有数据对齐后，统一进行归一化
        normalized_fund_dfs = []
        for fund in aligned_fund_dfs:
            df = fund['df']
            fund_id = df.columns[0]
            
            # 以对齐后的第一个值为基准进行归一化
            first_value = df[fund_id].iloc[0]
            if first_value != 0:
                normalized_df = df.copy()
                normalized_df.loc[:, fund_id] = normalized_df[fund_id] / first_value
                normalized_fund_dfs.append({
                    'df': normalized_df,
                    'share': fund['share']
                })
            else:
                # 如果第一个值为0，跳过这个基金
                try:
                    safe_print("跳过基金 {} (起始值为0)".format(fund_id))
                except Exception:
                    pass
        
        time_stats = {
            'aligned': True,
            'latest_start': latest_start,
            'earliest_end': earliest_end,
            'original_count': len(fund_dfs),
            'aligned_count': len(normalized_fund_dfs)
        }
        
        return normalized_fund_dfs, time_stats
    else:
        try:
            safe_print("组合 '{}' 时间区间已统一，无需对齐".format(portfolio_name))
        except Exception:
            pass
        
        # 即使不需要时间对齐，也需要进行归一化
        normalized_fund_dfs = []
        for fund in fund_dfs:
            df = fund['df']
            fund_id = df.columns[0]
            
            # 以第一个值为基准进行归一化
            first_value = df[fund_id].iloc[0]
            if first_value != 0:
                normalized_df = df.copy()
                normalized_df.loc[:, fund_id] = normalized_df[fund_id] / first_value
                normalized_fund_dfs.append({
                    'df': normalized_df,
                    'share': fund['share']
                })
            else:
                # 如果第一个值为0，跳过这个基金
                try:
                    safe_print("跳过基金 {} (起始值为0)".format(fund_id))
                except Exception:
                    pass
        
        time_stats = {
            'aligned': False,
            'latest_start': latest_start,
            'earliest_end': earliest_end,
            'original_count': len(fund_dfs),
            'aligned_count': len(normalized_fund_dfs)
        }
        return normalized_fund_dfs, time_stats


def calculate_investment_metrics(nav_series, portfolio_name):
    """
    计算投资组合的关键指标
    :param nav_series: 净值序列 (pandas Series)
    :param portfolio_name: 组合名称
    :return: 投资指标字典
    """
    try:
        safe_print("开始计算投资指标: {}".format(portfolio_name))
    except Exception:
        pass
    
    if nav_series.empty or len(nav_series) < 2:
        try:
            safe_print("{}: 数据不足，需要至少2个数据点".format(portfolio_name))
        except Exception:
            pass
        return None
    
    # 检查是否有NaN值
    if nav_series.isnull().any():
        try:
            safe_print("{}: 发现NaN值，进行清理".format(portfolio_name))
        except Exception:
            pass
        nav_series = nav_series.dropna()
        if len(nav_series) < 2:
            try:
                safe_print("{}: 清理NaN后数据不足".format(portfolio_name))
            except Exception:
                pass
            return None
    
    # 计算日收益率
    returns = nav_series.pct_change().dropna()
    
    if returns.empty:
        try:
            safe_print("{}: 无法计算收益率".format(portfolio_name))
        except Exception:
            pass
        return None
    
    try:
        safe_print("{}: 数据点={}, 收益率点={}".format(portfolio_name, len(nav_series), len(returns)))
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
            safe_print(sharpe_ratio)
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
        safe_print("{}: 计算完成，总收益={:.2f}%, 年化收益={:.2f}%".format(portfolio_name, total_return, annualized_return))
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
        safe_print("create_analytics_table 接收到指标数据:", len(metrics_list) if metrics_list else 0)
    except Exception:
        pass
    
    if not metrics_list:
        try:
            safe_print("metrics_list 为空，返回暂无数据提示")
        except Exception:
            pass
        return html.Div("暂无数据", style={'textAlign': 'center', 'color': COLORS['secondary']})
    
    # 详细打印每个指标数据
    for i, metrics in enumerate(metrics_list):
        try:
            portfolio_name = metrics.get('portfolio_name', 'N/A')
            total_return = metrics.get('total_return', 'N/A')
            safe_print("指标数据 {}: 组合名={}, 总收益={}%".format(i+1, portfolio_name, total_return))
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
        safe_print("create_analytics_table 返回完整表格组件，包含组合数据:", len(metrics_list))
    except Exception:
        pass
    return html.Div([table, legend])
