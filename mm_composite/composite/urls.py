from django.urls import include, path
from graphene_django.views import GraphQLView
from django.views.decorators.csrf import csrf_exempt

from . import views


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
    path('postevent/', views.EventCreateView.as_view(), name='event-create'),
    path('getevent/<int:event_id>/',
         views.EnrichedEventView.as_view(), name='get-event'),
    path('getavailability/<int:availability_id>/',
         views.EnrichedAvailabilityView.as_view(), name='get-event'),
    path("graphql/", csrf_exempt(CustomGraphQLView.as_view(graphiql=True))),
]
