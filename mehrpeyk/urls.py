from django.urls import path
from django.views.decorators.cache import cache_page
from server.views.client import home
from .views import *

app_name = 'mehrpeyk'

urlpatterns = [
    path('add_mission', AddMission.as_view(), name='add_mission'),
    path('start_mission', StartMission.as_view(), name='start_mission'),
    path('end_mission', EndMission.as_view(), name='end_mission'),
    path('get_mission', GetMission.as_view(), name='get_mission'),
    path('update_location', UpdateLocation.as_view(), name='update_location'),
    path('sign_up', Signup.as_view(), name='sign_up'),
    path('resend_activation', ResendActivate.as_view(), name='resend_activation'),
    path('activate', Activate.as_view(), name='activate'),
    path('login', Login.as_view(), name='login'),
    path('splash', VersionInfo.as_view(), name='splash'),
    path('get_location/<str:factor>', GetLocation.as_view(), name='get_location'),
    path('get_factors', GetFactors.as_view(), name='get_factors'),
    path('get_locations', GetActiveLocations.as_view(), name='get_locations'),
]
