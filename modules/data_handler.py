"""
数据处理模块 - 处理数据文件获取、脚本执行、数据保存等功能
"""

import os
import subprocess
import sys
import pandas as pd
from io import StringIO

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


def get_available_data_files():
    """扫描目录中可用的数据文件 (CSV)"""
    try:
        return [f for f in os.listdir('.') if f.endswith('.csv')]
    except FileNotFoundError:
        return []


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
            safe_print(f"脚本文件 {script_path} 不存在")
            return None
        
        # 执行脚本，优先用 utf-8，失败时自动回退 gbk
        cmd = [sys.executable, script_path, str(fund_code)]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, encoding='utf-8')
        except UnicodeDecodeError:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, encoding='gbk')

        if result.returncode == 0:
            # 解析CSV数据
            csv_data = result.stdout.strip()
            if csv_data:
                try:
                    df = pd.read_csv(StringIO(csv_data))
                    safe_print(f"脚本 {script_name} 执行成功，获得 {len(df)} 条数据")
                    return df
                except Exception as e:
                    safe_print(f"CSV解析失败: {e}")
                    return None
            else:
                safe_print(f"脚本 {script_name} 返回空数据")
                return None
        else:
            safe_print(f"脚本执行失败: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        safe_print(f"脚本 {script_name} 执行超时")
        return None
    except Exception as e:
        safe_print(f"执行脚本时出错: {e}")
        return None


def save_fund_data_individually(portfolios):
    """
    按条目分开保存基金数据到本地CSV文件，保存原始数据（未经时间对齐处理）
    只保存来自脚本（DataFetcher）的数据，跳过本地文件数据源
    :param portfolios: 组合数据字典
    :return: 保存状态信息
    """
    saved_files = []
    errors = []
    skipped_files = []  # 记录跳过的本地文件
    
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
                
            original_df = None  # 确保我们使用原始数据
            source_info = ""
            
            try:
                # 处理脚本数据源 - 重新获取原始数据
                if data_source.startswith('script:'):
                    script_name = data_source[7:]
                    if fund_code:
                        safe_print(f"正在获取原始数据：{fund_name} ({fund_code})")
                        # 直接从脚本获取新的原始数据，不使用任何缓存
                        original_df = execute_custom_script(script_name, fund_code)
                        source_info = f"{script_name}_{fund_code}"
                    else:
                        continue
                        
                # 跳过CSV文件数据源 - 本地数据不需要再次保存
                elif os.path.exists(data_source):
                    safe_print(f"跳过本地数据源：{fund_name} (来源: {data_source})")
                    skipped_files.append({
                        'fund_name': fund_name,
                        'fund_code': fund_code or 'N/A',
                        'source_file': os.path.basename(data_source),
                        'reason': '数据来源已是本地文件'
                    })
                    continue  # 跳过本地文件数据源
                
                if original_df is not None and not original_df.empty:
                    # 生成文件名
                    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
                    safe_fund_name = "".join(c for c in fund_name if c.isalnum() or c in (' ', '-', '_')).strip()
                    
                    # 命名：基金数据_[基金名称]_[数据源]_[时间戳]
                    if fund_code:
                        filename = f"基金数据_{safe_fund_name}_{fund_code}_{timestamp}.csv"
                    else:
                        filename = f"基金数据_{safe_fund_name}_{source_info}_{timestamp}.csv"
                    
                    # 确保数据格式标准化，但不进行时间对齐或截取
                    if 'time' in original_df.columns and 'nav' in original_df.columns:
                        # 已经是标准格式，保持原样
                        final_df = original_df.copy()
                    elif 'FSRQ' in original_df.columns and 'DWJZ' in original_df.columns:
                        # 转换为标准格式，但保留所有数据
                        final_df = original_df.rename(columns={'FSRQ': 'time', 'DWJZ': 'nav'})
                        final_df = final_df[['time', 'nav']]
                    else:
                        # 尝试猜测列名
                        time_col = next((col for col in original_df.columns if 'time' in col.lower() or 'date' in col.lower()), None)
                        value_col = next((col for col in original_df.columns if col != time_col and original_df[col].dtype in ['float64', 'int64']), None)
                        if time_col and value_col:
                            final_df = original_df[[time_col, value_col]].copy()
                            final_df.columns = ['time', 'nav']
                        else:
                            final_df = original_df.copy()
                    
                    # 确保时间列格式，但不截取数据
                    if 'time' in final_df.columns:
                        final_df['time'] = pd.to_datetime(final_df['time'])
                        # 按时间排序，但保留所有数据点
                        final_df = final_df.sort_values('time').reset_index(drop=True)
                    
                    # 保存完整的原始数据
                    final_df.to_csv(filename, index=False, encoding='utf-8-sig')
                    
                    safe_print(f"已保存原始数据：{filename}，包含 {len(final_df)} 行完整数据")
                    
                    saved_files.append({
                        'filename': filename,
                        'fund_name': fund_name,
                        'fund_code': fund_code or 'N/A',
                        'source': source_info,
                        'share': fund_share,
                        'from_portfolio': portfolio_name,
                        'rows': len(final_df)
                    })
                    
            except Exception as e:
                errors.append(f"{fund_name} ({fund_code or 'N/A'}): {str(e)}")
    
    return saved_files, errors, skipped_files
