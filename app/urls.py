from django.conf.urls import url, include

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^details/$', views.details, name='details'),
    url(r'^details-update/$', views.details_update, name='details_update'),
    url(r'^generate/$', views.generate, name='generate'),
    url(r'^overview/$', views.overview, name='overview'),
    url('accounts/', include('django.contrib.auth.urls')),
]