from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .models import Notification 

@login_required
def fetch_notifications(request):
    unread_pool = Notification.objects.filter(user=request.user, is_read=False)
    total_unread = unread_pool.count()
    
    notifications = unread_pool[:10]
    data = [{
        'id': n.id,
        'type': n.notification_type,
        'message': n.message,
        'created_at': n.created_at.strftime('%b %d, %H:%M')
    } for n in notifications]
    
    return JsonResponse({'notifications': data, 'unread_count': total_unread})


@login_required
@require_POST
def mark_notifications_read(request):
    """Flags all user alerts as read when they open up or click clear on the panel."""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'ok': True})