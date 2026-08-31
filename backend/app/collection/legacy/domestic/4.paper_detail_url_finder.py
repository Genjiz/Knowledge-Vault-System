"""
论文详情页URL获取器
根据期刊名称、年份、期数获取论文详情页链接
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import time
import random
import os
from datetime import datetime

class PaperDetailUrlFinder:
    """论文详情页URL查找器"""
    
    def __init__(self, min_delay=1, max_delay=3):
        """
        初始化查找器
        
        Args:
            min_delay (int): 最小延迟秒数
            max_delay (int): 最大延迟秒数
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Accept-Encoding': 'gzip, deflate, br'
        }
    
    def _random_delay(self):
        """随机延迟"""
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)
    
    def extract_paper_detail_urls_by_journal_info(self, journal_name, year, issue):
        """
        根据期刊名称、年份、期数获取论文详情页URL
        
        Args:
            journal_name (str): 期刊名称
            year (int): 年份
            issue (int): 期数
            
        Returns:
            bool: 是否成功处理
        """
        print(f"🔗 开始获取论文详情页URL...")
        print(f"   期刊: {journal_name}")
        print(f"   年份: {year}")
        print(f"   期数: {issue}")
        
        try:
            # 构建JSON文件路径
            # 修改：查找项目根目录（脚本所在目录的父级）
            project_root = os.path.dirname(os.path.dirname(__file__))
            json_file_path = os.path.join(
                project_root, 
                journal_name, 
                str(year), 
                f"{journal_name}_{year}_{issue}.json"
            )
            
            # 检查文件是否存在
            if not os.path.exists(json_file_path):
                print(f"❌ JSON文件不存在: {json_file_path}")
                return False
            
            # 读取JSON文件
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 获取期号页面URL
            issue_url = data.get('source_url', '')
            if not issue_url:
                print(f"❌ JSON文件中未找到source_url")
                return False
            
            print(f"   期号页面: {issue_url}")
            
            # 获取期号页面内容
            self._random_delay()
            response = requests.get(issue_url, headers=self.headers, timeout=15)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                print(f"❌ 获取页面失败，状态码: {response.status_code}")
                return False
            
            # 解析页面，查找论文链接
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 查找所有可能的论文链接
            paper_links = self._find_paper_links(soup)
            print(f"   页面中发现 {len(paper_links)} 个论文链接")
            
            # 为每篇论文匹配详情页URL
            papers = data.get('papers', [])
            print(f"   JSON文件中包含 {len(papers)} 篇论文")
            
            # 匹配论文标题和链接
            for paper in papers:
                paper_title = paper.get('title', '')
                matched_info = self._match_single_title_to_url(paper_title, paper_links)
                
                if matched_info:
                    paper['detail_url'] = matched_info['detail_url']
                    paper['matched_text'] = matched_info['matched_text']
                    paper['similarity'] = matched_info['similarity']
                    print(f"   ✅ 匹配: {paper_title[:30]}... -> {matched_info['detail_url']}")
                else:
                    print(f"   ❌ 未找到匹配: {paper_title[:30]}...")
            
            # 更新JSON文件
            data['papers'] = papers
            data['update_time'] = datetime.now().isoformat()
            
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 成功更新JSON文件: {json_file_path}")
            return True
            
        except Exception as e:
            print(f"❌ 处理论文详情页URL失败: {e}")
            return False
    
    def _find_paper_links(self, soup):
        """在页面中查找所有论文链接"""
        paper_links = []
        
        # 主要方法: 查找包含 openDetail 的 onclick 事件
        onclick_elements = soup.find_all('a', attrs={'onclick': True})
        for element in onclick_elements:
            onclick = element.get('onclick', '')
            if 'openDetail' in onclick and 'articleinfo' in onclick:
                title_text = element.get_text(strip=True)
                if title_text and len(title_text) > 10:
                    # 从onclick事件中提取URL
                    extracted_url = self._extract_url_from_onclick(onclick)
                    if extracted_url:
                        paper_links.append({
                            'title': title_text,
                            'url': extracted_url,
                            'full_url': self._normalize_url(extracted_url)
                        })
        
        return paper_links
    
    def _extract_url_from_onclick(self, onclick_text):
        """从onclick事件中提取URL"""
        # 主要模式: openDetail('/Literature/articleinfo?id=QBXB2024012001&type=journalArticle&typename=...')
        pattern = r"openDetail\(['\"]([^'\"]+)['\"]\)"
        match = re.search(pattern, onclick_text)
        if match:
            return match.group(1)
        
        return None
    
    def _normalize_url(self, url):
        """标准化URL"""
        if not url:
            return ''
        
        # 如果是相对URL，补充域名
        if url.startswith('/'):
            full_url = f"https://www.ncpssd.cn{url}"
        elif url.startswith('http'):
            full_url = url
        else:
            full_url = f"https://www.ncpssd.cn/{url}"
        
        # 对URL进行编码处理，避免中文字符问题
        try:
            from urllib.parse import urlparse, urlunparse, quote
            parsed = urlparse(full_url)
            # 对路径和查询参数进行编码
            encoded_path = quote(parsed.path, safe='/')
            encoded_query = quote(parsed.query, safe='&=')
            encoded_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                encoded_path,
                parsed.params,
                encoded_query,
                parsed.fragment
            ))
            return encoded_url
        except Exception:
            # 如果编码失败，返回原始URL
            return full_url
    
    def _match_single_title_to_url(self, paper_title, paper_links):
        """为单个论文标题匹配URL"""
        best_match = None
        best_score = 0
        
        # 清理标题用于比较
        clean_title = self._clean_title_for_matching(paper_title)
        
        for link in paper_links:
            link_title = self._clean_title_for_matching(link['title'])
            
            # 计算相似度
            similarity = self._calculate_similarity(clean_title, link_title)
            
            if similarity > best_score and similarity > 0.8:  # 相似度阈值
                best_score = similarity
                best_match = link
        
        if best_match:
            return {
                'detail_url': best_match['full_url'],
                'matched_text': best_match['title'],
                'similarity': best_score
            }
        
        return None
    
    def _clean_title_for_matching(self, title):
        """清理标题用于匹配"""
        if not title:
            return ''
        
        # 移除多余空格和特殊字符
        cleaned = re.sub(r'\s+', ' ', title.strip())
        cleaned = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', '', cleaned)
        return cleaned.lower()
    
    def _calculate_similarity(self, title1, title2):
        """计算两个标题的相似度"""
        if not title1 or not title2:
            return 0
        
        # 简单的相似度计算：检查title1是否包含在title2中或vice versa
        if title1 in title2 or title2 in title1:
            return min(len(title1), len(title2)) / max(len(title1), len(title2))
        
        # 计算共同字符比例
        common_chars = 0
        for char in title1:
            if char in title2:
                common_chars += 1
        
        return common_chars / max(len(title1), len(title2))

def main():
    """命令行调用功能"""
    import sys
    
    if len(sys.argv) != 4:
        print("使用方法: python 4.paper_detail_url_finder.py 期刊名称 年份 期数")
        print("示例: python 4.paper_detail_url_finder.py 情报学报 2024 12")
        return
    
    journal_name = sys.argv[1]
    try:
        year = int(sys.argv[2])
        issue = int(sys.argv[3])
    except ValueError:
        print("错误：年份和期数必须是数字")
        return
    
    print(f"根据期刊信息获取论文详情页URL: {journal_name} {year}年第{issue}期")
    
    finder = PaperDetailUrlFinder()
    success = finder.extract_paper_detail_urls_by_journal_info(journal_name, year, issue)
    
    if success:
        print(f"\n✅ 成功处理论文详情页URL")
    else:
        print(f"\n❌ 处理论文详情页URL失败")
        print("可能的原因:")
        print("  1. JSON文件不存在")
        print("  2. 期刊页面URL无效")
        print("  3. 页面结构发生变化")
        print("  4. 网络连接问题")

if __name__ == "__main__":
    main()