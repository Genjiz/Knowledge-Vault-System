"""
期刊论文信息爬虫主程序
串联所有功能模块，提供完整的论文抓取流程
"""

import sys
import os

class JournalPaperInfoCrawler:
    """期刊论文信息爬虫 - 完整的论文抓取流程"""
    
    def __init__(self):
        """初始化所有组件"""
        print("🚀 初始化期刊论文信息爬虫...")
        
        # 动态导入各个组件
        try:
            import importlib.util
            import sys
            import os
            
            # 获取当前文件目录
            current_dir = os.path.dirname(__file__)
            
            # 导入各个模块
            def import_module_by_path(module_name, file_path):
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module
            
            module_1 = import_module_by_path('journal_url_finder', os.path.join(current_dir, '1.journal_url_finder.py'))
            module_2 = import_module_by_path('issue_url_finder', os.path.join(current_dir, '2.issue_url_finder.py'))
            module_3 = import_module_by_path('paper_title_extractor', os.path.join(current_dir, '3.paper_title_extractor.py'))
            module_4 = import_module_by_path('paper_detail_url_finder', os.path.join(current_dir, '4.paper_detail_url_finder.py'))
            module_5 = import_module_by_path('paper_detail_info_extractor', os.path.join(current_dir, '5.paper_detail_info_extractor.py'))
            
            self.journal_finder = module_1.JournalUrlFinder()
            self.issue_finder = module_2.IssueUrlFinder(min_delay=1, max_delay=3)
            self.title_extractor = module_3.PaperTitleExtractor()
            self.detail_url_finder = module_4.PaperDetailUrlFinder(min_delay=1, max_delay=3)
            self.abstract_extractor = module_5.PaperDetailInfoExtractor(min_delay=1, max_delay=3)
            
            print("✅ 所有组件初始化完成")
        except ImportError as e:
            print(f"❌ 导入模块失败: {e}")
            print("请确保所有必要的模块文件存在")
            raise
    
    def crawl_journal_papers(self, journal_name, year, issue):
        """
        完整的论文抓取流程
        
        Args:
            journal_name (str): 期刊名称，如"情报学报"
            year (int): 年份，如 2024
            issue (int): 期数，如 12
            
        Returns:
            dict: 包含论文信息和相关元数据的字典
        """
        print(f"\n🎯 开始抓取: {journal_name} {year}年第{issue}期")
        print("=" * 60)
        
        result = {
            'journal_name': journal_name,
            'year': year,
            'issue': issue,
            'success': False,
            'papers': [],
            'error_message': None,
            'steps': {
                'journal_url_found': False,
                'issue_url_found': False,
                'papers_extracted': False,
                'detail_urls_found': False,
                'abstracts_extracted': False
            }
        }
        
        try:
            # 第一步：使用 journal_url_finder 获取期刊默认URL
            print(f"\n📖 第一步: 查找期刊默认URL")
            journal_url = self.journal_finder.find_journal_url(journal_name)
            
            if not journal_url:
                result['error_message'] = f"未找到期刊 '{journal_name}' 的默认URL"
                print(f"❌ {result['error_message']}")
                return result

            result['steps']['journal_url_found'] = True
            print(f"✅ 找到期刊默认URL: {journal_url[:80]}...")
            
            # 第二步：使用 issue_url_finder 获取具体期号URL
            print(f"\n🔍 第二步: 查找 {year}年第{issue}期 的具体URL")
            issue_result = self.issue_finder.get_issue_url(journal_name, year, issue)
            
            if not issue_result:
                result['error_message'] = f"未找到 {journal_name} {year}年第{issue}期 的具体URL"
                print(f"❌ {result['error_message']}")
                return result
            
            result['steps']['issue_url_found'] = True
            result['issue_url'] = issue_result['url']
            result['issue_method'] = issue_result['method']
            print(f"✅ 找到期号URL: {issue_result['url'][:80]}...")
            print(f"   获取方法: {issue_result['method']}")
            
            # 第三步：使用 paper_title_extractor 提取论文信息
            print(f"\n📚 第三步: 从期号页面提取论文标题信息")
            papers = self.title_extractor.extract_papers_by_journal_info(journal_name, year, issue)
            
            if not papers:
                result['error_message'] = f"从 {year}年第{issue}期 页面未提取到论文信息"
                print(f"❌ {result['error_message']}")
                return result
            
            result['steps']['papers_extracted'] = True
            result['papers'] = papers
            result['papers_count'] = len(papers)
            print(f"✅ 成功提取到 {len(papers)} 篇论文")
            
            # 获取保存路径（由 extract_papers_by_journal_info 已经保存）
            # 注意：保存路径是在项目根目录下
            project_root = os.path.dirname(os.path.dirname(__file__))
            result['saved_path'] = os.path.join(project_root, journal_name, str(year), f"{journal_name}_{year}_{issue}.json")
            
            # 第四步：使用 paper_detail_url_finder 获取论文详情页URL
            print(f"\n🔗 第四步: 获取论文详情页URL")
            detail_url_success = self.detail_url_finder.extract_paper_detail_urls_by_journal_info(journal_name, year, issue)
            
            if detail_url_success:
                result['steps']['detail_urls_found'] = True
                print(f"✅ 论文详情页URL获取完成")
            else:
                print(f"⚠️ 论文详情页URL获取失败")
            
            # 第五步：使用 paper_detail_info_extractor 提取摘要信息
            print(f"\n📝 第五步: 提取论文摘要信息")
            abstract_success = self.abstract_extractor.extract_abstracts_by_journal_info(journal_name, year, issue)
            
            if abstract_success:
                result['steps']['abstracts_extracted'] = True
                print(f"✅ 论文摘要信息提取完成")
            else:
                print(f"⚠️ 论文摘要信息提取失败")
            
            result['success'] = True
            
            print(f"\n🎉 抓取完成!")
            print(f"   期刊: {journal_name}")
            print(f"   期号: {year}年第{issue}期")
            print(f"   论文数量: {len(papers)} 篇")
            print(f"   保存路径: {result['saved_path']}")
            if result['steps']['detail_urls_found']:
                print(f"   详情页URL: 已获取")
            if result['steps']['abstracts_extracted']:
                print(f"   摘要信息: 已获取")
            
            return result
            
        except Exception as e:
            result['error_message'] = f"抓取过程中发生错误: {str(e)}"
            print(f"❌ {result['error_message']}")
            return result
    
    def print_papers_summary(self, papers, max_display=5):
        """打印论文摘要信息"""
        if not papers:
            print("❌ 没有论文信息可显示")
            return
        
        print(f"\n📋 论文列表 (显示前 {min(max_display, len(papers))} 篇):")
        print("=" * 80)
        
        for i, paper in enumerate(papers[:max_display], 1):
            print(f"{i}. 📄 {paper['title']}")
            if paper.get('authors'):
                print(f"   👥 作者: {paper['authors']}")
            if paper.get('pages'):
                print(f"   📃 页码: {paper['pages']}")
            if paper.get('issue'):
                print(f"   📅 期号: {paper['issue']}")
            print("-" * 80)
        
        if len(papers) > max_display:
            print(f"... 还有 {len(papers) - max_display} 篇论文，详见保存的JSON文件")

def main():
    """主函数"""
    # Force UTF-8 output for Windows consoles
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass # Python < 3.7 or other issue

    print("=" * 60)
    print("🕷️  期刊论文信息爬虫 - 一站式论文抓取工具")
    print("=" * 60)
    print("功能：输入期刊名称、年份、期数，自动抓取论文信息")
    print("流程：期刊查找 → 期号定位 → 论文提取 → 详情页URL获取 → 摘要提取")
    print()
    
    # 检查命令行参数
    if len(sys.argv) == 4:
        # 命令行参数模式
        journal_name = sys.argv[1]
        try:
            year = int(sys.argv[2])
            issue = int(sys.argv[3])
        except ValueError:
            print("❌ 年份和期数必须是数字")
            print("使用方法: python 0.journal_paper_info_crawler.py 期刊名称 年份 期数")
            return
        
        print(f"📋 命令行参数:")
        print(f"   期刊: {journal_name}")
        print(f"   年份: {year}")
        print(f"   期数: {issue}")
        
    else:
        # 交互式输入模式
        print("📋 请输入抓取信息:")
        
        try:
            journal_name = input("期刊名称 (如: 情报学报): ").strip()
            if not journal_name:
                print("❌ 期刊名称不能为空")
                return
            
            year_input = input("年份 (如: 2024): ").strip()
            if not year_input:
                print("❌ 年份不能为空")
                return
            
            issue_input = input("期数 (如: 12): ").strip()
            if not issue_input:
                print("❌ 期数不能为空")
                return
            
            year = int(year_input)
            issue = int(issue_input)
            
        except ValueError:
            print("❌ 年份和期数必须是数字")
            return
        except KeyboardInterrupt:
            print("\n❌ 用户取消操作")
            return
        except EOFError:
            print("\n❌ 输入结束")
            return
    
    # 创建爬虫实例并执行抓取
    try:
        crawler = JournalPaperInfoCrawler()
        result = crawler.crawl_journal_papers(journal_name, year, issue)
        
        # 显示结果
        print("\n" + "=" * 60)
        print("📊 抓取结果汇总:")
        print("=" * 60)
        
        if result['success']:
            print("✅ 抓取成功!")
            print(f"   期刊: {result['journal_name']}")
            print(f"   期号: {result['year']}年第{result['issue']}期")
            print(f"   论文数量: {result['papers_count']} 篇")
            print(f"   保存路径: {result['saved_path']}")
            if result['steps']['detail_urls_found']:
                print(f"   详情页URL: 已获取")
            if result['steps']['abstracts_extracted']:
                print(f"   摘要信息: 已获取")
            
            # 显示论文摘要
            crawler.print_papers_summary(result['papers'])
            
        else:
            print("❌ 抓取失败!")
            print(f"   错误信息: {result['error_message']}")
            
            # 显示执行步骤状态
            print("\n🔍 执行步骤:")
            steps = result['steps']
            print(f"   1. 期刊URL查找: {'✅' if steps['journal_url_found'] else '❌'}")
            print(f"   2. 期号URL查找: {'✅' if steps['issue_url_found'] else '❌'}")
            print(f"   3. 论文信息提取: {'✅' if steps['papers_extracted'] else '❌'}")
            print(f"   4. 详情页URL获取: {'✅' if steps['detail_urls_found'] else '❌'}")
            print(f"   5. 摘要信息提取: {'✅' if steps['abstracts_extracted'] else '❌'}")
        
        print("\n💡 使用提示:")
        print("   命令行模式: python 0.journal_paper_info_crawler.py 期刊名称 年份 期数")
        print("   交互式模式: python 0.journal_paper_info_crawler.py")
        
    except Exception as e:
        print(f"❌ 程序执行失败: {e}")
        print("请检查所有模块文件是否正确安装")

if __name__ == "__main__":
    main()
