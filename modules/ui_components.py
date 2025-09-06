"""
UI组件模块 - 创建基金条目、组合卡片等UI组件
"""

import uuid
from dash import dcc, html
from modules.config import (
    COLORS, INPUT_STYLE, DROPDOWN_STYLE, DANGER_BUTTON_STYLE, 
    PRIMARY_BUTTON_STYLE, CARD_STYLE
)
from modules.data_handler import get_available_data_files, get_available_scripts


def create_fund_entry(portfolio_id, fund_id):
    """创建单个基金条目的UI"""
    # 每次创建时都重新获取最新的文件和脚本列表，确保包含最新保存的文件
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
                    'width': '240px', 
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
    """创建单个投资组合卡片的UI"""
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
           'overflow': 'visible'
       })


def create_header_section():
    """创建页面头部区域"""
    return html.Div([
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
    })


def create_controls_section():
    """创建控制按钮区域"""
    return html.Div([
        html.Button('➕ 添加新组合', 
                   id='add-portfolio-btn', 
                   n_clicks=0, 
                   style={**PRIMARY_BUTTON_STYLE, 'marginBottom': '20px'})
    ], style={
        'textAlign': 'center',
        'marginBottom': '30px'
    })


def create_chart_section():
    """创建图表区域"""
    return html.Div([
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
                    **PRIMARY_BUTTON_STYLE,
                    'backgroundColor': COLORS['success'],
                    'marginBottom': '20px',
                    'marginRight': '15px'
                }
            ),
            html.Button(
                '📊 智能归一化',
                id='normalize-chart-btn',
                n_clicks=0,
                style={
                    **PRIMARY_BUTTON_STYLE,
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
    })
