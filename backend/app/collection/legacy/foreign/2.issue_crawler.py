from DrissionPage import ChromiumPage, ChromiumOptions
from pathlib import Path
try:
    from . import config_foreign
except ImportError:
    import config_foreign

class IssueCrawler:
    """使用 DrissionPage 爬取论文"""
    
    def __init__(self):
        self.page = None
        
    def _init_page(self):
        if not self.page:
            co = ChromiumOptions()
            co.set_local_port(9222)
            
            # 设置用户数据目录，使用 dp_browser_data
            data_dir = Path(__file__).parent.parent / "dp_browser_data"
            co.set_user_data_path(str(data_dir))
            
            print(f"🚀 正在连接到 Chrome 端口 9222...")
            print(f"📂 使用用户数据目录: {data_dir}")
            self.page = ChromiumPage(co)
            
    def close_page(self):
        if self.page:
            self.page.quit()
            self.page = None

    # 重点：千万不要用css选择器，要用tag的方式获取元素信息
    def crawl_issue(self, url):
        self._init_page()
        print(f"🕷️ 正在爬取期刊: {url}")
        papers = []
        
        try:
            self.page.get(url)
            
            print("⏳ 等待开关加载...")
            # self.page.wait.ele_displayed('#aa-expand-all-articles-previews', timeout=10)
            if not self.page.wait.ele_displayed('#aa-expand-all-articles-previews', timeout=10):
                self.page.get_screenshot(name='error_switch_not_found.png') # 截图
                raise Exception("❌ 超时：未能找到预览开关按钮")


            switch_container = self.page.ele('#aa-expand-all-articles-previews')
            switch_label = switch_container.ele('tag:label@@class:switch-label')
            
            if switch_label:
                switch_input = switch_label.ele('tag:input')
                if switch_input:
                    current_id = switch_input.attr('id')
                    if current_id == 'previews-switch':
                        print("开关当前关闭，正在打开...")
                        switch_label.click()
                        self.page.wait.ele_displayed('#previews-switch-checked', timeout=5)
                        print("开关已打开")
                    else:
                        print("开关已经打开")
                else:
                    print("调试: 未找到开关 input 元素")
            else:
                print("调试: 未找到开关 label 元素")
            
            print("⏳ 等待文章列表加载...")
            if not self.page.wait.ele_displayed('tag:li@@class:js-article-list-item', timeout=30):
                self.page.get_screenshot(name='error_articles_timeout.png') # 截图
                raise Exception("❌ 超时：文章列表在 30s 内未加载完成")

            print("⏳ 等待摘要加载...")
            if not self.page.wait.ele_displayed('tag:div@@class:js-abstract-body-text', timeout=120):
                self.page.get_screenshot(name='error_abstract_timeout.png') # 截图
                raise Exception("❌ 超时：摘要内容在 120s 内未显示，请检查开关是否点开")

            print("🔍 正在查找文章...")
            articles = self.page.eles('tag:li@@class:js-article-list-item')
            print(f"📄 找到 {len(articles)} 篇文章。")
            
            if not articles:
                 print("调试: 页面内容可能不同。正在输出部分 HTML 结构:")
                 print(self.page.html[:500])
                 print(f"调试: 任意 'li' 元素数量: {len(self.page.eles('tag:li'))}")
            
            for art in articles:
                try:
                    dl_node = art.ele('tag:dl@@class:js-article article-content')
                    if not dl_node:
                        print("调试: 未找到 dl 元素")
                        continue

                    title_node = dl_node.ele('tag:span@@class:js-article-title')
                    if not title_node:
                        print("调试: 未找到标题节点")
                        continue
                    title = title_node.text.strip()
                    print(f"📝 标题: {title[:30]}...")

                    link_node = dl_node.ele('tag:a')
                    if not link_node:
                        print("调试: 未找到链接节点")
                        continue
                    href = link_node.attr('href')
                    if not href: 
                        print("调试: 未找到 HREF")
                        continue
                    detail_url = config_foreign.BASE_URL + href if href.startswith('/') else href
                    print(f"🔗 链接: {detail_url}")
                    
                    authors = "Unknown"
                    author_dd = dl_node.ele('tag:dd@@class:js-article-author-list')
                    if author_dd:
                        authors = author_dd.text.strip()
                        print(f"👤 作者: {authors}")
                    else:
                        print(f"调试: 未找到作者节点")

                    abstract = "无摘要"
                    abstract_div = dl_node.ele('tag:div@@class:js-abstract-body-text branded')
                    if abstract_div:
                        abstract_p = abstract_div.ele('tag:p')
                        if abstract_p:
                            abstract = abstract_p.text.strip()
                            print(f"📄 摘要: {abstract[:50]}...")
                        else:
                            print(f"调试: 找到了摘要容器，但未找到 p 标签")
                    else:
                        print(f"调试: 未找到摘要容器")

                    paper = {
                        "title": title,
                        "authors": authors,
                        "detail_url": detail_url,
                        "abstract": abstract
                    }
                    papers.append(paper)
                    
                    print(f"✅ 已提取: {title[:30]}...")
                    
                except Exception as e:
                    print(f"❌ 部分错误: {e}")
                    
            return papers
            
        except Exception as e:
            print(f"❌ 期刊爬取失败: {e}")
            return []

if __name__ == "__main__":
    crawler = IssueCrawler()
    print("请输入 ScienceDirect 期刊 URL:")
    print("示例: https://www.sciencedirect.com/journal/information-processing-and-management/vol/60/issue/1")
    url = input("URL: ").strip()
    
    if url:
        results = crawler.crawl_issue(url)
        print(f"\n{'='*60}")
        print(f"📊 摘要: 已爬取 {len(results)} 篇论文")
        print(f"{'='*60}")
        for i, res in enumerate(results, 1):
            print(f"\n{i}. {res['title']}")
            print(f"   作者: {res['authors']}")
            print(f"   摘要: {res['abstract'][:100]}...")
            print(f"   链接: {res['detail_url']}")
        crawler.close_page()
    else:
        print("未提供 URL。")
