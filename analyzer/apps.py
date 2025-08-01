from django.apps import AppConfig
import os

class AnalyzerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analyzer'

    def ready(self):
        """
        當應用程式準備好時，執行此函式。
        在這裡預先載入 Embedding 模型，以避免 Web 請求時的延遲。
        """
        # 確保這段程式碼只在主進程中執行，避免在多線程或多進程環境中重複執行
        # 'RUN_MAIN' 環境變數在 Django 啟動時的子進程中會被設定為 'true'
        if os.environ.get('RUN_MAIN', None) != 'true':
            return
        
        print("📢 Django 應用程式啟動中...")
        print("➡️ 正在檢查並預先載入 SentenceTransformer 模型...")
        
        try:
            from sentence_transformers import SentenceTransformer
            # 💡 導入整個模組，然後訪問其全域變數
            from . import rag_service 
            
            # 載入模型並將其實例賦值給 rag_service.py 中的全域變數
            rag_service._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            print("✅ SentenceTransformer 模型載入成功！")
        except Exception as e:
            print(f"❌ SentenceTransformer 模型載入失敗：{e}")
            print("請確認已安裝 'sentence-transformers' 套件，並檢查網路連線。")
        
        