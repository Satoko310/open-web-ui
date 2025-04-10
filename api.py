from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
from rag_system import RAGSystem
import logging

# ロギングの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORSの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静的ファイルの設定
os.makedirs("static", exist_ok=True)

# HTMLテンプレート
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>RAG System</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        .container {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        .upload-section, .query-section {
            border: 1px solid #ccc;
            padding: 20px;
            border-radius: 5px;
        }
        textarea {
            width: 100%;
            height: 100px;
            margin-bottom: 10px;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        button:hover {
            background-color: #45a049;
        }
        #response, #contexts {
            white-space: pre-wrap;
            border: 1px solid #ccc;
            padding: 10px;
            margin-top: 10px;
            border-radius: 5px;
        }
        .context-item {
            margin-bottom: 10px;
            padding: 10px;
            background-color: #f5f5f5;
            border-radius: 5px;
        }
        .context-source {
            font-weight: bold;
        }
        .context-text {
            margin-top: 5px;
        }
        .context-score {
            color: #666;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="upload-section">
            <h2>ドキュメントのアップロード</h2>
            <input type="file" id="file" />
            <button onclick="uploadFile()">アップロード</button>
        </div>
        
        <div class="query-section">
            <h2>質問</h2>
            <textarea id="question" placeholder="質問を入力してください"></textarea>
            <button onclick="askQuestion()">質問する</button>
            <h3>回答:</h3>
            <div id="response"></div>
            <h3>参照したコンテキスト:</h3>
            <div id="contexts"></div>
        </div>
    </div>

    <script>
        async function uploadFile() {
            const fileInput = document.getElementById('file');
            const file = fileInput.files[0];
            if (!file) {
                alert('ファイルを選択してください');
                return;
            }

            const formData = new FormData();
            formData.append('file', file);

            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                const result = await response.json();
                alert(result.message);
            } catch (error) {
                alert('エラーが発生しました: ' + error);
            }
        }

        async function askQuestion() {
            const question = document.getElementById('question').value;
            if (!question) {
                alert('質問を入力してください');
                return;
            }

            try {
                const response = await fetch('/query', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ text: question })
                });
                const result = await response.json();
                
                // 回答を表示
                document.getElementById('response').textContent = result.answer;
                
                // コンテキストを表示
                const contextsDiv = document.getElementById('contexts');
                contextsDiv.innerHTML = result.contexts.map(context => `
                    <div class="context-item">
                        <div class="context-source">出典: ${context.source}</div>
                        <div class="context-text">${context.text}</div>
                        <div class="context-score">
                            総合スコア: ${context.score}<br>
                            ベクトル検索スコア: ${context.vector_score}<br>
                            BM25スコア: ${context.bm25_score}
                        </div>
                    </div>
                `).join('');
            } catch (error) {
                alert('エラーが発生しました: ' + error);
            }
        }
    </script>
</body>
</html>
"""

# RAGシステムのインスタンスを作成
try:
    rag = RAGSystem(model_name="gemma3:12b")
    logger.info("RAGSystem initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize RAGSystem: {e}")
    rag = None

class Question(BaseModel):
    text: str

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTML_TEMPLATE

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        if not rag:
            raise HTTPException(status_code=500, detail="RAGSystem not initialized")
        
        # 一時ファイルとして保存
        temp_path = f"temp_{file.filename}"
        try:
            with open(temp_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            # RAGシステムに追加
            rag.add_document(temp_path)
            
            return {"message": "ファイルが正常にアップロードされました"}
        finally:
            # 一時ファイルを削除
            if os.path.exists(temp_path):
                os.remove(temp_path)
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
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 