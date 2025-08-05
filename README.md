# Discord 機器人專案

這是一個功能豐富的 Discord 機器人，整合了等級系統、貨幣系統、商店、報到獎勵、票務系統、天氣查詢、自訂指令及多項管理功能。

## 專案結構概覽

- `main.py`: 機器人主程式，負責啟動機器人、載入擴充功能 (Cogs) 並同步斜線指令。
- `config.py`: 存放機器人的敏感資訊，如 Bot Token 和天氣 API 金鑰。
- `requirements.txt`: 專案所需的 Python 函式庫清單，方便部署。
- `cogs/`: 存放所有擴充功能的資料夾。
  - `checkin.py`: 處理簽到相關指令和邏輯。
  - `currency.py`: 實現貨幣系統，包括轉帳和餘額查詢。
  - `custom_commands.py`: 允許管理員建立和管理自訂關鍵詞觸發的回應。
  - `game.py`: 包含遊戲相關功能，例如 1a2b 猜數字遊戲。
  - `giveaways.py`: 處理抽獎活動的建立、參與和結束。
  - `leveling.py`: 處理等級系統，如經驗值累計和升級通知。
  - `member_events.py`: 管理新成員加入和離開時的歡迎與再見訊息。
  - `moderation.py`: 提供管理員工具，如大量刪除訊息。
  - `ping.py`: 簡單的延遲測試指令。
  - `reactroles.py`: 實作反應身分組功能。
  - `shop.py`: 處理商店功能，允許使用者購買物品。
  - `tickets.py`: 提供工單系統，供使用者建立客服票券。
  - `weather.py`: 提供天氣查詢功能。
- `utils/`: 存放輔助模組的資料夾。
  - `weather.py`: 包含從中央氣象署 API 獲取天氣預報的輔助函數。
  - `giveaway_data.py`: 處理抽獎數據的讀取和儲存。
  - `giveaway_utils.py`: 包含解析時間字串的工具函數。
- `data/` (建議資料夾): 存放所有 `.json` 數據檔案。
  - `checkin_data.json`: 儲存使用者報到的時間戳和報到獎勵設定。
  - `currency.json`: 儲存使用者的貨幣餘額。
  - `currency_config.json`: 設定貨幣系統的參數，如轉帳手續費。
  - `custom_commands.json`: 儲存伺服器的自訂關鍵詞觸發回應。
  - `giveaway_data.json`: 儲存進行中抽獎活動的資訊。
  - `goodbye_messages.json`: 儲存伺服器的再見訊息設定。
  - `leveling_config.json`: 設定等級系統的相關參數，如經驗值計算公式。
  - `leveling_data.json`: 儲存使用者的等級、經驗值和代幣數據。
  - `react_roles.json`: 儲存反應身分組面板的設定。
  - `shop_data.json`: 儲存商店中可購買的物品資訊。
  - `tickets.json`: 儲存票務系統的相關資訊，如活躍中的票券和面板訊息 ID。
  - `welcome_messages.json`: 儲存伺服器的歡迎訊息設定。

## 安裝與設定

### 1. 前置作業

- 確保您已安裝 Python 3.8 或更高版本。
- 建立一個 Discord 機器人應用程式並取得您的 Bot Token。
- 取得一個天氣 API 金鑰（來自中央氣象署）。

### 2. 檔案設定

- **`config.py`**:
    - 將 `BOT_TOKEN` 替換為您的 Discord Bot Token。
    - 將 `WEATHER_API_KEY` 替換為您的天氣 API 金鑰。

- **`requirements.txt`**:
    - 專案需要 `discord.py` 和 `requests` 等函式庫。
    - 您可以使用以下指令安裝所有依賴套件：

    ```bash
    pip install -r requirements.txt
    ```

- **`cogs/` 資料夾**:
    - 為了方便管理，您可以將所有 `.json` 檔案移動到一個獨立的 `data/` 資料夾中。
    - 若您移動檔案，請務必更新各個 `cogs` 檔案中的檔案路徑。

### 3. 啟動機器人

- 在終端機中執行以下指令：

```bash
python main.py
