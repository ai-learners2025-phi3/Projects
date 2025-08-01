import chromadb
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
from typing import List, Dict
import hashlib
_embedding_model = None
class RAGService:
    def __init__(self, api_key: str, db_name: str = "news_db", model_name: str = "gemini-1.5-flash"):
        """
        初始化 RAG 服務，設定 ChromaDB 和 Gemini 模型。
        """
        self.db_name = db_name
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(name=self.db_name)
        # self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        global _embedding_model
        if _embedding_model is None:
            raise RuntimeError("Embedding 模型尚未載入。請確認應用程式已啟動。")
        self.embedding_model = _embedding_model
        genai.configure(api_key=api_key)
        self.gemini_model = genai.GenerativeModel(model_name)
    
    def generate_unique_id(self, article: Dict) -> str:
        """
        使用文章的標題和摘要生成一個穩定的唯一 ID。
        """
        title = article.get('title', '')
        summary = article.get('summary', '')
        # 結合標題和摘要，並使用 SHA-256 雜湊
        combined_text = f"{title}_{summary}"
        return hashlib.sha256(combined_text.encode('utf-8')).hexdigest()

    def add_articles(self, articles: List[Dict]):
        """
        將文章資料轉換成向量並存入 ChromaDB。
        此函式會為每篇文章生成一個唯一的 ID，並避免重複添加。
        """
        print("📢 正在進行資料 Embedding 處理...")
        documents = []
        metadatas = []
        ids = []

        try:
            # 從資料庫中獲取所有已存在的 ID
            existing_ids_in_db = set(self.collection.get(include=[])['ids'])
        except Exception:
            existing_ids_in_db = set()

        # 💡 新增一個集合，用於追蹤當前批次中已處理的 ID
        ids_in_current_batch = set()

        for d in articles:
            # 為每篇文章生成一個唯一的 ID
            article_id = self.generate_unique_id(d)
            
            # 只有當 ID 不存在於資料庫中 AND 不存在於當前批次中時才進行添加
            if article_id not in existing_ids_in_db and article_id not in ids_in_current_batch:
                # 檢查必要的欄位是否存在，以防 KeyError
                if 'summary' in d and 'title' in d:
                    documents.append(d['summary'])
                    metadatas.append({'title': d['title'], 'sentiment': d.get('sentiment'), 'category': d.get('category')})
                    ids.append(article_id)
                    # 💡 將 ID 加入到當前批次的追蹤集合中
                    ids_in_current_batch.add(article_id)
                else:
                    print(f"⚠️ 警告：文章缺少 'summary' 或 'title' 欄位，已跳過：{d}")
            else:
                # 如果文章 ID 已存在於資料庫或當前批次中，則跳過
                pass # print(f"ℹ️ 文章已存在或為重複，已跳過 ID: {article_id}")
        
        if documents:
            embeddings = self.embedding_model.encode(documents).tolist()
            self.collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            print(f"✅ {len(documents)} 篇文章已成功加入資料庫。")
        else:
            print("ℹ️ 沒有新文章需要加入資料庫。")

    def query(self, user_query: str, n_results: int = 5) -> str:
        """
        處理使用者查詢，並使用 RAG 生成最終回答。
        """
        print("➡️ 接收到查詢，開始檢索...")
        try:
            results = self.collection.query(
                query_texts=[user_query],
                n_results=n_results
            )
            relevant_docs = results['documents'][0]
            print("✅ 檢索完成，找到文件數量：", len(relevant_docs))
        except Exception as e:
            print(f"❌ 檢索時發生錯誤: {e}")
            return "查詢資料庫時發生錯誤，請稍後再試。"

        if not relevant_docs:
            return "很抱歉，我無法在現有資料中找到相關資訊。"

        context_str = "\n".join(relevant_docs)
        prompt = f"""
        你是一位擅長利用大數據分析時事的分析師，以下是一些近期新聞摘要資料，
        請根據這些資料回答使用者的問題，不要產出跟問題不相關的內容，
        直接給回答，不用前言。
        ---
        {context_str}
        ---
        使用者問題：{user_query}
        請用條列方式回答問題，並指出整體情緒趨勢與議題重點,最後給出結論。
        """.strip()
        
        try:
            print("➡️ 正在呼叫 Gemini API 進行生成...")
            response = self.gemini_model.generate_content(prompt)
            print("✅ Gemini 回應成功。")
            return response.text
        except Exception as e:
            print(f"❌ Gemini API 呼叫失敗: {e}")
            return f"生成回答時發生錯誤：{e}"