from django.shortcuts import render
from .utils import work

def index(request):
    context = {}
    if request.method == "POST":
        keyword = request.POST.get('keyword')
        results = work(keyword)
        context = {
            'keyword': keyword,
            'articles': results['articles'],
            'positive_count': int(results['sentiment_count']['正面']),
            'negative_count': int(results['sentiment_count']['負面']),
            'neutral_count':int(results['sentiment_count']['中立']),
            'cate_count': results['category_stats'],
            'tag_image': results['tag_image'],
            'top_word': results['top_word'],
            'trend_labels': results['trend_labels'],
            'trend_values': results['trend_values'],
            'report': results['AIreport'],
        }
    return render(request, 'pages/index.html', context)
