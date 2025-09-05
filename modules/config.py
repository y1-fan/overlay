"""
配置文件 - 存储所有颜色配置、样式定义等常量
"""

# --- 颜色配置 ---
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

# --- 基础样式 ---
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

# --- CSS样式字符串 ---
CSS_STYLES = '''
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

/* 下拉菜单样式 - 修复z-index问题 */
.Select-menu-outer {
    position: absolute !important;
    top: 100% !important;
    left: 0 !important;
    right: 0 !important;
    z-index: 9999 !important;
    background: white !important;
    border: 1px solid #E5E8E8 !important;
    border-radius: 6px !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
    margin-top: 2px !important;
    max-height: 200px !important;
    overflow-y: auto !important;
}

.Select-menu {
    background: white !important;
    border-radius: 6px !important;
    max-height: 200px !important;
    overflow-y: auto !important;
}

.Select-option {
    padding: 10px 12px !important;
    cursor: pointer !important;
    border-bottom: 1px solid #F8F9FA !important;
    transition: background-color 0.2s ease !important;
}

.Select-option:last-child {
    border-bottom: none !important;
}

.Select-option.is-focused {
    background-color: #F8F9FA !important;
    color: #2E86C1 !important;
}

.Select-option.is-selected {
    background-color: #2E86C1 !important;
    color: white !important;
}

.Select-option:hover {
    background-color: #F8F9FA !important;
    color: #2E86C1 !important;
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
'''
