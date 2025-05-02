import argparse
import csv
import json
import os
import random
import time
from datetime import datetime
from typing import Dict, List, Set

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


# 問題データを保持するグローバル変数
current_questions: List[Dict] = []
current_question_index: int = 0
start_time: float = 0.0
used_question_ids: Set[str] = set()
is_practice_mode: bool = False  # 練習モードかどうかを示すフラグ


def load_questions() -> List[Dict]:
    """問答集(記述).csvから問題を読み込む"""
    questions = []
    try:
        with open('問答集(記述).csv', 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:  # 問題IDと問題文があることを確認
                    questions.append({
                        'id': row[0],
                        'question': row[1]
                    })
    except Exception as e:
        print(f"Error loading questions: {e}")
        # サンプル問題
        questions = [{
            'id': '1',
            'question': '8歳の患者。学校心臓検診の自動診断によりQT延長が検出された。次に行うべき対応として適切なのはどれか。'
        }]
    return questions


def save_answer(question: Dict, answer: str, time_spent: int) -> None:
    """回答と時間をoutput_essay.csvに保存"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        with open('output_essay.csv', 'a', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp,
                question['question'],
                answer,
                time_spent,
                len(answer)  # 文字数を記録
            ])
    except Exception as e:
        print(f"Error saving answer: {e}")


def save_used_questions() -> None:
    """使用した問題IDを保存"""
    try:
        with open('used_questions_essay.json', 'w', encoding='utf-8') as f:
            json.dump(list(used_question_ids), f)
    except Exception as e:
        print(f"Error saving used questions: {e}")


def load_used_questions() -> Set[str]:
    """使用した問題IDを読み込む"""
    try:
        if os.path.exists('used_questions_essay.json'):
            with open('used_questions_essay.json', 'r', encoding='utf-8') as f:
                return set(json.load(f))
    except Exception as e:
        print(f"Error loading used questions: {e}")
    return set()


class AnswerSubmission(BaseModel):
    """回答提出用のモデル"""
    answer: str
    timeSpent: int


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """トップページ表示 - 練習問題を表示"""
    global is_practice_mode
    is_practice_mode = True
    return templates.TemplateResponse(
        "quiz_essay.html",
        {
            "request": request,
            "question": {"id": "0", "question": "これは練習問題です"}
        }
    )


@app.get("/start", response_class=HTMLResponse)
async def start(request: Request):
    """本番問題開始"""
    global current_questions, current_question_index, start_time, used_question_ids, is_practice_mode
    is_practice_mode = False
    all_questions = load_questions()

    # 未使用の問題のみをフィルタリング
    available_questions = [q for q in all_questions if q['id'] not in used_question_ids]
    current_questions = random.sample(available_questions, min(5, len(available_questions)))

    # current_questionsが空の場合に警告を表示
    if len(current_questions) == 0:
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html lang="ja">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>エラー</title>
            </head>
            <body>
                <script>
                    alert("使用可能な問題がありません。used_questions.jsonを削除してください！");
                </script>
            </body>
            </html>
            """,
            status_code=400
        )

    current_question_index = 0
    start_time = time.time()

    # 選択した問題のIDを記録
    used_question_ids.update(q['id'] for q in current_questions)
    save_used_questions()

    return templates.TemplateResponse(
        "quiz_essay.html",
        {
            "request": request,
            "question": current_questions[current_question_index],
        }
    )


@app.post("/submit")
async def submit(submission: AnswerSubmission):
    """回答を受け取ってCSVに保存"""
    global current_question_index
    if is_practice_mode:  # 練習モードの場合は保存しない
        return JSONResponse({"practice": True})
    save_answer(current_questions[current_question_index], submission.answer, submission.timeSpent)
    current_question_index += 1

    if current_question_index >= len(current_questions):
        return JSONResponse({"success": True, "finished": True})
    return JSONResponse({"success": True, "finished": False})


@app.get("/next", response_class=HTMLResponse)
async def next_question(request: Request):
    """次の問題へリダイレクト"""
    return templates.TemplateResponse(
        "quiz_essay.html",
        {
            "request": request,
            "question": current_questions[current_question_index],
        }
    )


@app.get("/finish", response_class=HTMLResponse)
async def finish(request: Request):
    """終了画面を表示"""
    return templates.TemplateResponse("finish.html", {"request": request})


def main():
    parser = argparse.ArgumentParser(description='記述式問題出題システム')
    parser.add_argument('--reset', action='store_true', help='使用済み問題の履歴をリセット')
    args = parser.parse_args()

    global used_question_ids
    if args.reset:
        used_question_ids = set()
        if os.path.exists('used_questions_essay.json'):
            os.remove('used_questions_essay.json')
    else:
        used_question_ids = load_used_questions()

    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8081)  # ポートを8081に変更


if __name__ == "__main__":
    main()
