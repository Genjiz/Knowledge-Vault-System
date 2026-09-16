import requests
from bs4 import BeautifulSoup
import json
import os
import re
import time
import random
import urllib.parse
from urllib.parse import urljoin, urlparse, parse_qs

class IssueUrlFinder:
    """期号URL查找器 - 完全基于页面内容获取期号URL，不依赖任何预设模式"""
    
    def __init__(self, min_delay=1, max_delay=3, session=None):
        """初始化爬虫
        
        Args:
            min_delay: 最小请求间隔（秒）
            max_delay: 最大请求间隔（秒）
        """
        self.base_url = "https://www.ncpssd.cn"
        self.session = session or requests.Session()
        self.session.trust_env = False
        
        # 反爬虫防护：请求频率控制
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request_time = 0
        
        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.ncpssd.cn/'
        })

        # 加载已知期刊URL缓存文件（仅用于获取期刊首页URL）
        self.known_journals_file = os.path.join(os.path.dirname(__file__), 'journal_url_cache.json')
        self.known_journals = self._load_known_journals()
        
        # 加载期刊期号URL缓存文件
        self.issue_cache_file = os.path.join(os.path.dirname(__file__), 'issue_url_cache.json')
        self.issue_cache = self._load_issue_cache()

    def _coerce_int(self, value, fallback=0):
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback
    
    def _wait_between_requests(self):
        """在请求之间等待，防止被反爬虫系统检测"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_delay:
            delay = random.uniform(self.min_delay, self.max_delay)
            print(f"🕰️ 防爬虫等待 {delay:.1f} 秒...")
            time.sleep(delay)
        
        self.last_request_time = time.time()
    
    def _load_known_journals(self):
        """加载已知期刊数据"""
        try:
            if os.path.exists(self.known_journals_file):
                with open(self.known_journals_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"加载期刊数据失败: {e}")
            return {}
    
    def _load_issue_cache(self):
        """加载期号URL缓存"""
        try:
            if os.path.exists(self.issue_cache_file):
                with open(self.issue_cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"加载期号缓存失败: {e}")
            return {}
    
    def _save_issue_cache(self):
        """保存期号URL缓存"""
        try:
            with open(self.issue_cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.issue_cache, f, ensure_ascii=False, indent=2)
            print(f"💾 期号URL缓存已保存到: {self.issue_cache_file}")
        except Exception as e:
            print(f"保存期号缓存失败: {e}")
    
    def _get_cache_key(self, journal_name, year, issue):
        """生成缓存键值"""
        return f"{str(journal_name).strip()}_{self._coerce_int(year)}_{self._coerce_int(issue)}"
    
    def _get_cached_issue_url(self, journal_name, year, issue):
        """从缓存中获取期号URL"""
        cache_key = self._get_cache_key(journal_name, year, issue)
        return self.issue_cache.get(cache_key)
    
    def _cache_issue_url(self, journal_name, year, issue, result):
        """将期号URL保存到缓存"""
        cache_key = self._get_cache_key(journal_name, year, issue)
        self.issue_cache[cache_key] = result
        self._save_issue_cache()
    
    def get_issue_url(self, journal_name, year, issue):
        """
        获取指定期刊的URL
        
        Args:
            journal_name: 期刊名称（如"情报学报"）
            year: 年份（如 2024）
            issue: 期号（如 12）
            
        Returns:
            dict: 包含 URL 等信息的字典，或 None
        """

        year = self._coerce_int(year)
        issue = self._coerce_int(issue)
        journal_name = str(journal_name).strip()

        # 重新加载已知期刊数据缓存文件（仅用于获取期刊首页URL）
        self.known_journals = self._load_known_journals()
        # 重新加载期刊期号URL缓存文件
        self.issue_cache = self._load_issue_cache()

        cached_result = self._get_cached_issue_url(journal_name, year, issue)
        if cached_result:
            print(f"💾 从缓存中获取: {journal_name} {year}年第{issue}期")
            return cached_result

        # 新增：优先走站内检索直达，避免依赖旧版Ajax期号列表结构
        print(f"🔎 先尝试站内检索定位期号URL...")
        search_result = self.find_issue_url_by_search(journal_name, year, issue)
        if search_result:
            self._cache_issue_url(journal_name, year, issue, search_result)
            print("✅ 通过站内检索定位到期号URL")
            return search_result
        
        # 如果还是没有，通过页面分析获取
        print(f"🔍 缓存中未找到，开始页面分析...")
        result = self.find_issue_url_by_page_analysis(journal_name, year, issue)
        
        # 如果找到了，保存到缓存
        if result:
            self._cache_issue_url(journal_name, year, issue, result)
            print(f"✅ 已将结果保存到缓存")
        
        return result

    def find_issue_url_by_search(self, journal_name, year, issue):
        """通过站内检索直接定位目标期号URL"""
        target_journal_name = str(journal_name).strip()
        queries = []
        for keyword in [
            f"{target_journal_name} {year} 第{issue}期",
            f"{target_journal_name} {year}/{issue}",
            f"{target_journal_name} {year}",
            target_journal_name,
            str(journal_name).strip(),
        ]:
            keyword = keyword.strip()
            if keyword and keyword not in queries:
                queries.append(keyword)

        best_candidate = None
        for query in queries:
            soup = self._fetch_search_page(query)
            if soup is None:
                continue

            candidates = self._extract_issue_candidates_from_search_page(
                soup=soup,
                target_journal_name=target_journal_name,
                target_year=year,
                target_issue=issue,
            )
            if not candidates:
                continue

            top_candidate = max(candidates, key=lambda item: item["score"])
            if best_candidate is None or top_candidate["score"] > best_candidate["score"]:
                best_candidate = top_candidate

            # 命中期刊+年份+期号后直接返回，不再继续放大请求
            if top_candidate["journal_match"] and top_candidate["year_match"] and top_candidate["issue_match"]:
                break

        if not best_candidate:
            return None

        if not (best_candidate["journal_match"] and best_candidate["issue_match"]):
            # 至少需要期刊+期号同时命中，避免误命中其它期刊页
            return None

        return {
            "url": best_candidate["url"],
            "params": best_candidate.get("params"),
            "text": best_candidate["text"],
            "method": "站内检索匹配",
        }

    def _fetch_search_page(self, keyword):
        """请求站内检索结果页"""
        try:
            keyword_encoded = urllib.parse.quote(str(keyword).strip())
            search_url = (
                f"{self.base_url}/journal/list"
                f"?e=s%3D{keyword_encoded}&langType=1&keyword={keyword_encoded}"
            )
            print(f"  检索URL: {search_url}")
            self._wait_between_requests()
            response = self.session.get(search_url, timeout=15)
            response.encoding = "utf-8"
            if response.status_code != 200:
                print(f"  ❌ 检索请求失败，状态码: {response.status_code}")
                return None
            return BeautifulSoup(response.text, "html.parser")
        except Exception as exc:
            print(f"  ❌ 检索请求异常: {exc}")
            return None

    def _extract_issue_candidates_from_search_page(self, soup, target_journal_name, target_year, target_issue):
        """从检索页提取期号候选链接并评分"""
        candidates = []
        links = soup.find_all("a", href=re.compile(r"journal/(?:secure/)?details\?params="))
        if not links:
            return candidates

        for link in links:
            href = link.get("href") or ""
            link_text = (link.get_text() or "").strip()
            if not href:
                continue

            container = link.find_parent(["li", "div", "tr", "dd", "section"]) or link.parent
            context_text = " ".join(container.stripped_strings) if container else link_text
            combined_text = f"{link_text} {context_text}".strip()

            journal_match = False
            target_journal_name = str(target_journal_name).strip()
            if target_journal_name:
                journal_match = (
                    target_journal_name in link_text
                    or target_journal_name in context_text
                )

            year_match = bool(re.search(rf"(?<!\d){target_year}(?!\d)", combined_text))
            issue_match = self._match_issue_token(combined_text, target_issue)

            score = 0
            if journal_match:
                score += 120
            if year_match:
                score += 45
            if issue_match:
                score += 45
            if journal_match and year_match and issue_match:
                score += 120
            elif journal_match and issue_match:
                score += 60
            if "年第" in combined_text or "/" in combined_text:
                score += 5

            full_url = f"{self.base_url}{href}" if href.startswith("/") else href
            candidates.append(
                {
                    "url": full_url,
                    "params": self._extract_params_from_url(href),
                    "text": link_text or context_text[:64],
                    "score": score,
                    "journal_match": journal_match,
                    "year_match": year_match,
                    "issue_match": issue_match,
                }
            )

        return candidates

    def _match_issue_token(self, text, issue):
        """在文本中匹配目标期号"""
        if not text:
            return False

        issue = self._coerce_int(issue)
        if issue <= 0:
            return False

        patterns = [
            rf"第\s*0?{issue}\s*[期號号]",
            rf"(?<!\d)0?{issue}\s*[期號号](?!\d)",
            rf"/\s*0?{issue}(?!\d)",
            rf"[\s_（(]0?{issue}[\s_）)]",
        ]
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)
    
    def fetch_journal_page(self, journal_name):
        """获取期刊页面内容"""
        journal_name = str(journal_name).strip()
        if journal_name not in self.known_journals:
            print(f"❌ 未知期刊: {journal_name}")
            return None

        journal_param = self.known_journals[journal_name]

        # 尝试使用新的secure路径，如果原来的是journal/details
        journal_url = f"{self.base_url}/journal/secure/details?params={journal_param}"
        
        try:
            print(f"🔄 正在获取 {journal_name} 页面...")
            print(f"页面URL: {journal_url}")
            
            # 反爬虫防护：请求前等待
            self._wait_between_requests()
            
            response = self.session.get(journal_url, timeout=15)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                print(f"✅ 成功获取 {journal_name} 页面")
                
                return soup
            else:
                print(f"❌ 页面响应异常: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ 获取页面失败: {e}")
            return None
    
    def find_all_links_on_page(self, soup):
        """查找页面上的所有链接"""
        try:
            all_links = []
            
            # 查找所有链接
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href')
                text = link.get_text().strip()
                
                if href and text:
                    # 构造完整URL
                    full_url = urljoin(self.base_url, href) if href.startswith('/') else href
                    
                    link_info = {
                        'text': text,
                        'url': full_url,
                        'href': href,
                        'year': self._extract_year_from_text(text),
                        'issue': self._extract_issue_from_text(text)
                    }
                    
                    all_links.append(link_info)
            
            return all_links
            
        except Exception as e:
            print(f"❌ 链接分析失败: {e}")
            return []
    
    def find_year_issue_patterns_on_page(self, soup):
        """在页面上查找年份期号的文本模式"""
        try:
            print("🔍 查找页面上的年份期号文本模式...")
            
            # 获取页面所有文本内容
            page_text = soup.get_text()
            
            # 查找年份期号模式
            patterns = []
            
            # 查找 "YYYY年 第X期" 模式
            year_issue_pattern = r'(20\d{2})\s*年\s*第?\s*(\d+)\s*期'
            matches = re.findall(year_issue_pattern, page_text)
            for year, issue in matches:
                patterns.append({
                    'type': '年份期号',
                    'year': int(year),
                    'issue': int(issue),
                    'text': f"{year}年第{issue}期"
                })
            
            # 查找单独的年份
            year_pattern = r'(20\d{2})\s*年'
            year_matches = re.findall(year_pattern, page_text)
            for year in year_matches:
                patterns.append({
                    'type': '年份',
                    'year': int(year),
                    'issue': None,
                    'text': f"{year}年"
                })
            
            print(f"找到文本模式: {len(patterns)} 个")
            
            # 显示前10个模式
            for i, pattern in enumerate(patterns[:10]):
                print(f"  {i+1}. {pattern['type']}: {pattern['text']}")
            
            return patterns
            
        except Exception as e:
            print(f"❌ 文本模式分析失败: {e}")
            return []
    
    def find_issue_url_by_page_analysis(self, journal_name, year, issue):
        """通过页面分析查找期号URL"""
        try:
            print(f"\n🎯 通过页面分析查找 {journal_name} {year}年第{issue}期")
            
            # 方法1: 直接在页面上查找链接
            soup = self.fetch_journal_page(journal_name)
            if not soup:
                return None
            
            # 查找所有期号链接
            issue_links = self._find_all_issue_links_on_page(soup, journal_name)
            
            # 查找年份期号文本模式
            text_patterns = self.find_year_issue_patterns_on_page(soup)
            
            # 尝试匹配目标年份和期号
            for link in issue_links:
                if link['year'] == year and link['issue'] == issue:
                    print(f"✅ 精确匹配找到: {link['text']}")
                    return {
                        'url': link['url'],
                        'params': link.get('params'),
                        'text': link['text'],
                        'method': '页面链接精确匹配'
                    }
            
            # 方法2: 通过Ajax接口获取期号列表
            print(f"\n🔄 尝试通过Ajax接口获取期号列表...")
            ajax_html = self._get_issue_list_via_ajax(journal_name, year, soup)
            
            if ajax_html:
                ajax_issue_links = self._parse_issue_list_html(ajax_html)
                
                # 在Ajax结果中查找目标期号
                for link in ajax_issue_links:
                    if link['year'] == year and link['issue'] == issue:
                        print(f"✅ Ajax精确匹配找到: {link['text']}")
                        return {
                            'url': link['url'],
                            'params': link.get('params'),
                            'text': link['text'],
                            'method': 'Ajax接口精确匹配'
                        }
                    # 特殊处理：如果只有期号匹配但年份不匹配，但是请求的年份是正确的
                    elif link['issue'] == issue:
                        ajax_year = getattr(self, '_current_ajax_year', None)
                        if ajax_year == year:
                            print(f"✅ Ajax期号匹配找到 (使用请求年份): {link['text']} -> 调整为{year}年第{issue}期")
                            return {
                                'url': link['url'],
                                'params': link.get('params'),
                                'text': f"{year}年第{issue}期",
                                'method': 'Ajax接口期号匹配'
                            }
                
                # 显示Ajax返回的所有期号
                if ajax_issue_links:
                    print(f"\n📁 Ajax返回的期号列表:")
                    for i, link in enumerate(ajax_issue_links[:10]):
                        year_str = str(link['year']) if link['year'] else '未知'
                        issue_str = str(link['issue']) if link['issue'] else '未知'
                        print(f"    {i+1}. {year_str}年第{issue_str}期: {link['text'][:30]}")
            
            # 如果没有精确匹配，检查是否有部分匹配
            partial_matches = []
            for link in issue_links + (ajax_issue_links if ajax_html else []):
                if link['year'] == year or link['issue'] == issue:
                    partial_matches.append(link)
            
            if partial_matches:
                print(f"\n⚠️ 找到部分匹配的链接: {len(partial_matches)} 个")
                for match in partial_matches[:5]:
                    print(f"  - {match['text']} (年份:{match['year']}, 期号:{match['issue']})")
            
            # 检查文本模式中是否有目标期号信息
            target_pattern = None
            for pattern in text_patterns:
                if pattern['year'] == year and pattern['issue'] == issue:
                    target_pattern = pattern
                    break
            
            if target_pattern:
                print(f"\n✅ 在页面文本中找到目标期号信息: {target_pattern['text']}")
                print("但该信息不是以链接形式存在")
                
                # 可以尝试基于页面结构推导 URL
                # 这里可以扩展更复杂的分析逻辑
                
            return None
            
        except Exception as e:
            print(f"❌ 页面分析查找失败: {e}")
            return None
    
    def _find_all_issue_links_on_page(self, soup, journal_name):
        """查找页面上所有期刊相关的链接"""
        try:
            print(f"🔍 分析 {journal_name} 页面，查找期号相关链接...")
            
            issue_links = []
            
            # 获取所有链接
            all_links = soup.find_all('a', href=True)
            print(f"页面总链接数: {len(all_links)}")
            
            # 过滤期刊相关链接
            for link in all_links:
                href = link.get('href')
                text = link.get_text().strip()
                
                if href and text:
                    # 构造完整URL
                    full_url = urljoin(self.base_url, href) if href.startswith('/') else href
                    
                    link_info = {
                        'text': text,
                        'url': full_url,
                        'href': href,
                        'year': self._extract_year_from_text(text),
                        'issue': self._extract_issue_from_text(text)
                    }
                    
                    # 检查是否为期刊详情链接
                    if ('journal/details' in href or 'journal/secure/details' in href) and 'params=' in href:
                        # 提取参数
                        params = self._extract_params_from_url(href)
                        link_info['params'] = params
                        issue_links.append(link_info)
                    
                    # 或者检查文本是否包含年份期号信息
                    elif link_info['year'] or link_info['issue']:
                        issue_links.append(link_info)
            
            print(f"找到期刊相关链接: {len(issue_links)} 个")
            
            # 显示前5个链接的信息
            for i, link in enumerate(issue_links[:5]):
                year_str = str(link['year']) if link['year'] else '未知'
                issue_str = str(link['issue']) if link['issue'] else '未知'
                print(f"  {i+1}. 文本: {link['text'][:50]}")
                print(f"      年份: {year_str}, 期号: {issue_str}")
                print(f"      链接: {link['href']}")
                if 'params' in link:
                    print(f"      参数: {link['params'][:50]}...")
                print()
            
            return issue_links
            
        except Exception as e:
            print(f"❌ 期号链接分析失败: {e}")
            return []
    
    def _get_issue_list_via_ajax(self, journal_name, year, soup):
        """通过Ajax接口获取指定年份的期号列表"""
        try:
            print(f"🔄 通过Ajax获取 {journal_name} {year}年期号列表...")
            
            # 设置当前年份供解析函数使用
            self._current_ajax_year = year
            
            journal_info = self._extract_journal_params_from_page(soup)
            if not journal_info or not journal_info.get('gch'):
                print("❌ 未能从页面提取必要参数")
                return None
            
            # 模拟Ajax请求
            ajax_url = f"{self.base_url}/journal/journalHandler"
            
            params = {
                'op': 'getnum',
                'gch': journal_info['gch'],
                'years': str(year),
                'langType': '1'
            }
            
            print(f"  Ajax URL: {ajax_url}")
            print(f"  参数: {params}")
            
            # 反爬虫防护：请求前等待
            self._wait_between_requests()
            
            response = self.session.get(ajax_url, params=params, timeout=15)
            
            if response.status_code == 200:
                try:
                    json_data = response.json()
                    if json_data.get('succee', False):
                        print(f"✅ 成功获取期号数据")
                        return json_data.get('data', '')
                    else:
                        print(f"❌ Ajax请求返回失败: {json_data}")
                        return None
                except json.JSONDecodeError:
                    print(f"❌ Ajax响应不是有效JSON: {response.text[:200]}")
                    return None
            else:
                print(f"❌ Ajax请求失败，状态码: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Ajax请求异常: {e}")
            return None
    
    def _extract_journal_params_from_page(self, soup):
        """从页面JavaScript代码中提取期刊参数和Ajax接口信息"""
        try:
            print("🔍 从页面JavaScript中提取参数信息...")
            
            # 获取页面脚本内容
            scripts = soup.find_all('script', string=True)
            page_html = str(soup)
            
            journal_info = {
                'qkurl': None,
                'gch': None,
                'ajax_endpoints': []
            }
            
            for script in scripts:
                script_content = script.string
                if script_content:
                    # 查找期刊刊号
                    gch_match = re.search(r'"gch":\s*"([^"]+)"', script_content)
                    if gch_match:
                        journal_info['gch'] = gch_match.group(1)
                        print(f"  找到期刊刊号: {journal_info['gch']}")
            
            # 在整个页面HTML中查找 dtgch 属性
            dtgch_matches = re.findall(r'dtgch=[\'"]([^\'"]+)[\'"]', page_html)
            if dtgch_matches:
                # 取第一个匹配的值作为期刊的gch
                journal_info['gch'] = dtgch_matches[0]
                print(f"  从页面元素中找到期刊标识符(dtgch): {journal_info['gch']}")
            
            return journal_info
            
        except Exception as e:
            print(f"❌ 提取JavaScript参数失败: {e}")
            return None
    
    def _parse_issue_list_html(self, html_content):
        """解析期号列表HTML内容"""
        try:
            if not html_content:
                return []
            
            print("🔍 解析期号列表HTML...")
            soup = BeautifulSoup(html_content, 'html.parser')
            
            issue_links = []
            
            # 查找所有链接
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href')
                text = link.get_text().strip()
                
                # 检查是否为期号链接
                if href and ('journal/details' in href or 'journal/secure/details' in href or 'details?params=' in href):
                    year = self._extract_year_from_text(text)
                    issue = self._extract_issue_from_text(text)
                    
                    # 对于只包含数字的文本（如"8"），将其作为期号，并使用当前Ajax请求的年份
                    if not year and not issue and text.isdigit():
                        issue = int(text)
                        year = getattr(self, '_current_ajax_year', None)
                    
                    # 如果文本中只有期号信息（如"第8期"或简单的"8"），使用请求的年份
                    if issue and not year:
                        year = getattr(self, '_current_ajax_year', None)
                        if not year:
                            import datetime
                            year = datetime.datetime.now().year
                    
                    # 确保年份信息正确（Ajax返回的数据可能年份信息不准确）
                    ajax_year = getattr(self, '_current_ajax_year', None)
                    if ajax_year:
                        if year != ajax_year:
                            print(f"    调整年份: {year} -> {ajax_year} (使用Ajax请求的年份)")
                        year = ajax_year
                    
                    # 构造完整URL
                    if href.startswith('details?params='):
                        full_url = f"{self.base_url}/journal/{href}"
                    else:
                        full_url = urljoin(self.base_url, href) if href.startswith('/') else href
                    
                    issue_info = {
                        'text': text,
                        'url': full_url,
                        'href': href,
                        'params': self._extract_params_from_url(href),
                        'year': year,
                        'issue': issue
                    }
                    
                    issue_links.append(issue_info)
                    print(f"  找到期号: {text} -> {year}年第{issue}期")
                    print(f"    URL: {full_url}")
            
            return issue_links
            
        except Exception as e:
            print(f"❌ 解析期号列表失败: {e}")
            return []
    
    def _extract_year_from_text(self, text):
        """从文本中提取年份"""
        if not text:
            return None
        year_pattern = r'20\d{2}'
        match = re.search(year_pattern, text)
        if match:
            return int(match.group())
        return None
    
    def _extract_issue_from_text(self, text):
        """从文本中提取期号"""
        if not text:
            return None
        issue_patterns = [
            r'第(\d+)期',
            r'第(\d+)號',
            r'(\d+)期',
            r'/\s*0?(\d{1,2})(?!\d)',
            r'No\.?\s*(\d+)',
        ]
        for pattern in issue_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        pure_number_match = re.match(r'^\s*0?(\d{1,2})\s*$', text)
        if pure_number_match:
            return int(pure_number_match.group(1))
        return None
    
    def _extract_params_from_url(self, url):
        """从URL中提取params参数"""
        try:
            if 'params=' in url:
                return url.split('params=')[1].split('&')[0]
            return None
        except:
            return None

def main():
    """命令行调用功能"""
    import sys
    
    if len(sys.argv) != 4:
        print("使用方法: python 2.issue_url_finder.py 期刊名称 年份 期数")
        print("示例: python 2.issue_url_finder.py 情报学报 2024 12")
        return
    
    journal_name = sys.argv[1]
    try:
        year = int(sys.argv[2])
        issue = int(sys.argv[3])
    except ValueError:
        print("错误：年份和期数必须是数字")
        return
    
    print(f"查找 {journal_name} {year}年第{issue}期的URL...")
    
    finder = IssueUrlFinder()
    result = finder.get_issue_url(journal_name, year, issue)
    
    if result:
        print(f"✅ 找到期号URL:")
        print(f"   URL: {result['url']}")
        print(f"   方法: {result['method']}")
        if result.get('params'):
            print(f"   参数: {result['params']}")
    else:
        print(f"❌ 未找到 {journal_name} {year}年第{issue}期的URL")

if __name__ == "__main__":
    main()
