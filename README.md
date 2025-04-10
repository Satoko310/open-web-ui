# 日本語対応 RAG システム

このシステムは、日本語テキストに最適化されたRetrieval-Augmented Generation (RAG) システムです。ベクトル検索とBM25を組み合わせたハイブリッド検索を使用し、高精度な文書検索と回答生成を実現します。

## 特徴

- 日本語形態素解析による高精度な文書検索
- ベクトル検索とBM25のハイブリッド検索
- マルチリンガルな埋め込みモデルの使用
- スコアベースの文書ランキング
- 文書ソースの追跡と引用

## 必要条件

- Python 3.8以上
- Ollama
- 必要なPythonパッケージ

## セットアップ

1. 必要なパッケージのインストール:

```bash
pip install -r requirements.txt
```

2. Ollamaのインストールと設定:
   - [Ollama公式サイト](https://ollama.ai)からOllamaをインストール
   - gemma3:12bモデルをダウンロード:
     ```bash
     ollama pull gemma3:12b
     ```

## 使い方

### サーバーの起動

api.pyを実行してサーバーを起動します：

```bash
python api.py
```

### APIエンドポイント

1. ドキュメントの追加:
```bash
curl -X POST "http://localhost:8000/add_document" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@/path/to/your/document.jsonl"
```

2. 質問の実行:
```bash
curl -X POST "http://localhost:8000/query" \
     -H "Content-Type: application/json" \
     -d '{"question": "あなたの質問をここに"}'
```

### ドキュメントフォーマット

ナレッジベースに追加するドキュメントは以下のJSONL形式である必要があります：

```jsonl
{"text": "文書の本文", "chapter": "章タイトル", "section": "セクションタイトル", "id": "一意のID"}
```

### 検索システムの仕組み

1. **ハイブリッド検索**:
   - ベクトル検索（Sentence Transformers）
   - BM25検索（Okapi BM25）
   - スコアの組み合わせによるランキング

2. **回答生成**:
   - 上位3件の関連文書を使用
   - 重要度に基づく情報の優先順位付け
   - ソース情報の明記

## 設定

`rag_system.py`で以下の設定を変更できます：

- `model_name`: 使用するOllamaモデル（デフォルト: "gemma3:12b"）
- `data_dir`: ナレッジベースのディレクトリ（デフォルト: "knowledge_base"）
- `top_k`: 検索結果の数（デフォルト: 3）
- `alpha`: ベクトル検索とBM25のバランス（デフォルト: 0.5）

## 注意事項

- ナレッジベースは起動時に自動的に読み込まれます
- 新しいドキュメントを追加した場合、システムは自動的に再初期化されます
- 大量のドキュメントを扱う場合はメモリ使用量に注意してください 