import requests
from bs4 import BeautifulSoup
import re
import json
import os
from datetime import datetime

class PaperTitleExtractor:
    """论文标题提取器 - 从URL获取论文标题信息"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive'
        }
        
        # 加载期号URL缓存
        self.issue_url_cache = self._load_issue_url_cache()
    
    def _load_issue_url_cache(self):
        """加载期号URL缓存"""
        try:
            issue_cache_file = os.path.join(os.path.dirname(__file__), 'issue_url_cache.json')
            if os.path.exists(issue_cache_file):
                with open(issue_cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"加载期号URL缓存失败: {e}")
            return {}
    
    def get_issue_url(self, journal_name, year, issue):
        """
        根据期刊名称、年份、期数获取期号URL
        
        Args:
            journal_name (str): 期刊名称，如"情报学报"
            year (int): 年份，如 2024
            issue (int): 期数，如 12
            
        Returns:
            str: 期号URL，或 None
        """
        cache_key = f"{journal_name}_{year}_{issue}"
        
        # 重新加载缓存以确保获取最新数据
        self.issue_url_cache = self._load_issue_url_cache()
        
        if cache_key in self.issue_url_cache:
            url = self.issue_url_cache[cache_key]['url']
            print(f"✅ 从缓存中找到 {journal_name} {year}年第{issue}期的URL")
            return url
        else:
            print(f"❌ 未在缓存中找到 {journal_name} {year}年第{issue}期的URL")
            print(f"可用的期号: {list(self.issue_url_cache.keys())}")
            return None
    
    def extract_papers_by_journal_info(self, journal_name, year, issue):
        """
        根据期刊信息提取论文
        
        Args:
            journal_name (str): 期刊名称
            year (int): 年份
            issue (int): 期数
            
        Returns:
            list: 论文信息列表
        """
        print(f"根据期刊信息提取论文: {journal_name} {year}年第{issue}期")
        
        # 获取期号URL
        url = self.get_issue_url(journal_name, year, issue)
        if not url:
            return []
        
        # 提取论文信息
        papers = self.extract_papers(url)
        
        # 保存论文信息（按指定格式）
        if papers:
            saved_path = self.save_papers(
                papers, 
                url=url,
                journal_name=journal_name,
                year=year,
                issue=issue
            )
            print(f"✅ 已保存到: {saved_path}")
        
        return papers
    
    def extract_papers(self, url):
        """
        从URL提取论文信息
        
        Args:
            url (str): 期刊页面URL
            
        Returns:
            list: 论文信息列表，每个元素包含title, authors, pages, issue等字段
        """
        try:
            print(f"正在获取论文信息: {url}")
            
            response = requests.get(url, headers=self.headers, timeout=15)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                print(f"访问失败，状态码: {response.status_code}")
                return []
            
            return self._parse_papers(response.text)
            
        except Exception as e:
            print(f"提取论文信息失败: {e}")
            return []
    
    def _parse_papers(self, content):
        """解析网页内容，提取论文信息"""
        papers = []
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text()
        
        # 按行分割并处理
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        current_issue = ""
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # 识别期号信息
            if self._is_issue_line(line):
                current_issue = line
                i += 1
                continue
            
            # 识别论文标题
            if self._is_likely_title(line):
                title = line
                authors = ""
                pages = ""
                
                # 查看后续行是否包含作者和页码信息
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if self._is_author_line(next_line):
                        authors = next_line
                        i += 1
                        
                        # 查看是否有页码信息
                        if i + 1 < len(lines):
                            page_line = lines[i + 1]
                            if self._is_page_line(page_line):
                                pages = page_line.strip('()')
                                i += 1
                
                paper_info = {
                    'title': title,
                    'authors': authors,
                    'pages': pages,
                    'issue': current_issue,
                    'extract_time': datetime.now().isoformat()
                }
                papers.append(paper_info)
            
            i += 1
        
        # 清理和去重
        return self._clean_papers(papers)
    
    def _is_issue_line(self, line):
        """判断是否是期号信息行"""
        issue_patterns = [
            r'\d{4}年\s*第\d+期',
            r'\d{4}\s*/\s*\d+',
        ]
        
        for pattern in issue_patterns:
            if re.search(pattern, line):
                return True
        return False
    
    def _is_likely_title(self, text):
        """判断文本是否可能是论文标题"""
        # 基本长度检查
        if len(text) < 8 or len(text) > 150:
            return False
        
        # 中文字符检查
        chinese_chars = len(re.findall(r'[\u4e00-\u9fa5]', text))
        if chinese_chars < 5:
            return False
        
        # 排除明显不是标题的内容
        exclude_patterns = [
            r'^http', r'^www', r'版权', r'登录', r'注册', r'搜索', r'导航', r'首页',
            r'^\d{4}年', r'^\d+月', r'^\d+期', r'^第\d+', r'情报学报', r'现代情报',
            r'国家哲学社会科学', r'中国社会科学院', r'主管单位', r'主办单位', 
            r'出版社', r'地址：', r'ISSN', r'ISBN', r'国际标准刊号', r'国内统一刊号',
            r'扫一扫', r'微信', r'小程序', r'=.*=', r'CN \d+-\d+', r'邮发代号',
            r'创刊时间', r'出版周期', r'主编', r'编辑部', r'电话', r'邮箱'
        ]
        
        for pattern in exclude_patterns:
            if re.search(pattern, text):
                return False
        
        # 标题不应该包含特殊符号
        if re.search(r'[\[\]()]', text):
            return False
        
        return True
    
    def _is_author_line(self, line):
        """判断是否是作者信息行"""
        # 作者行通常包含方括号标注
        return bool(re.search(r'\[[\d,，\s]+\]', line))
    
    def _is_page_line(self, line):
        """判断是否是页码信息行"""
        # 页码行格式如 (123-456)
        return bool(re.match(r'^\(\d+-\d+\)$', line.strip()))
    
    def _clean_papers(self, papers):
        """清理论文列表，去重和过滤"""
        seen_titles = set()
        cleaned_papers = []
        
        for paper in papers:
            title = paper['title'].strip()
            
            # 去重
            if title in seen_titles:
                continue
            
            # 检查是否有作者或页码信息（核心判断）
            has_author_info = bool(paper.get('authors', '').strip())
            has_page_info = bool(paper.get('pages', '').strip())
            
            # 如果没有作者和页码信息，说明不是论文标题
            if not (has_author_info or has_page_info):
                continue
            
            # 进一步过滤明显不是论文的内容
            if len(title) < 10:
                continue
            
            # 清理标题中的多余空格
            paper['title'] = re.sub(r'\s+', ' ', title)
            
            seen_titles.add(title)
            cleaned_papers.append(paper)
        
        return cleaned_papers
    
    def save_papers(self, papers, filename=None, url=None, journal_name=None, year=None, issue=None):
        """
        保存论文信息到JSON文件
        
        Args:
            papers (list): 论文信息列表
            filename (str, optional): 保存文件名
            url (str, optional): 来源URL
            journal_name (str, optional): 期刊名称
            year (int, optional): 年份
            issue (int, optional): 期数
            
        Returns:
            str: 保存的文件路径
        """
        # 优先使用指定的期刊信息创建文件夹结构：/期刊/年份
        if journal_name and year:
            # 修改：保存到项目根目录（脚本所在目录的父级）
            base_dir = os.path.dirname(os.path.dirname(__file__))
            journal_dir = os.path.join(base_dir, journal_name)
            year_dir = os.path.join(journal_dir, str(year))
            
            # 创建文件夹（如果不存在）
            os.makedirs(year_dir, exist_ok=True)
            print(f"📁 确保文件夹存在: {year_dir}")
            
            # 生成文件名：期刊名称_年份_期数.json
            if not filename:
                filename = f"{journal_name}_{year}_{issue}.json" if issue else f"{journal_name}_{year}.json"
            
            # 完整文件路径
            full_path = os.path.join(year_dir, filename)
        else:
            # 如果没有期刊和年份信息，使用默认方式
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"论文信息_{timestamp}.json"
            full_path = filename
        
        result = {
            'journal_name': journal_name,
            'year': year,
            'issue': issue,
            'source_url': url,
            'extract_time': datetime.now().isoformat(),
            'total_count': len(papers),
            'papers': papers
        }
        
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"论文信息已保存到: {full_path}")
        return full_path
    
    def print_papers(self, papers):
        """打印论文信息"""
        if not papers:
            print("未提取到论文信息")
            return
        
        print(f"\n提取到 {len(papers)} 篇论文:")
        print("=" * 80)
        
        for i, paper in enumerate(papers, 1):
            print(f"{i}. 标题: {paper['title']}")
            if paper.get('authors'):
                print(f"   作者: {paper['authors']}")
            if paper.get('pages'):
                print(f"   页码: {paper['pages']}")
            if paper.get('issue'):
                print(f"   期号: {paper['issue']}")
            print("-" * 80)

def main():
    """命令行调用功能"""
    import sys
    
    if len(sys.argv) != 4:
        print("使用方法: python 3.paper_title_extractor.py 期刊名称 年份 期数")
        print("示例: python 3.paper_title_extractor.py 情报学报 2024 12")
        return
    
    journal_name = sys.argv[1]
    try:
        year = int(sys.argv[2])
        issue = int(sys.argv[3])
    except ValueError:
        print("错误：年份和期数必须是数字")
        return
    
    print(f"根据期刊信息提取论文: {journal_name} {year}年第{issue}期")
    
    extractor = PaperTitleExtractor()
    papers = extractor.extract_papers_by_journal_info(journal_name, year, issue)
    
    if papers:
        print(f"✅ 成功提取到 {len(papers)} 篇论文:")
        extractor.print_papers(papers)
    else:
        print(f"❌ 未提取到论文信息")
        print("可能的原因:")
        print("  1. 期刊信息不在缓存中")
        print("  2. URL无效或无法访问")
        print("  3. 页面结构发生变化")
        print("  4. 网络连接问题")

if __name__ == "__main__":
    main()