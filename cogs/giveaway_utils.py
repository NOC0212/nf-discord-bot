import datetime
from typing import Optional

def parse_duration(duration_str: str) -> Optional[datetime.timedelta]:
    """
    解析一個表示時間持續時間的字符串，並返回一個 datetime.timedelta 對象。
    支援的單位有 's' (秒), 'm' (分), 'h' (小時), 'd' (天)。
    """
    seconds = 0
    if duration_str.endswith('s'):
        try:
            seconds = int(duration_str[:-1])
        except ValueError:
            return None
    elif duration_str.endswith('m'):
        try:
            seconds = int(duration_str[:-1]) * 60
        except ValueError:
            return None
    elif duration_str.endswith('h'):
        try:
            seconds = int(duration_str[:-1]) * 3600
        except ValueError:
            return None
    elif duration_str.endswith('d'):
        try:
            seconds = int(duration_str[:-1]) * 86400
        except ValueError:
            return None
    
    if seconds <= 0:
        return None
    return datetime.timedelta(seconds=seconds)