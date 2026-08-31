import json
import os
import time

from DrissionPage import ChromiumPage, ChromiumOptions
import config_foreign

class VolumeYearMapper:
    """Builds and caches Year <-> Volume/Issue mapping using DrissionPage (Anti-Bot)"""
    
    def __init__(self):
        self.cache_file = os.path.join(os.path.dirname(__file__), 'journal_vol_cache.json')
        self.cache = self._load_cache()
        self.page = None
        
    def _load_cache(self):
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
        
    def _save_cache(self):
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)
            
    def _init_page(self):
        if not self.page:
            co = ChromiumOptions()
            # Connect to the existing browser launched by run_browser.bat
            co.set_local_port(9222)
            
            print(f"🚀 Connecting to Chrome on port 9222...")
            self.page = ChromiumPage(co)
            
    def close_page(self):
        if self.page:
            self.page.quit()
            self.page = None
            
    def get_calculated_volume(self, journal_name, target_year):
        slug = config_foreign.JOURNAL_SLUGS.get(journal_name)
        if not slug:
            print(f"❌ Unknown journal: {journal_name}")
            return None
            
        # Ensure we have an anchor
        if journal_name not in self.cache or 'anchor' not in self.cache[journal_name]:
            print(f"🔄 Cache miss for anchor of {journal_name}. Fetching latest issue info...")
            self._update_journal_anchor(journal_name, slug)
            
        if journal_name in self.cache and 'anchor' in self.cache[journal_name]:
            anchor = self.cache[journal_name]['anchor']
            anchor_year = int(anchor['year'])
            anchor_vol = int(anchor['vol'])
            
            # Logic: Vol_Target = Vol_Anchor - (Year_Anchor - Year_Target)
            # Assuming 1 Volume per Year as per user instruction
            diff = anchor_year - target_year
            target_vol = anchor_vol - diff
            
            return target_vol
        return None

    def _log(self, msg):
        print(msg)
        with open('mapper_debug.log', 'a', encoding='utf-8') as f:
            f.write(msg + "\n")

    def _update_journal_anchor(self, journal_name, slug):
        self._init_page()
        url = f"{config_foreign.BASE_URL}/journal/{slug}/issues"
        self._log(f"📖 Visiting: {url}")
        
        try:
            self.page.get(url)
            
            # Anti-Bot checks
            if "Just a moment" in self.page.title or "Challenge" in self.page.title:
                self._log("⚠️ Challenge detected! Please solve it in the browser window.")
                self.page.wait.ele_displayed('.accordion-panel', timeout=60)

            # 1. Dismiss Overlays
            try:
                btn = self.page.ele('#accept-recommended-btn-handler')
                if btn: btn.click()
                btns = self.page.eles('tag:button@@aria-label:Close')
                for b in btns:
                    if b.states.is_displayed: b.click()
            except: pass

            # 2. Find valid Year panel
            self._log("📂 Finding latest year panel...")
            self.page.wait.ele_displayed('.accordion-panel', timeout=15)
            
            all_panels = self.page.eles('.accordion-panel')
            if not all_panels:
                self._log("❌ No accordion panels found.")
                return

            found_anchor = False
            for panel in all_panels:
                # Logic from scrape_sciencedirect.py
                # Try to find the button inside this panel
                btn = panel.ele('tag:button')
                if not btn:
                    btn = panel.ele('xpath:.//button')
                
                if btn and 'Volume' in btn.text:
                    full_text = btn.text
                    # Normalize dashes
                    full_text_normalized = full_text.replace('—', '-').replace('–', '-')
                    parts = full_text_normalized.split('-')
                    
                    year = ""
                    volume = ""
                    
                    for part in parts:
                        part = part.strip()
                        if part.isdigit() and len(part) == 4:
                            year = part
                        if 'Volume' in part:
                            volume = part.replace('Volume', '').strip()
                    
                    if year and volume:
                        year = int(year)
                        vol = int(volume)
                        
                        self._log(f"✅ Found Anchor: Year {year} -> Volume {vol} (Text: {full_text})")
                        
                        if journal_name not in self.cache:
                            self.cache[journal_name] = {}
                        
                        self.cache[journal_name]['anchor'] = {
                            'year': year,
                            'vol': vol,
                            'updated_at': time.strftime("%Y-%m-%d")
                        }
                        self._save_cache()
                        found_anchor = True
                        break # Found our anchor, stop looking
                    
            if not found_anchor:
                self._log("❌ Could not find any panel with 'Volume' in the title.")

        except Exception as e:
            self._log(f"❌ Error: {e}")
        finally:
            pass

if __name__ == "__main__":
    mapper = VolumeYearMapper()
    # Test for 2024
    vol = mapper.get_calculated_volume("Information Processing & Management", 2024)
    print(f"Calculated Volume for 2024: {vol}")
