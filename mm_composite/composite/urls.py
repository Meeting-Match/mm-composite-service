from django.urls import include, path

from . import views

urlpatterns = [
    path('postevent/', views.EventCreateView.as_view(), name='event-create'),
    path('getevent/<int:event_id>/',
         views.EnrichedEventView.as_view(), name='get-event'),
    path('getavailability/<int:availability_id>/',
         views.EnrichedAvailabilityView.as_view(), name='get-event')
]
