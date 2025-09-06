"""
基金组合回测工具 - 主应用文件
重构后的版本，专注于UI布局和回调函数
"""

import dash
from dash import dcc, html, Input, Output, State, ALL
import pandas as pd
import plotly.graph_objs as go
import os
import uuid
import sys

# 导入模块化组件
from modules.config import COLORS, INPUT_STYLE, CSS_STYLES, PRIMARY_BUTTON_STYLE
from modules.data_handler import (
    get_available_data_files, get_available_scripts, 
    execute_custom_script, save_fund_data_individually
)
from modules.analytics import (
    align_time_series_data, calculate_investment_metrics, 
    create_analytics_table
)
from modules.ui_components import (
    create_fund_entry, create_portfolio_card, create_header_section,
    create_controls_section, create_chart_section
)

# 简单的日志函数，避免编码问题
def safe_print(*args):
    """安全的打印函数，避免Windows编码问题"""
    try:
        # 只在开发模式下输出，并且转换为简单的ASCII
        if __debug__:
            message = ' '.join(str(arg) for arg in args)
            # 移除可能有问题的字符
            safe_message = ''.join(c if ord(c) < 128 else '?' for c in message)
            safe_print(safe_message[:200])  # 限制长度
    except:
        pass  # 完全忽略打印错误

# --- App Initialization ---
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "基金组合回测"

# Create initial base portfolio that cannot be deleted
initial_portfolio_id = 'base-portfolio'
initial_fund_id = str(uuid.uuid4())

# --- App Layout ---
app.layout = html.Div([
    # --- Header Section ---
    create_header_section(),

    # --- Controls Section ---
    create_controls_section(),

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
            
            html.Div([
                html.Button('➕ 添加基金', 
                           id={'type': 'add-fund-btn', 'portfolio_id': initial_portfolio_id}, 
                           n_clicks=0, 
                           style={**PRIMARY_BUTTON_STYLE, 'marginTop': '15px'}),
                html.Div(id={'type': 'share-feedback', 'portfolio_id': initial_portfolio_id}, 
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
        ], id={'type': 'portfolio-card', 'portfolio_id': initial_portfolio_id}, 
           style={
               'backgroundColor': COLORS['white'],
               'borderRadius': '12px',
               'padding': '24px',
               'marginBottom': '20px',
               'boxShadow': f'0 4px 12px {COLORS["shadow"]}',
               'border': f'1px solid {COLORS["border"]}'
           })
    ], style={'maxWidth': '1200px', 'margin': '0 auto', 'padding': '0 20px'}),

    # --- Chart Section ---
    create_chart_section(),

], style={
    'fontFamily': '"Segoe UI", Tahoma, Geneva, Verdana, sans-serif',
    'backgroundColor': f'{COLORS["light"]}',
    'minHeight': '100vh',
    'paddingBottom': '40px'
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
    
    # Save data to CSV files (按条目分开保存，只保存脚本数据源)
    saved_files, errors, skipped_files = save_fund_data_individually(portfolios)
    
    # Prepare status message
    if saved_files or skipped_files:
        message_parts = []
        
        if saved_files:
            message_parts.append("✅ 基金数据按条目保存成功！")
            message_parts.append(f"📁 已保存 {len(saved_files)} 个基金数据文件：")
            for file_info in saved_files:
                fund_info = f"{file_info['fund_name']} ({file_info['fund_code']})"
                if file_info['share']:
                    fund_info += f" - 份额: {file_info['share']}%"
                message_parts.append(f"• {file_info['filename']}")
                message_parts.append(f"  └─ {fund_info} | {file_info['rows']} 行数据")
        
        if skipped_files:
            message_parts.append("ℹ️ 跳过的本地数据源：")
            for skip_info in skipped_files:
                fund_info = f"{skip_info['fund_name']} ({skip_info['fund_code']})"
                message_parts.append(f"• {fund_info}")
                message_parts.append(f"  └─ 来源: {skip_info['source_file']} | {skip_info['reason']}")
        
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
    
    import dash
    ctx = dash.callback_context
    
    # 强化检查逻辑，确保只有在按钮被明确点击时才执行
    # 移除调试输出以避免Windows编码问题
    
    if n_clicks is None or n_clicks == 0:
        return [], {'display': 'none'}, [], {'display': 'none'}
    
    # 额外检查：确保触发的是正确的按钮
    if not ctx.triggered or ctx.triggered[0]['prop_id'] != 'normalize-chart-btn.n_clicks':
        return [], {'display': 'none'}, [], {'display': 'none'}
    
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
                    safe_print("Error processing file {}: {}".format(data_source, str(e)))
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
    
    try:
        start_date_str = global_latest_start.strftime('%Y-%m-%d')
        safe_print("Smart normalization: Using latest start time {} as baseline".format(start_date_str))
    except Exception as e:
        safe_print("Smart normalization: Using latest start time as baseline (date formatting error: {})".format(str(e)))
    
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
                try:
                    date_str = global_latest_start.strftime('%Y-%m-%d')
                    chart_name = f"{portfolio_name} (归一化至 {date_str})"
                except Exception as e:
                    chart_name = f"{portfolio_name} (归一化)"
                traces.append(go.Scatter(
                    x=nav.index,
                    y=(nav - 1) * 100,  # 转换为百分比收益率
                    mode='lines',
                    name=chart_name,
                    line=dict(dash='dot' if len(traces) % 2 == 1 else 'solid'),  # 交替使用虚线和实线
                    hovertemplate='<b>%{fullData.name}</b><br>' +
                                  '时间: %{x}<br>' +
                                  '收益率: %{y:.2f}%<br>' +
                                  '<extra></extra>'
                ))
                
                # 保存净值数据用于投资分析
                try:
                    safe_print("Smart normalization saved portfolio nav data: {}, data points: {}".format(portfolio_name, len(nav)))
                except Exception:
                    pass
                portfolio_nav_data[portfolio_name] = nav
    
    # Create Figure
    figure = go.Figure(
        data=traces,
        layout=go.Layout(
            title='智能归一化组合对比 - 基于最晚开始时间',
            xaxis={'title': '时间'},
            yaxis={'title': '收益率 (%)', 'tickformat': '.1f'},
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
            safe_print("Smart normalization: Starting investment analysis, portfolios:", len(portfolio_nav_data))
        except Exception:
            pass
        # 统一用所有组合净值序列的交集时间区间
        nav_series_list = list(portfolio_nav_data.values())
        if nav_series_list:
            # 取所有净值序列的时间索引交集
            common_index = nav_series_list[0].index
            for s in nav_series_list[1:]:
                common_index = common_index.intersection(s.index)
            start_str = common_index.min().strftime('%Y-%m-%d')
            end_str = common_index.max().strftime('%Y-%m-%d')
            safe_print("统一分析区间: {} ~ {}, 共 {} 天".format(start_str, end_str, len(common_index)))
            for portfolio_name, nav_series in portfolio_nav_data.items():
                nav_common = nav_series.loc[common_index]
                safe_print("计算归一化组合: {}, 数据点: {}".format(portfolio_name, len(nav_common)))
                metrics = calculate_investment_metrics(nav_common, "{} (归一化)".format(portfolio_name))
                if metrics:
                    try:
                        safe_print("{} 归一化分析完成".format(portfolio_name))
                    except Exception:
                        pass
                    analytics_data.append(metrics)
                else:
                    try:
                        safe_print("{} 归一化分析失败".format(portfolio_name))
                    except Exception:
                        pass
    else:
        try:
            safe_print("Smart normalization: No portfolio nav data for analysis")
        except Exception:
            pass
    
    try:
        safe_print("Smart normalization investment analysis results: {} portfolios".format(len(analytics_data)))
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
                        safe_print("正在执行脚本 {} 获取基金 {} 数据...".format(script_name, fund_code))
                        df = execute_custom_script(script_name, fund_code)
                        if df is not None and 'time' in df.columns:
                            df['time'] = pd.to_datetime(df['time'])
                            df = df.set_index('time')
                            value_cols = [col for col in df.columns if df[col].dtype in ['float64', 'int64']]
                            if value_cols:
                                value_col = value_cols[0]
                                # 不在这里归一化，保留原始数据
                                df.rename(columns={value_col: fund_id}, inplace=True)
                                fund_dfs.append({'df': df[[fund_id]], 'share': share})
                                safe_print("脚本数据处理成功: {} 条记录".format(len(df)))
                            else:
                                safe_print("脚本返回的数据中没有找到数值列")
                        else:
                            safe_print("脚本 {} 执行失败或返回数据格式不正确".format(script_name))
                    else:
                        safe_print("使用脚本 {} 但未提供基金代码".format(script_name))
                elif os.path.exists(data_source):
                    try:
                        df = pd.read_csv(data_source)
                        if 'time' in df.columns:
                            value_col = next((col for col in df.columns if col.lower() != 'time'), None)
                            if value_col:
                                df['time'] = pd.to_datetime(df['time'])
                                df = df.set_index('time')
                                # 不在这里归一化，保留原始数据
                                df.rename(columns={value_col: fund_id}, inplace=True)
                                fund_dfs.append({'df': df[[fund_id]], 'share': share})
                        elif 'FSRQ' in df.columns and 'DWJZ' in df.columns:
                            df = df.rename(columns={'FSRQ': 'time', 'DWJZ': 'nav'})
                            df['time'] = pd.to_datetime(df['time'])
                            df = df.set_index('time')
                            df = df.sort_index()
                            df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
                            df = df.dropna()
                            # 不在这里归一化，保留原始数据
                            df.rename(columns={'nav': fund_id}, inplace=True)
                            fund_dfs.append({'df': df[[fund_id]], 'share': share})
                    except Exception as e:
                        safe_print("Error processing file {}: {}".format(data_source, str(e)))
                        continue
        if round(total_share, 2) != 100 and total_share > 0:
            feedback_messages[p_id] = "份额总和为 {}%, 不等于 100%！".format(total_share)
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
                        y=(nav - 1) * 100,  # 转换为百分比收益率
                        mode='lines',
                        name=chart_name,
                        hovertemplate='<b>%{fullData.name}</b><br>' +
                                      '时间: %{x}<br>' +
                                      '收益率: %{y:.2f}%<br>' +
                                      '<extra></extra>'
                    ))
                    
                    # 保存净值数据用于投资分析
                    try:
                        safe_print("保存组合净值数据: {}, 数据点: {}".format(unique_portfolio_key, len(nav)))
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
            yaxis={'title': '收益率 (%)', 'tickformat': '.1f'},
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
        safe_print("调试：portfolio_nav_data 包含组合数:", len(portfolio_nav_data))
    except Exception:
        pass
    if portfolio_nav_data:
        try:
            safe_print("开始计算投资分析，共有组合数:", len(portfolio_nav_data))
        except Exception:
            pass
        for unique_portfolio_key, nav_series in portfolio_nav_data.items():
            try:
                safe_print("计算组合: {}, 数据点: {}".format(unique_portfolio_key, len(nav_series)))
            except Exception:
                pass
            metrics = calculate_investment_metrics(nav_series, unique_portfolio_key)
            if metrics:
                try:
                    safe_print("{} 分析完成".format(unique_portfolio_key))
                except Exception:
                    pass
                analytics_data.append(metrics)
            else:
                try:
                    safe_print("{} 分析失败".format(unique_portfolio_key))
                except Exception:
                    pass
    else:
        try:
            safe_print("没有组合净值数据用于分析")
        except Exception:
            pass
        try:
            safe_print("调试：portfolio_nav_data 详情:", str(portfolio_nav_data))
        except Exception:
            pass
    
    try:
        safe_print(f"投资分析结果：{len(analytics_data)} 个组合")
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
app.index_string = f'''
<!DOCTYPE html>
<html>
    <head>
        {{%metas%}}
        <title>{{%title%}}</title>
        {{%favicon%}}
        {{%css%}}
        <style>
            {CSS_STYLES}
        </style>
    </head>
    <body>
        {{%app_entry%}}
        <footer>
            {{%config%}}
            {{%scripts%}}
            {{%renderer%}}
        </footer>
    </body>
</html>
'''


# Callback to auto-refresh portfolio display after saving data
@app.callback(
    Output('portfolios-container', 'children', allow_duplicate=True),
    Input('save-data-btn', 'n_clicks'),
    State('portfolios-container', 'children'),
    prevent_initial_call=True
)
def refresh_portfolios_after_save(save_clicks, current_children):
    """保存数据后刷新组合显示，以便下拉菜单包含最新的文件"""
    if save_clicks is None or save_clicks == 0:
        return current_children
    
    # 简单地返回当前的children，但这会触发重新渲染
    # 重新渲染时，create_fund_entry会被调用，从而获取最新的文件列表
    return current_children


if __name__ == '__main__':
    app.run(debug=True, port=8051)
