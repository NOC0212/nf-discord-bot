# utils/weather.py
import requests
from config import WEATHER_API_KEY
import json
from datetime import datetime

async def get_weather_forecast(location: str):
    """
    從中央氣象署 API 獲取未來3天的天氣預報。
    """
    api_url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={WEATHER_API_KEY}&locationName={location}"
    
    try:
        # 添加 verify=False 來禁用 SSL 證書驗證
        # 注意：這會降低安全性，但可以解決 SSLCertVerificationError。
        # 僅在您了解風險的情況下使用。
        response = requests.get(api_url, verify=False)
        response.raise_for_status()  # 檢查 HTTP 請求是否成功
        data = response.json()
        
        if 'records' not in data or not data['records']['location']:
            return f"找不到 **{location}** 的天氣資訊，請確認地區名稱是否正確。"
        
        location_data = data['records']['location'][0]
        forecast = location_data['weatherElement']
        
        forecast_str = f"**未來 {len(forecast[0]['time'])} 個時段 {location} 的天氣預報：**\n\n"
        
        wx = next((item for item in forecast if item['elementName'] == 'Wx'), None)
        min_temp = next((item for item in forecast if item['elementName'] == 'MinT'), None)
        max_temp = next((item for item in forecast if item['elementName'] == 'MaxT'), None)
        pop = next((item for item in forecast if item['elementName'] == 'PoP'), None)

        if not wx or not min_temp or not max_temp or not pop:
            return f"無法獲取 **{location}** 的詳細天氣資訊。"

        for i in range(len(wx['time'])):
            day_forecast = wx['time'][i]['parameter']['parameterName']
            min_t = min_temp['time'][i]['parameter']['parameterName']
            max_t = max_temp['time'][i]['parameter']['parameterName']
            rain_chance = pop['time'][i]['parameter']['parameterName']
            
            # 使用 startTime 和 endTime 建立更精準的時間標籤
            start_time_str = wx['time'][i]['startTime']
            end_time_str = wx['time'][i]['endTime']
            
            start_time = datetime.fromisoformat(start_time_str)
            end_time = datetime.fromisoformat(end_time_str)
            
            # 格式化為易於閱讀的時段標籤
            time_period = f"{start_time.strftime('%m/%d %H:%M')} 至 {end_time.strftime('%m/%d %H:%M')}"

            forecast_str += (
                f"**時段：** {time_period}\n"
                f"**天氣狀況：** {day_forecast}\n"
                f"**溫度：** {min_t}°C ~ {max_t}°C\n"
                f"**降雨機率：** {rain_chance}%\n\n"
            )

        return forecast_str
    
    except requests.exceptions.RequestException as e:
        print(f"呼叫天氣 API 時發生錯誤：{e}")
        return "很抱歉，在查詢天氣時發生了網路錯誤。請稍後再試。"
    except Exception as e:
        print(f"處理天氣資料時發生錯誤：{e}")
        return "很抱歉，處理天氣資訊時發生了意外錯誤。"
