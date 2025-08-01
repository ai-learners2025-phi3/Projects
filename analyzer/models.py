from django.db import models
from django.conf import settings

# Create your models here.
class News(models.Model):
    keyword = models.CharField(max_length=20,db_index=True, default='新聞') # 對應的主題關鍵字
    source = models.CharField(max_length=20)                # 資料來源
    title = models.CharField(max_length=255)                # 新聞標題
    publish_date = models.DateTimeField()                   # 發布日期
    summary = models.TextField()                            # 新聞摘要
    tags = models.JSONField()                               # 詞語標籤
    url = models.URLField(unique=True)                      # 新聞網址（不可重複）
    category = models.CharField(max_length=100)             # 類別
    sentiment = models.CharField(max_length=2)              # 情緒分類
    sentiment_score = models.FloatField()                   # 情緒分數
    created_at = models.DateTimeField(auto_now_add=True)    # 寫入時間
    searches = models.ManyToManyField('HistorySearch', related_name='related_news', blank=True)
    class Meta:
        db_table = 'News'
    def __str__(self):
        return f"[{self.source}] {self.title}"
class Posts(models.Model):
    keyword = models.CharField(max_length=20, db_index=True)
    source = models.CharField(max_length=20)
    title = models.CharField(max_length=255)   
    publish_date = models.DateTimeField()
    summary = models.TextField()
    comments = models.JSONField() 
    url = models.URLField(unique=True)
    sentiment = models.CharField(max_length=2)
    sentiment_score = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    searches = models.ManyToManyField('HistorySearch', related_name='related_posts', blank=True)
    class Meta:
        db_table = 'Posts'

    def __str__(self):
        return f"[{self.source}] {self.title}" 
class AnalysisResult(models.Model):
    keyword = models.CharField(max_length=20, db_index=True,default="default")
    positive_count = models.IntegerField()
    negative_count = models.IntegerField()
    neutral_count = models.IntegerField()
    cate_count = models.JSONField()  # 類別統計
    tag_image = models.TextField()   # 圖片 URL
    top_word = models.JSONField()    # 前 N 詞頻
    trend_labels = models.JSONField()  # 折線圖日期軸
    trend_values = models.JSONField()  # 折線圖對應數值
    report = models.TextField()      # AI 生成功能摘要

    pos_count = models.IntegerField(default=0.0)
    neg_count = models.IntegerField(default=0.0)
    neu_count = models.IntegerField(default=0.0)
    sour_count = models.JSONField(default=dict)  # 類別統計
    post_image = models.TextField(default='')   # 圖片 URL
    post_top_word = models.JSONField(default=dict)    # 前 N 詞頻
    post_trend_labels = models.JSONField(default=list)  # 折線圖日期軸
    post_trend_values = models.JSONField(default=list)  # 折線圖對應數值
    post_report = models.TextField(default='')      # AI 生成功能摘要
    created_at = models.DateTimeField(auto_now_add=True)
    search = models.ForeignKey('HistorySearch', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="相關搜尋")
    class Meta:
        db_table = 'AnalysisResult'



    def __str__(self):
        # 檢查 self.search 是否存在，以避免 AttributeError
        if self.search:
            return f"分析結果：{self.search.keyword} (使用者: {self.search.user.username}) ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
        else:
            # 如果沒有關聯的 HistorySearch，則使用 AnalysisResult 自己的 keyword 欄位
            return f"分析結果：{self.keyword} (無關聯搜尋) ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
    
class HistorySearch(models.Model):
    keyword = models.CharField(max_length=20)  
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='search_history')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'HistorySearch'
        ordering = ['-created_at']  # 預設按時間倒序排列
    
    def __str__(self):
        return f"{self.user.username} 搜尋「{self.keyword}」@{self.created_at}"
# python manage.py makemigrations
# python manage.py migrate
