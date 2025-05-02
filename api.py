import logging
import os

import uvicorn
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from rag_system import RAGSystem

# ロギングの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(debug=True)

# CORSの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# テンプレートディレクトリを指定
templates = Jinja2Templates(directory="templates")

# RAGシステムのインスタンスを作成
try:
    rag = RAGSystem(model_name="gemma3:27b")
    logger.info("RAGSystem initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize RAGSystem: {e}")
    rag = None


class Question(BaseModel):
    text: str


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        if not rag:
            raise HTTPException(status_code=500, detail="RAGSystem not initialized")

        # 一時ファイルとして保存
        temp_path = f"temp_{file.filename}"
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # RAGシステムに追加
        rag.add_document(temp_path)

        # 一時ファイルを削除
        if os.path.exists(temp_path):
            os.remove(temp_path)

        return {"message": "ファイルが正常にアップロードされました"}

    except Exception as e:
        logger.error(f"Error in upload_file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query")
async def query(question: Question):
    try:
        if not rag:
            raise HTTPException(status_code=500, detail="RAGSystem not initialized")

        response = rag.query(question.text)
        return response  # レスポンス全体をそのまま返す
    except Exception as e:
        logger.error(f"Error in query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=3000)
