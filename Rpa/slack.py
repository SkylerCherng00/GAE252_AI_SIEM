import os, io, time, logging, asyncio, requests
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from endpoint import endpoint_url

logging.basicConfig(level=logging.INFO)

# ---------------- 共用 ---------------- #

def _get_slack_token() -> str:
    """向 MsgCenter 取 Slack Bot Token，失敗則退回 .env"""
    try:
        r = requests.get(endpoint_url+"config_rpa", timeout=3)
        r.raise_for_status()
        return r.json()["configs"]["Slack"]["slack_bot_token"]
    except Exception as e:
        logging.warning("取 token 失敗，fallback .env: %s", e)
        return os.getenv("SLACK_BOT_TOKEN", "")

_slack: Optional[WebClient] = None
def slack() -> WebClient:
    global _slack
    if _slack is None:
        _slack = WebClient(token=_get_slack_token())
    return _slack

def channel_id(name: str) -> Optional[str]:
    logging.info(f"查找頻道 ID: {name}")
    try:
        resp = slack().conversations_list(limit=1000)
        logging.info(f"取得 {len(resp['channels'])} 個頻道")
        for ch in resp["channels"]:
            if ch["name"] == name.lstrip("#"):
                logging.info(f"找到匹配頻道: {ch['name']} -> {ch['id']}")
                return ch["id"]
        logging.warning(f"未找到頻道: {name}")
    except SlackApiError as e:
        logging.error("conversations.list 失敗: %s", e.response["error"])
    return None

async def chat(channel: str, text: str):
    try:
        await asyncio.to_thread(
            slack().chat_postMessage,
            channel=channel,
            text=text,
            mrkdwn=True
        )
    except SlackApiError as e:
        logging.error("chat_postMessage 失敗: %s", e.response["error"])
        raise

async def join_channel_if_needed(channel: str) -> bool:
    """嘗試加入頻道，如果已經在頻道中則跳過"""
    try:
        logging.info(f"嘗試加入頻道: {channel}")
        await asyncio.to_thread(slack().conversations_join, channel=channel)
        logging.info(f"成功加入頻道: {channel}")
        return True
    except SlackApiError as e:
        if e.response["error"] == "already_in_channel":
            logging.info(f"已經在頻道中: {channel}")
            return True
        else:
            logging.error(f"加入頻道失敗: {e.response['error']}")
            return False

async def upload_markdown(md_text: str, channel: str) -> dict:
    """
    上傳 Markdown，回傳 {'file_id', 'permalink_public'}
    channel：用於存檔的頻道 ID
    """
    logging.info(f"開始上傳 Markdown 到頻道: {channel}")
    logging.info(f"Markdown 內容長度: {len(md_text)} 字元")
    
    # 先嘗試加入頻道
    if not await join_channel_if_needed(channel):
        logging.warning(f"無法加入頻道 {channel}，嘗試直接上傳")
    
    ts = int(time.time())
    mem = io.BytesIO(md_text.encode("utf-8"))
    mem.name = f"{ts}.md"
    logging.info(f"檔案名稱: {mem.name}")

    try:
        # upload using v2 API
        logging.info("正在上傳檔案到 Slack (使用 v2 API)...")
        resp = await asyncio.to_thread(
            slack().files_upload_v2,
            channel=channel,
            file=mem,
            filename=mem.name,
            title="full_report.md"
        )
        logging.info(f"檔案上傳成功，回應: {resp}")
        file_id = resp["file"]["id"]
        logging.info(f"取得檔案 ID: {file_id}")

        # 一律使用 Slack permalink（在 Slack 內可直接查看）
        if "permalink" in resp["file"]:
            url = resp["file"]["permalink"]
            logging.info(f"使用 Slack permalink: {url}")
        else:
            logging.error("找不到 permalink")
            url = f"檔案 ID: {file_id} (請在 Slack 中查看)"
        
        return {"file_id": file_id, "permalink_public": url}
    except Exception as e:
        logging.error(f"上傳 Markdown 失敗: {str(e)}")
        logging.error(f"錯誤類型: {type(e)}")
        raise

# ---------------- FastAPI ---------------- #

app = FastAPI(title="Slack Alert Service")

# 定義請求模型

TEMPLATE = (
    "🚨 *{priority_level}*\n\n"
    "{short_report}\n\n"
    "📄 *Report*：{md_link}"
)

class MarkdownReq(BaseModel):
    content: str = Field(example="# Full Report\n\nDetails...")

class AlertReq(BaseModel):
    priority_level: str = Field(example="P2")
    calling_departments: List[str] = Field(example=["it-server"])
    short_report: str = Field(example="*來源* ...\n\n> 摘要 ...")
    md_content: str | None = Field(None, description="完整 Markdown 報告")

# ---- API Endpoints ---- #

@app.post("/markdown/upload")
async def markdown_upload(req: MarkdownReq):
    # 先找一個預設頻道 (若不存在就退 400)
    default_channel = channel_id("general") or channel_id("random")
    if not default_channel:
        raise HTTPException(400, "找不到可用頻道上傳檔案")
    info = await upload_markdown(req.content, default_channel)
    return {"ok": True, **info}


@app.post("/alert")
async def alert(req: AlertReq):
    logging.info(f"收到 Alert 請求: priority={req.priority_level}, departments={req.calling_departments}")
    logging.info(f"是否包含 md_content: {req.md_content is not None}")
    if req.md_content:
        logging.info(f"md_content 長度: {len(req.md_content)} 字元")
    
    # 1. resolve channels
    logging.info("解析頻道 ID...")
    found, miss = [], []
    for ch in req.calling_departments:
        logging.info(f"查找頻道: {ch}")
        cid = channel_id(ch)
        if cid:
            logging.info(f"找到頻道 {ch}: {cid}")
            found.append(cid)
        else:
            logging.warning(f"找不到頻道: {ch}")
            miss.append(ch)
    
    if not found:
        logging.error(f"沒有找到任何有效頻道: {miss}")
        raise HTTPException(404, f"找不到任何頻道: {miss}")

    # 2. 若有 md_content 先上傳一次 (取第一個頻道ID即可)
    md_link = "(未提供完整報告)"
    if req.md_content:
        logging.info(f"開始處理 Markdown 內容，使用頻道: {found[0]}")
        try:
            info = await upload_markdown(req.md_content, found[0])
            md_link = info["permalink_public"]
            logging.info(f"Markdown 上傳成功，取得連結: {md_link}")
        except Exception as e:
            logging.error(f"Markdown 上傳失敗: {str(e)}")
            md_link = "(報告上傳失敗)"

    # 3. 組訊息
    logging.info("組合訊息...")
    message = TEMPLATE.format(
        priority_level=req.priority_level,
        short_report=req.short_report,
        md_link=md_link
    )
    logging.info(f"最終訊息: {message}")

    # 4. 群播
    logging.info(f"開始群播到 {len(found)} 個頻道...")
    results = []
    for cid in found:
        try:
            logging.info(f"發送訊息到頻道: {cid}")
            await chat(cid, message)
            results.append({"channel_id": cid, "status": "success"})
            logging.info(f"成功發送到頻道: {cid}")
        except Exception as e:
            logging.error(f"發送到頻道 {cid} 失敗: {str(e)}")
            results.append({"channel_id": cid, "status": "error", "error": str(e)})

    response_data = {
        "ok": True,
        "results": results,
        "not_found_channels": miss,
        "md_link": None if md_link.startswith("(") else md_link
    }
    logging.info(f"回應資料: {response_data}")
    return response_data

# ---------------- main ---------------- #

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10002, reload=False)