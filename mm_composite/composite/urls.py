from django.urls import include, path
from graphene_django.views import GraphQLView
from django.views.decorators.csrf import csrf_exempt
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


class GraphQLContext:
    def __init__(self, request):
        self.request = request

    # class CustomGraphQLView(GraphQLView):
        # def get_context(self, request):
        # Add the Authorization token to the context
        # context = super().get_context(request)
        # print("About to assign the token to the context")
        # print(context)
        # context['request'] = request
        # print("About to return context")
    # return context


class CustomGraphQLView(GraphQLView):
    def get_context(self, request):
        # Use a custom context class to pass the request object
        context = GraphQLContext(request)
        return context


urlpatterns = [
    path('postevent/', log_request_with_correlation_id(views.EventCreateView.as_view()), name='event-create'),
    path('getevent/<int:event_id>/', log_request_with_correlation_id(views.EnrichedEventView.as_view()), name='get-event'),
    path('getavailability/<int:availability_id>/', log_request_with_correlation_id(views.EnrichedAvailabilityView.as_view()), name='get-event'),
    path("graphql/", log_request_with_correlation_id(csrf_exempt(CustomGraphQLView.as_view(graphiql=True)))),
]