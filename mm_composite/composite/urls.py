from django.urls import include, path
from . import views
import logging

logger = logging.getLogger('composite')

def log_request_with_correlation_id(view):
    """
    Decorator to log requests with Correlation ID at the URL level.
    """
    def wrapper(request, *args, **kwargs):
        correlation_id = getattr(request, 'correlation_id', 'N/A')
        logger.info(f"Request to URL '{request.path}' with method '{request.method}'", extra={'correlation_id': correlation_id})
        return view(request, *args, **kwargs)
    return wrapper

urlpatterns = [
    path('postevent/', log_request_with_correlation_id(views.EventCreateView.as_view()), name='event-create'),
    path('getevent/<int:event_id>/',
         log_request_with_correlation_id(views.EnrichedEventView.as_view()), name='get-event'),
    path('getavailability/<int:availability_id>/',
         log_request_with_correlation_id(views.EnrichedAvailabilityView.as_view()), name='get-event')
]
