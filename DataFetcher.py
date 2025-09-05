#!/usr/bin/env python3
"""
改进的基金数据获取脚本
用于被Web应用调用，返回标准化的CSV格式数据
"""
import requests
import re
import json
import pandas as pd
import sys
import argparse
from datetime import datetime
import io

class FundDataFetcher:
    def __init__(self, fund_code: str):
        """
        :param fund_code: 基金代码（字符串格式）
        """
        self.root_url = 'http://api.fund.eastmoney.com/f10/lsjz'
        self.fund_code = fund_code
        self.session = requests.session()
        self.headers = {
            'Host': 'api.fund.eastmoney.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': f'http://fundf10.eastmoney.com/jjjz_{self.fund_code}.html',
        }

    def get_fund_info(self):
        """获取基金基本信息"""
        search_url = 'https://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx'
        params = {
            "callback": "jQuery18309325043269513131_1618730779404",
            "m": 1,
            "key": self.fund_code,
        }
        try:
            res = self.session.get(search_url, params=params, timeout=10)
            content = self._format_content(res.text)
            if content and 'Datas' in content and len(content['Datas']) > 0:
                fund_data = content['Datas'][0]
                return {
                    'name': fund_data.get('NAME', '未知基金'),
                    'type': fund_data.get('FundBaseInfo', {}).get('FTYPE', '未知类型'),
                    'manager': fund_data.get('FundBaseInfo', {}).get('JJJL', '未知经理')
                }
        except Exception as e:
            print(f"Error getting fund info: {e}", file=sys.stderr)
        return None

    @staticmethod
    def _format_content(content):
        """格式化返回内容"""
        try:
            params = re.compile(r'jQuery.+?\((.*)\)')
            matches = params.findall(content)
            if matches:
                return json.loads(matches[0])
        except Exception:
            pass
        return None

    def get_page_data(self, page_index):
        """获取指定页的数据"""
        params = {
            'callback': 'jQuery18308909743577296265_1618718938738',
            'fundCode': self.fund_code,
            'pageIndex': page_index,
            'pageSize': 20,
        }
        try:
            res = self.session.get(url=self.root_url, headers=self.headers, params=params, timeout=10)
            return self._format_content(res.text)
        except Exception as e:
            print(f"Error getting page {page_index}: {e}", file=sys.stderr)
            return None

    def fetch_all_data(self, max_pages=50):
        """获取所有历史净值数据"""
        all_data = []
        page_index = 1
        
        while page_index <= max_pages:
            page_data = self.get_page_data(page_index)
            
            if not page_data or 'Data' not in page_data:
                break
                
            lsjz_list = page_data['Data'].get('LSJZList', [])
            if not lsjz_list:
                break
                
            all_data.extend(lsjz_list)
            
            # 如果这一页的数据少于20条，说明已经是最后一页
            if len(lsjz_list) < 20:
                break
                
            page_index += 1
            
        return all_data

    def process_data(self):
        """处理数据并返回标准化的DataFrame"""
        print(f"正在获取基金 {self.fund_code} 的数据...", file=sys.stderr)
        
        # 获取基金信息
        fund_info = self.get_fund_info()
        if not fund_info:
            raise ValueError(f"无法获取基金 {self.fund_code} 的信息，请检查基金代码是否正确")
        
        print(f"基金名称: {fund_info['name']}", file=sys.stderr)
        
        # 获取历史数据
        raw_data = self.fetch_all_data()
        if not raw_data:
            raise ValueError(f"无法获取基金 {self.fund_code} 的历史数据")
        
        # 转换为DataFrame
        df = pd.DataFrame(raw_data)
        
        # 数据清洗和标准化
        if 'FSRQ' in df.columns and 'DWJZ' in df.columns:
            # 选择需要的列
            result_df = df[['FSRQ', 'DWJZ']].copy()
            
            # 重命名列为标准格式
            result_df.columns = ['time', 'nav']
            
            # 转换数据类型
            result_df['time'] = pd.to_datetime(result_df['time'])
            result_df['nav'] = pd.to_numeric(result_df['nav'], errors='coerce')
            
            # 删除无效数据
            result_df = result_df.dropna()
            
            # 按时间排序（从早到晚）
            result_df = result_df.sort_values('time').reset_index(drop=True)
            
            print(f"成功获取 {len(result_df)} 条数据", file=sys.stderr)
            return result_df
        else:
            raise ValueError("数据格式不正确，缺少必要的列")

def main():
    """主函数 - 命令行接口"""
    parser = argparse.ArgumentParser(description='获取基金历史净值数据')
    parser.add_argument('fund_code', help='基金代码')
    parser.add_argument('--output', '-o', help='输出文件路径（默认输出到标准输出）')
    parser.add_argument('--format', choices=['csv', 'json'], default='csv', help='输出格式')
    
    args = parser.parse_args()
    
    try:
        fetcher = FundDataFetcher(args.fund_code)
        df = fetcher.process_data()
        
        if args.format == 'csv':
            if args.output:
                df.to_csv(args.output, index=False)
                print(f"数据已保存到 {args.output}", file=sys.stderr)
            else:
                # 输出到标准输出
                csv_string = df.to_csv(index=False)
                print(csv_string, end='')
        elif args.format == 'json':
            if args.output:
                df.to_json(args.output, orient='records', date_format='iso')
                print(f"数据已保存到 {args.output}", file=sys.stderr)
            else:
                print(df.to_json(orient='records', date_format='iso'))
                
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
