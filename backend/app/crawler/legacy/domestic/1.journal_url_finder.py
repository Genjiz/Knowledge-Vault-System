import json
import os


class JournalUrlFinder:
    """期刊URL查找器 - 严格依赖缓存(精确名称匹配)"""

    def __init__(self):
        self.base_url = "https://www.ncpssd.cn"
        # 期刊数据文件路径
        self.data_file = os.path.join(os.path.dirname(__file__), 'journal_url_cache.json')

        self.known_journals = self._load_known_journals()

    def _load_known_journals(self):
        """加载已知期刊参数"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                print(f"期刊数据文件不存在: {self.data_file}")
                return {}
        except Exception as e:
            print(f"加载期刊数据失败: {e}")
            return {}
    
    def _save_known_journals(self):
        """保存已知期刊参数"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.known_journals, f, ensure_ascii=False, indent=2)
            print(f"期刊数据已保存到: {self.data_file}")
        except Exception as e:
            print(f"保存期刊数据失败: {e}")
    
    def find_journal_url(self, journal_name):
        """
        根据期刊名称查找期刊URL
        
        Args:
            journal_name (str): 期刊名称
            
        Returns:
            str: 期刊URL，如果未找到返回None
        """
        journal_name = str(journal_name).strip()
        param = self.known_journals.get(journal_name)
        if not param:
            print(f"未找到期刊缓存: {journal_name}")
            return None
        return f"{self.base_url}/journal/secure/details?params={param}"
    
    def add_known_journal(self, journal_name, param):
        """添加已知期刊参数到缓存并保存到文件"""
        self.known_journals[journal_name] = param
        self._save_known_journals()
        print(f"已添加期刊: {journal_name}")
    
    def get_journal_param_from_url(self, url):
        """从 URL 中提取 params 参数"""
        if url and 'params=' in url:
            return url.split('params=')[1].split('&')[0]
        return None
    
    def get_journal_param(self, journal_name):
        """获取期刊的params参数"""
        url = self.find_journal_url(journal_name)
        if url and 'params=' in url:
            return url.split('params=')[1].split('&')[0]
        return None
    
    def list_known_journals(self):
        """列出已知的期刊"""
        print("已知期刊列表:")
        for journal in self.known_journals.keys():
            print(f"  - {journal}")

def main():
    """命令行调用功能"""
    import sys
    
    if len(sys.argv) != 2:
        print("使用方法: python 1.journal_url_finder.py 期刊名称")
        print("示例: python 1.journal_url_finder.py 情报学报")
        return
    
    journal_name = sys.argv[1]
    print(f"查找期刊: {journal_name}")
    
    finder = JournalUrlFinder()
    url = finder.find_journal_url(journal_name)
    
    if url:
        print(f"✅ 找到期刊URL: {url}")
        param = finder.get_journal_param(journal_name)
        if param:
            print(f"   参数: {param}")
    else:
        print(f"❌ 未找到期刊: {journal_name}")
        print("可能的原因:")
        print("  1. 期刊名称不正确")
        print("  2. 期刊不在数据库中")
        print("  3. 网络连接问题")

if __name__ == "__main__":
    main()
