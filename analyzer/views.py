from django.shortcuts import render, redirect
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q

import json
from datetime import datetime,timedelta


from .utils import _batch_save_news,_batch_save_posts,_save_analysis_result,news_work,posts_work
from .rag_service import RAGService
from .models import News, Posts, AnalysisResult, HistorySearch

def user_register(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        if User.objects.filter(username=username).exists():
            messages.error(request, '使用者名稱已存在')
        else:
            User.objects.create_user(username=username, password=password)
            messages.success(request, '註冊成功，請登入')
            return redirect('login')
    return render(request, 'pages/register.html')

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('index')
        else:
            messages.error(request, '帳號或密碼錯誤')
    return render(request, 'pages/login.html')

def user_logout(request):
    logout(request)
    return redirect('index')

#rag_instance = RAGService(api_key=settings.GEMINI_API_KEY)

def index(request):
    keyword_from_user = None
    is_default_search = True
    if request.method == 'POST':
        keyword_from_user = request.POST.get('keyword', '').strip()
        is_default_search = False
        # 確保關鍵字不為空字符串，避免搜索空白
        if not keyword_from_user:
            keyword_from_user = None # 如果是空字符串，則視為預設搜尋
            is_default_search = True

    # 調用核心數據處理函式
    context = get_or_fetch_data(request, user_search_keyword=keyword_from_user)
    context['is_default_search'] = is_default_search
    
    # 渲染模板
    return render(request, 'pages/index.html', context)
@csrf_exempt # 在開發階段為了方便，暫時關閉 CSRF 保護
def get_rag_response(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_query = data.get('user_query', '')

            # 每次 AJAX 請求都去檢查快取是否有資料
            cache_key = f"rag_articles_{request.session.session_key}"
            cached_articles = cache.get(cache_key)

            if cached_articles is None:
                # 如果快取過期，重新載入資料
                # 這裡的邏輯需要你自己定義，例如顯示錯誤訊息或重新從 work() 取得
                return JsonResponse({'error': '資料已過期，請重新提交關鍵字。'}, status=400)
            
            # 確保 rag_instance 已經有資料
            # 這裡我們假設在 index view 中已經添加過，所以直接查詢即可
            rag_instance = RAGService(api_key=settings.GEMINI_API_KEY)
            response_text = rag_instance.query(user_query)

            return JsonResponse({'response': response_text})

        except Exception as e:
            return JsonResponse({'error': f'發生錯誤: {e}'}, status=500)
    
    return JsonResponse({'error': '不支援的請求方法。'}, status=405)

def get_or_fetch_data(request, user_search_keyword=None):
    current_keyword = user_search_keyword if user_search_keyword else '新聞'
    _hours_ago = timezone.now() - timedelta(hours=6)

    articles_to_display = []
    posts_to_display = []
    analysis_result = None
    
    history_search_instance = None
    is_data_recent = False # 統一判斷新聞、貼文和分析結果是否都近期
    
    # --- 1. 處理 HistorySearch 記錄 ---
    if request.user.is_authenticated and user_search_keyword:
        # 登入用戶的明確搜尋
        history_search_instance, created = HistorySearch.objects.get_or_create(
            keyword=current_keyword,
            user=request.user,
            defaults={'created_at': timezone.now()} 
        )
        if not created:
            history_search_instance.created_at = timezone.now()
            history_search_instance.save()
        print(f"用戶 {request.user.username} 的搜尋紀錄 {'創建' if created else '更新'}：'{current_keyword}'")
    else:
        # 預設關鍵字或未登入用戶：使用匿名使用者
        try:
            anonymous_user = User.objects.get(username='_anonymous_search_user')
        except User.DoesNotExist:
            # 如果匿名使用者不存在，則嘗試創建（這應該在啟動時完成，但作為 fallback）
            print("警告：匿名使用者'_anonymous_search_user'不存在，嘗試創建。")
            #anonymous_user = User.objects.create_user(username='_anonymous_search_user', password='very_secure_random_password_that_doesnt_matter', is_active=False)
            from django.utils.timezone import now
            anonymous_user = User(
                username='_anonymous_search_user',
                is_active=False,
                last_login=now(),  # ✅ 避免 NULL 問題
            )
            anonymous_user.set_password('very_secure_random_password_that_doesnt_matter')
            anonymous_user.save()
            
            
            
        history_search_instance, created = HistorySearch.objects.get_or_create(
            keyword=current_keyword,
            user=anonymous_user, # 綁定到匿名使用者
            defaults={'created_at': timezone.now()}
        )
        if not created:
            history_search_instance.created_at = timezone.now()
            history_search_instance.save()
        print(f"匿名搜尋紀錄 {'創建' if created else '更新'}：'{current_keyword}'")

    # --- 2. 嘗試從資料庫查找最近的數據 ---
    # 檢查 News 表中是否有該關鍵字且 created_at 未超過 3 小時的數據
    # 這裡我們查找的是 News 和 Posts 自己關聯的 keyword
    condition1 = Q(searches=history_search_instance)
    condition2 = Q(keyword=current_keyword)
    condition3 = Q(created_at__gte=_hours_ago)
    conditions = condition1 | (condition2 & condition3)
    condition_a = Q(search=history_search_instance) | (condition2 & condition3)
    recent_news = News.objects.filter(
        conditions
    ).order_by('-created_at') # 按最新創建時間排序

    recent_posts = Posts.objects.filter(
        conditions
    ).order_by('-created_at')

    # 檢查 AnalysisResult 的時效性
    # 只有在有 history_search_instance (即登入用戶的明確搜尋) 時，才檢查其對應的 AnalysisResult
    # 否則 (預設關鍵字或未登入用戶)，直接視為沒有近期分析結果
    try:
        temp_analysis_result = AnalysisResult.objects.get(
            condition_a
        )
        analysis_result = temp_analysis_result
        is_data_recent = True
        print("AnalysisResult 已找到且未過期。")
    except AnalysisResult.DoesNotExist:
        print("AnalysisResult 不存在或已過期。")
        is_data_recent = False
    
    # 判斷是否需要重新爬蟲
    should_crawl = (

        not is_data_recent
    )

    if should_crawl:
        print(f"資料過期或不存在 (新聞/貼文或分析結果)，正在重新爬取和分析 '{current_keyword}'...")
        articles_to_display, analysis_n = news_work(current_keyword, settings.GEMINI_API_KEY)
        posts_to_display,analysis_p = posts_work(current_keyword,settings.GEMINI_API_KEY)
        # 把文章存進快取，供 RAG 使用
        #rag_instance = RAGService(api_key=settings.GEMINI_API_KEY)
        cache_key = f"rag_articles_{request.session.session_key}"
        cache.set(cache_key, articles_to_display, timeout=600)
        rag_instance = RAGService(api_key=settings.GEMINI_API_KEY)
        rag_instance.add_articles(articles_to_display)
        
        # --- 4. 儲存到資料庫 (News, Posts, AnalysisResult) ---
        # 批量儲存新聞
        _batch_save_news(articles_to_display, history_search_instance)
        # 批量儲存貼文
        _batch_save_posts(posts_to_display, history_search_instance)

        analysis_result = _save_analysis_result(analysis_n,analysis_p, history_search_instance,current_keyword)
    
        
    else: # 資料庫已有未過期的資料，直接使用
        print(f"資料庫中有 '{current_keyword}' 近 3 小時內的所有資料 (新聞/貼文/分析結果)，直接使用。")
        # 從資料庫中取出的 News/Posts 實例填充顯示列表
        for news_item in recent_news:
            articles_to_display.append({
                'title': news_item.title,
                'summary': news_item.summary,
                'news_url': news_item.url,
                'sentiment': news_item.sentiment,
                'sentiment_score': news_item.sentiment_score,
                'date': news_item.publish_date.strftime('%Y-%m-%d'),
                'category': news_item.category,
                'source': news_item.source,
            })
        for post_item in recent_posts:
            posts_to_display.append({
                'title': post_item.title,
                'summary': post_item.summary,
                'comments': post_item.comments,
                'post_url': post_item.url,
                'sentiment_display': post_item.sentiment,
                'sentiment_score': post_item.sentiment_score,
                'date': post_item.publish_date.strftime('%Y-%m-%d'),
                'source': post_item.source,
            })
        
        # 如果 analysis_result 仍然是 None（雖然理論上現在 should_crawl=False 時，它應該不會是 None），
        # 則從 news_work 獲取一個臨時的字典用於顯示。
        if analysis_result is None:
            _, temp_analysis_dict = news_work(current_keyword, settings.GEMINI_API_KEY)
            analysis_result = temp_analysis_dict
            print(f"為'{current_keyword}'獲取臨時分析結果以供顯示 (因資料庫無近期記錄)。")

    # 準備傳遞給模板的上下文 (使用 getattr 處理 ORM 物件或字典)
    context = {
        'keyword': current_keyword,
        'articles': articles_to_display,
        'posts':posts_to_display,
        'positive_count': int(getattr(analysis_result,'positive_count',analysis_result.get('positive_count',0)if isinstance(analysis_result, dict) else 0)),
        'negative_count': int(getattr(analysis_result,'negative_count',analysis_result.get('negative_count',0)if isinstance(analysis_result, dict) else 0)),
        'neutral_count':int(getattr(analysis_result,'neutral_count',analysis_result.get('neutral_count',0)if isinstance(analysis_result, dict) else 0)),
        'cate_count': getattr(analysis_result , 'cate_count', analysis_result .get('cate_count', {}) if isinstance(analysis_result , dict) else {}),
        'tag_image': getattr(analysis_result , 'tag_image', analysis_result .get('tag_image', '') if isinstance(analysis_result , dict) else ''),
        'top_word': getattr(analysis_result , 'top_word', analysis_result .get('top_word', {}) if isinstance(analysis_result , dict) else {}),
        'trend_labels': getattr(analysis_result , 'trend_labels', analysis_result .get('trend_labels', []) if isinstance(analysis_result , dict) else []),
        'trend_values': getattr(analysis_result , 'trend_values', analysis_result .get('trend_values', []) if isinstance(analysis_result , dict) else []),
        'report': getattr(analysis_result , 'report', analysis_result .get('report', '') if isinstance(analysis_result , dict) else ''),
        
        'post_positive_count': int(getattr(analysis_result,'pos_count',analysis_result.get('pos_count',0)if isinstance(analysis_result, dict) else 0)),
        'post_negative_count': int(getattr(analysis_result,'neg_count',analysis_result.get('neg_count',0)if isinstance(analysis_result, dict) else 0)),
        'post_neutral_count':int(getattr(analysis_result,'neu_count',analysis_result.get('neu_count',0)if isinstance(analysis_result, dict) else 0)),
        'sour_count': getattr(analysis_result , 'sour_count', analysis_result .get('sour_count', {}) if isinstance(analysis_result , dict) else {}),
        'post_image': getattr(analysis_result , 'post_image', analysis_result .get('post_image', '') if isinstance(analysis_result , dict) else ''),
        'post_top_word': getattr(analysis_result , 'post_top_word', analysis_result .get('post_top_word', {}) if isinstance(analysis_result , dict) else {}),
        'post_trend_labels': getattr(analysis_result , 'trend_labels', analysis_result .get('trend_labels', []) if isinstance(analysis_result , dict) else []),
        'post_trend_values': getattr(analysis_result , 'post_trend_values', analysis_result .get('post_trend_values', []) if isinstance(analysis_result , dict) else []),
        'post_report': getattr(analysis_result , 'post_report', analysis_result .get('post_report', '') if isinstance(analysis_result , dict) else ''),
    }
    
    return context

