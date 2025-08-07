import logging, asyncio
import requests
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

def get_slack_token_from_api() -> str:
    """從 API 取得 SLACK_BOT_TOKEN"""
    try:
        response = requests.get("http://0.0.0.0:10000/config/config_rpa")
        response.raise_for_status()
        config_data = response.json()
        return config_data["configs"]["Slack"]["slack_bot_token"]
    except Exception as e:
        logging.error(f"無法從 API 取得 SLACK_BOT_TOKEN: {e}")
        raise

# 初始化 FastAPI
app = FastAPI()

# 延遲初始化 Slack client
_client = None

def get_slack_client() -> WebClient:
    """取得 Slack client，如果還沒初始化則先初始化"""
    global _client
    if _client is None:
        _client = WebClient(token=get_slack_token_from_api())
    return _client

# 定義請求模型

alert_message_template = "🚨 *{priority_level}*\n\n{short_report}"

class AlertReq(BaseModel):
    priority_level: str = Field(example="P2", description="優先級別")
    calling_departments: List[str] = Field(example=["it-server", "security-team"], description="要通知的頻道名稱列表")
    short_report: str = Field(example="*來源*: Nginx\n*事件 ID*: `LX-20250805-001`\n*時間區間*: `2025-08-05 12:31~12:32`\n\n> 大量 500 伺服器錯誤，IP 203.0.113.7 疑似注入攻擊\n\n*建議處置：*\n1. 暫時封鎖來源 IP\n2. 檢查 `user_service` 資料庫連線\n3. 啟用 WAF SQL Injection Policy\n\n", description="詳細報告內容")

def get_channel_id_by_name(chan_name: str) -> Optional[str]:
    client = get_slack_client()
    try:
        response = client.conversations_list(limit=1000)
        for ch in response["channels"]:
            if ch["name"] == chan_name:
                return ch["id"]
    except SlackApiError as e:
        logging.error("conversations.list 失敗: %s", e.response["error"])
    return None

async def post_to_slack(channel_id: str, text: str):
    client = get_slack_client()
    try:
        await asyncio.to_thread(
            client.chat_postMessage,
            channel=channel_id,
            text=text,
            mrkdwn=True
        )
    except SlackApiError as e:
        logging.error("chat.postMessage 失敗: %s", e.response["error"])
        raise


def _list_channels():
    client = get_slack_client()
    try:
        response = client.conversations_list(limit=1000)
        channels = [{"name": ch["name"], "id": ch["id"]} for ch in response["channels"]]
        return {"channels": channels}
    except SlackApiError as e:
        raise HTTPException(status_code=500, detail=str(e))


# --------- API 端點 ---------

@app.post("/alert")
async def alert(request: AlertReq):
    # 格式化訊息
    formatted_message = alert_message_template.format(
        priority_level=request.priority_level,
        short_report=request.short_report
    )
    
    # 取得所有頻道 ID
    channel_ids = []
    not_found_channels = []
    
    for channel_name in request.calling_departments:
        channel_id = get_channel_id_by_name(channel_name)
        if channel_id:
            channel_ids.append(channel_id)
        else:
            not_found_channels.append(channel_name)
    
    if not channel_ids:
        raise HTTPException(
            status_code=404,
            detail=f"找不到任何指定的頻道: {request.calling_departments}"
        )
    
    # 發送到所有找到的頻道
    results = []
    for channel_id in channel_ids:
        try:
            await post_to_slack(channel_id, formatted_message)
            results.append({"channel_id": channel_id, "status": "success"})
        except Exception as e:
            results.append({"channel_id": channel_id, "status": "error", "error": str(e)})
    
    return {
        "ok": True, 
        "priority_level": request.priority_level,
        "calling_departments": request.calling_departments,
        "results": results,
        "not_found_channels": not_found_channels
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=12000)
    # 測試列出頻道
    # try:
    #     response = client.conversations_list(limit=1000)
    #     print(f"找到 {len(response['channels'])} 個頻道:")
    #     for ch in response['channels'][:5]:  # 只顯示前5個
    #         print(f"- {ch['name']} (ID: {ch['id']})")
    # except SlackApiError as e:
    #     print(f"錯誤: {e}")