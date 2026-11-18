# 《歸來者》— 暄、阿卉共同創作的 Analog Horror Blog

**作品作者：暄、阿卉。** 這是學生共同創作的虛構互動恐怖故事，並非 Chai 的個人作品。故事以一名失蹤後歸來者的 Blog 為敘事介面：某人受小說影響，企圖在森林中獻祭同行者，兩人卻遭遇會模仿人類的偽人，被取代後重新出現，行為與習慣逐漸失真。

一個能正常閱讀、但又處處藏著異常訊號的故事 Blog。包含 Flask 後端、SQL 文章資料庫、管理後台、四位數解謎以及非血腥突發驚嚇（可關閉、無閃光及音效）。

## 功能

- 角色自述、森林事件檔案、VHS 雜訊與異常系統提示
- 文章列表、搜尋、分類、文章閱讀（後端 API 提供資料）
- 顯示四位數密碼解謎，伺服器端驗證，正確後出現原創恐怖面孔
- 無聲音、無快速閃爍，訪客可事先關閉突發驚嚇；尊重系統減少動態效果設定
- 管理頁面 `/admin`（登入、新增、編輯、刪除、草稿）
- 本機 SQLite、正式環境可透過 `DATABASE_URL` 使用 PostgreSQL
- HTTP 安全標頭、基本登入頻率限制、CSRF token、參數化 SQL、內容作為純文字顯示

## 專案結構

```text
app.py                    Flask API、資料庫、登入、解謎驗證
requirements.txt          Python 套件
render.yaml               Render Web Service 設定
static/style.css          網站外觀
static/app.js             首頁互動
static/assets/            原創恐怖影像
static/admin.css          管理頁面外觀
templates/index.html      首頁
templates/login.html      登入頁
templates/dashboard.html  文章列表後台
templates/editor.html     文章編輯後台
tests/test_app.py         自動化 API 測試
```

## 本機執行

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

然後開啟 http://127.0.0.1:5000/ ，`/admin` 是管理後台。**請自行設定 `ADMIN_PASSWORD` 環境變數**（不要將密碼放在程式碼或 GitHub）。未設定時後台登入功能會停用。

本機示例（Linux/macOS，請替換為自己的密碼）：

```bash
export ADMIN_PASSWORD='your-strong-private-password'
export SECRET_KEY="$(python -c 'import secrets;print(secrets.token_hex(32))')"
python app.py
```

`.env.example` 僅提供環境變數名稱參考；本專案不會自動載入 `.env` 檔。若使用 .env，請自行在終端載入後啟動，且不要提交到 GitHub。

## Render 部署

1. 上傳此資料夾裡的**全部檔案**到 GitHub 儲存庫（`render.yaml` 放在根目錄）。
2. 在 Render 選 **New > Blueprint**，連結 GitHub 儲存庫，讀取 `render.yaml`。
3. Render 會要求設定 `ADMIN_PASSWORD` 及 `PUZZLE_ANSWER`，請把密碼設為自行保管的安全值；第一次測試的解謎答案可設為 `0417`。
4. `SECRET_KEY` 由 Blueprint 自動產生。部署後確認 `/health` 回應 `{"status":"ok"}`。
5. 如果不使用 Blueprint，也能建立 **Web Service**，Build Command `pip install -r requirements.txt`，Start Command `gunicorn --bind 0.0.0.0:$PORT app:app`。

### ⚠️ Render 免費服務的文章儲存問題

Render 免費 Web Service 的本機檔案系統是**暫時性**的，重新部署或重啟時 SQLite 資料庫可能會遺失。網站仍能運作，並重新載入原始示範文章，但**後台新文章不保證保存**。

想長期使用文章後台，請另行建立 PostgreSQL 資料庫（可選提供持久化服務的供應商），在 Render 的 **Environment** 中新增 `DATABASE_URL`，格式：

```
postgresql://USER:PASSWORD@HOST:5432/DB_NAME
```

**絕對不要**把真實 `DATABASE_URL`、`SECRET_KEY` 或 `ADMIN_PASSWORD` 寫到公開 GitHub。

## 更改網站內容

- 角色介紹、作者署名、作品卡片、導覽列：編輯 `templates/index.html`
- 視覺設計：編輯 `static/style.css`
- 異常訊息、動態：編輯 `static/app.js`
- 故事初始文章：編輯 `app.py` 的 `SEED_POSTS`（只在資料庫沒有文章時匯入）
- 解謎正確答案：後端環境變數 `PUZZLE_ANSWER`，預設 `0417`。同步修改文章裡的線索以保持可解。
- 新增文章：設定管理密碼後，從 `/admin` 登入，無需修改程式碼。

### 關於解謎

謎題線索分別出現在「森林訊號中斷紀錄」與「歸來之後的第十七格」文章，以及頁尾彩蛋。訪客依提示拼接四位數時間（示範答案 `0417`）。密碼驗證由伺服器完成，前端 JavaScript 不包含標準答案。**如果 GitHub 儲存庫公開，熟悉程式碼的人仍可能從示範文章或後端預設值推知答案；此謎題不應用於真正的認證或保護機密資料。**

## 基本測試

```bash
pip install pytest
pytest -q
```

> **作者：暄、阿卉。** 本站中的「記錄者」與「歸來者」為故事角色，並非學生本人。怪談、異常現象與恐怖面孔都是虛構效果。沒有追蹤訪客位置、收集個人資訊，也沒有第三方分析工具。

## 故事大綱

一名沉迷小說傳說的人認為森林中可以完成獻祭，邀請另一人同行，打算犧牲對方。兩人走進森林後，遭遇了外表可以模仿人類的偽人，原本的人類再也沒有走出來。幾天後，兩名與失蹤者長相相同的人回來了，表情僵硬，說話、慣用手和記憶中的行為都逐漸產生矛盾。故事中的 Blog 由其中一名「歸來者」繼續更新，散落的日誌、影像與隱藏檔案提供解謎線索。

解謎成功會顯示非血腥驚嚇畫面，訪客可預先關閉該效果。故事中的人物與事件皆屬虛構。

若網站已經部署、資料庫存在原版預設文章，啟動時只會自動更新**標題仍等於舊示範標題**的文章；已有不同標題的自訂文章不會覆蓋。
