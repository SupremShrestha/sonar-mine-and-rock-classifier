from django.urls import path

from . import views

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('classify/', views.predict_view, name='home'),
    path('predictions/<int:pk>/', views.prediction_detail, name='prediction_detail'),
    path('history/', views.history_view, name='history'),
]