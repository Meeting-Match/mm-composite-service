from django.urls import include, path

from . import views

urlpatterns = [
    path('postevent/', views.EventCreateView.as_view(), name='event-create')
]
