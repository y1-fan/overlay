#!/usr/bin/env python3
"""
Improved fund data fetcher script
Called by Web application, returns standardized CSV format data
"""
import requests
import re
import json
import pandas as pd
import sys
import argparse
from datetime import datetime
import io

def safe_print(*args):
    """Safe print function to handle Windows encoding issues"""
    try:
        message = ' '.join(str(arg) for arg in args)
        # Ensure only ASCII characters
        safe_message = ''.join(char if ord(char) < 128 else '?' for char in message)
        if safe_message:
            print(safe_message[:200], file=sys.stderr)  # Limit length
    except Exception:
        print("Print error", file=sys.stderr)

class FundDataFetcher:
    def __init__(self, fund_code: str):
        """
        :param fund_code: Fund code (string format)
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
        """Get fund basic information"""
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
                    'name': fund_data.get('NAME', 'Unknown Fund'),
                    'type': fund_data.get('FundBaseInfo', {}).get('FTYPE', 'Unknown Type'),
                    'manager': fund_data.get('FundBaseInfo', {}).get('JJJL', 'Unknown Manager')
                }
        except Exception as e:
            safe_print(f"Error getting fund info: {e}")
        return None

    @staticmethod
    def _format_content(content):
        """Format return content"""
        try:
            params = re.compile(r'jQuery.+?\((.*)\)')
            matches = params.findall(content)
            if matches:
                return json.loads(matches[0])
        except Exception:
            pass
        return None

    def get_page_data(self, page_index):
        """Get data for specified page"""
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
            safe_print(f"Error getting page {page_index}: {e}")
            return None

    def fetch_all_data(self, max_pages=50):
        """Get all historical NAV data"""
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
            
            # If this page has less than 20 records, it's the last page
            if len(lsjz_list) < 20:
                break
                
            page_index += 1
            
        return all_data

    def process_data(self):
        """Process data and return standardized DataFrame"""
        safe_print(f"Getting fund {self.fund_code} data...")
        
        # Get fund information
        fund_info = self.get_fund_info()
        if not fund_info:
            raise ValueError(f"Cannot get fund {self.fund_code} info, please check fund code")
        
        safe_print(f"Fund name: {fund_info['name']}")
        
        # Get historical data
        raw_data = self.fetch_all_data()
        if not raw_data:
            raise ValueError(f"Cannot get fund {self.fund_code} historical data")
        
        # Convert to DataFrame
        df = pd.DataFrame(raw_data)
        
        # Data cleaning and standardization
        if 'FSRQ' in df.columns and 'DWJZ' in df.columns:
            # Select needed columns
            result_df = df[['FSRQ', 'DWJZ']].copy()
            
            # Rename columns to standard format
            result_df.columns = ['time', 'nav']
            
            # Convert data types
            result_df['time'] = pd.to_datetime(result_df['time'])
            result_df['nav'] = pd.to_numeric(result_df['nav'], errors='coerce')
            
            # Remove invalid data
            result_df = result_df.dropna()
            
            # Sort by time (earliest to latest)
            result_df = result_df.sort_values('time').reset_index(drop=True)
            
            safe_print(f"Successfully got {len(result_df)} records")
            return result_df
        else:
            raise ValueError("Data format incorrect, missing required columns")

def main():
    """Main function - command line interface"""
    parser = argparse.ArgumentParser(description='Get fund historical NAV data')
    parser.add_argument('fund_code', help='Fund code')
    parser.add_argument('--output', '-o', help='Output file path (default output to stdout)')
    parser.add_argument('--format', choices=['csv', 'json'], default='csv', help='Output format')
    
    args = parser.parse_args()
    
    try:
        fetcher = FundDataFetcher(args.fund_code)
        df = fetcher.process_data()
        
        if args.format == 'csv':
            if args.output:
                df.to_csv(args.output, index=False)
                safe_print(f"Data saved to {args.output}")
            else:
                # Output to stdout
                csv_string = df.to_csv(index=False)
                print(csv_string, end='')
        elif args.format == 'json':
            if args.output:
                df.to_json(args.output, orient='records', date_format='iso')
                safe_print(f"Data saved to {args.output}")
            else:
                print(df.to_json(orient='records', date_format='iso'))
                
    except Exception as e:
        safe_print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
