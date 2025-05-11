from django.urls import path
from . import views

urlpatterns = [
    path('', views.interactive_page, name='interactive_page'),
    path('ml_page/', views.ml_page, name='ml_page'),  
    path('get-fields/', views.get_fields, name='get_fields'),
    path('ajax-predict/', views.ajax_predict, name='ajax_predict'),
    path('fetch-weather/', views.fetch_weather, name='fetch_weather'),
    path('get-predictions/', views.get_predictions, name='get_predictions'),
    path('dashboard/', views.dashboard_page, name='dashboard'),  
]
