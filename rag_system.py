import json
import os
import shutil

import numpy as np
import ollama
from janome.tokenizer import Tokenizer
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer


class HybridRetriever:
    """ベクトル検索とBM25を組み合わせたハイブリッド検索"""
    def __init__(self, texts: list[str], metadata: list[dict] = list()):
        self.tokenizer = Tokenizer()
        self.texts = texts
        self.metadata = metadata if metadata else [{}] * len(texts)

        # Janomeを用いたテキストの形態素解析
        self.tokenized_texts = []
        for text in self.texts:
            tokens = self.tokenizer.tokenize(text)
            words = [token.base_form for token in tokens if token.part_of_speech.split(',')[0] in ['名詞', '動詞', '形容詞', '副詞']]
            self.tokenized_texts.append(words)

        # BM25の初期化
        self.bm25 = BM25Okapi(self.tokenized_texts)

        # Embedding modelの初期化
        self.model = SentenceTransformer('intfloat/multilingual-e5-base')
        self.embeddings = self.model.encode(texts)

    def retrieve(self, query: str, top_k: int = 1, alpha: float = 0.5) -> list[dict]:
        # ベクトルの類似度スコアの計算
        query_embedding = self.model.encode(query)
        vector_scores = np.dot(self.embeddings, query_embedding)
        max_vector_score = max(vector_scores) if any(vector_scores) else 1.0
        normalized_vector_scores = vector_scores / max_vector_score if max_vector_score > 0 else vector_scores

        # BM25スコアの計算
        query_tokens = self.tokenizer.tokenize(query)
        query_words = [token.base_form for token in query_tokens
                       if token.part_of_speech.split(',')[0] in ['名詞', '動詞', '形容詞', '副詞']]
        bm25_scores = self.bm25.get_scores(query_words)
        max_bm25_score = max(bm25_scores) if any(bm25_scores) else 1.0
        normalized_bm25_scores = bm25_scores / max_bm25_score if max_bm25_score > 0 else bm25_scores

        # スコアの組み合わせ
        combined_scores = alpha * normalized_vector_scores + (1 - alpha) * normalized_bm25_scores

        # 上位k件の結果を返す（スコアの高い順）
        top_indices = np.argsort(combined_scores)[-top_k:][::-1]
        results = []
        for idx in top_indices:
            result = {
                'text': self.texts[idx],
                'score': float(combined_scores[idx]),
                'vector_score': float(normalized_vector_scores[idx]),
                'bm25_score': float(normalized_bm25_scores[idx]),
                **self.metadata[idx]
            }
            results.append(result)

        # スコアの高い順にソート
        results.sort(key=lambda x: x['score'], reverse=True)
        return results


class RAGSystem:
    def __init__(self, data_dir="knowledge_base", model_name="mistral"):
        # データディレクトリの作成（存在しない場合）
        os.makedirs(data_dir, exist_ok=True)
        self.data_dir = data_dir
        self.model_name = model_name

        # 検索システムの初期化
        self.documents = []
        self.retriever = None
        self.initialize_system()

    def initialize_system(self):
        """システムの初期化"""
        if os.path.exists(self.data_dir) and any(os.scandir(self.data_dir)):
            # ドキュメントの読み込み
            self.documents = []
            for file in os.listdir(self.data_dir):
                file_path = os.path.join(self.data_dir, file)
                if os.path.isfile(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            try:
                                doc = json.loads(line.strip())
                                self.documents.append(doc)
                            except json.JSONDecodeError:
                                continue

            # 検索システムの初期化
            if self.documents:
                self.retriever = HybridRetriever(
                    texts=[doc['text'] for doc in self.documents],
                    metadata=[
                        {
                            'id': doc.get('id', ''),
                            'chapter': doc.get('chapter', ''),
                            'section': doc.get('section', '')
                        }
                        for doc in self.documents
                    ]
                )

    def add_document(self, file_path):
        """新しい文書をナレッジベースに追加"""
        filename = os.path.basename(file_path)
        dest_path = os.path.join(self.data_dir, filename)
        shutil.copy2(file_path, dest_path)
        # システムを再初期化
        self.initialize_system()

    def query(self, question: str) -> dict:
        """質問に対する回答を生成"""
        if not self.documents:
            return {
                "answer": "エラー: ナレッジベースが空です。先にドキュメントを追加してください。",
                "contexts": []
            }

        try:
            # コンテキストの取得
            retrieved_contexts = self.retriever.retrieve(question, top_k=3)
            contexts_with_scores = [
                {
                    "text": item['text'],
                    "source": f"{item['chapter']} - {item['section']}",
                    "score": f"{item['score']:.4f}",
                    "vector_score": f"{item['vector_score']:.4f}",
                    "bm25_score": f"{item['bm25_score']:.4f}"
                }
                for item in retrieved_contexts
            ]

            # コンテキストを重要度順に並べて表示（スコアの高い順）
            context_parts = []
            for i, item in enumerate(retrieved_contexts, 1):
                relevance = "非常に関連性が高い" if i <= 2 else "参考情報"
                context_parts.append(
                    f"[重要度: {relevance}]\n"
                    f"[出典: {item['chapter']} - {item['section']}]\n"
                    f"[スコア: {item['score']:.4f}]\n"
                    f"{item['text']}\n"
                )
            # プロンプトの組み立て
            context_text = '---\n'.join(context_parts)

            # Ollamaで回答を生成
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "あなたは学校心臓検診に関する文献に基づいて質問に答える、医学的に正確かつ丁寧な医療アシスタントです。\n"
                            "以下のルールに従って回答してください：\n"
                            "1. 『重要度: 非常に関連性が高い』の情報を最優先して参照すること。\n"
                            "2. 抜粋をそのまま使用せず、読者にわかりやすい自然な日本語に要約・言い換えること。\n"
                            "3. 回答の最後までしっかりと出力し、途中で途切れないようにすること。\n"
                            "4. 使用した情報の出典（章・出典名）を明記すること。\n"
                            "5. 医療専門家に向けた内容として、用語の正確性と論理性を重視すること。"
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            "以下のコンテキストは、「学校心臓検診」に関する資料から抽出したテキストです。\n"
                            "『重要度: 非常に関連性が高い』のものを最優先して使用してください。\n\n"
                            f"コンテキスト:\n{context_text}\n\n質問:\n{question}"
                        )
                    }
                ],
                stream=False,
            )

            return {
                "answer": response.message.content,
                "contexts": contexts_with_scores
            }

        except Exception as e:
            return {
                "answer": f"エラー: 質問の処理中にエラーが発生しました - {str(e)}",
                "contexts": []
            }
