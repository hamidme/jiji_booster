from django.urls import path, include
from booster import views as booster_views

urlpatterns = [
    path('manifest.json', booster_views.pwa_manifest, name='manifest'),
    path('sw.js', booster_views.service_worker, name='service_worker'),
    path('icon-<int:size>.png', booster_views.icon_png, name='icon_png'),
    path('', include('booster.urls')),
]
