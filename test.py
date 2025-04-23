from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Set
import csv
import random
import time
from datetime import datetime
import argparse
import json
import os


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
    """問答集.csvから問題を読み込む"""
    questions = []
    try:
        with open('問答集.csv', 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 6:  # 問題文と4つの選択肢があることを確認
                    questions.append({
                        'id': row[0],
                        'question': row[1],
                        'choices': row[2:6]
                    })
    except Exception as e:
        print(f"Error loading questions: {e}")
        # サンプル問題
        questions = [{
            'id': '1',
            'question': '8歳の患者。学校心臓検診の自動診断によりQT延長が検出された。次に行うべき対応として適切なのはどれか。',
            'choices': [
                '直ちに薬物治療を開始する',
                '心臓超音波検査を行う',
                '再度手動でQT間隔を測定し、2次検診の要否を判断する',
                '問題ないと判断して経過観察とする'
            ]
        }]
    return questions


def save_answer(question: Dict, answer: str, time_spent: int) -> None:
    """回答と時間をoutput.csvに保存"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        with open('output.csv', 'a', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp,
                question['question'],
                answer,
                time_spent
            ])
    except Exception as e:
        print(f"Error saving answer: {e}")


def save_used_questions() -> None:
    """使用した問題IDを保存"""
    try:
        with open('used_questions.json', 'w', encoding='utf-8') as f:
            json.dump(list(used_question_ids), f)
    except Exception as e:
        print(f"Error saving used questions: {e}")


def load_used_questions() -> Set[str]:
    """使用した問題IDを読み込む"""
    try:
        if os.path.exists('used_questions.json'):
            with open('used_questions.json', 'r', encoding='utf-8') as f:
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
        "quiz.html",
        {
            "request": request,
            "question": {"id": "0", "question": "これは練習問題です", "choices": ["選択肢1", "選択肢2", "選択肢3", "選択肢4"]},
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

    # 未使用の問題が5問未満の場合は、すべての問題から選択
    if len(available_questions) < 5:
        available_questions = all_questions

    current_questions = random.sample(available_questions, min(5, len(available_questions)))
    current_question_index = 0
    start_time = time.time()

    # 選択した問題のIDを記録
    used_question_ids.update(q['id'] for q in current_questions)
    save_used_questions()

    return templates.TemplateResponse(
        "quiz.html",
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
        "quiz.html",
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
    parser = argparse.ArgumentParser(description='問題出題システム')
    parser.add_argument('--reset', action='store_true', help='使用済み問題の履歴をリセット')
    args = parser.parse_args()

    global used_question_ids
    if args.reset:
        used_question_ids = set()
        if os.path.exists('used_questions.json'):
            os.remove('used_questions.json')
    else:
        used_question_ids = load_used_questions()

    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)


if __name__ == "__main__":
    main()
