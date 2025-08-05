import json
import os
from typing import Dict, Any

GIVEAWAY_DATA_FILE = 'giveaway_data.json' # 數據檔案路徑

def load_giveaway_data() -> Dict[str, Any]:
    """從 JSON 檔案載入抽獎數據"""
    if os.path.exists(GIVEAWAY_DATA_FILE):
        with open(GIVEAWAY_DATA_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print(f"警告: {GIVEAWAY_DATA_FILE} 檔案內容無效或為空。將建立新的檔案。")
                return {}
    return {}

def save_giveaway_data(data: Dict[str, Any]):
    """將抽獎數據儲存到 JSON 檔案 (確保能處理中文)"""
    with open(GIVEAWAY_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_guild_data(giveaway_data: Dict[str, Any], guild_id: int) -> Dict[str, Any]:
    """獲取或初始化伺服器的抽獎數據"""
    guild_id_str = str(guild_id)
    if guild_id_str not in giveaway_data:
        giveaway_data[guild_id_str] = {
            "prize_pools": {},
            "active_giveaways": {}
        }
    return giveaway_data[guild_id_str]