"""mehr_takhfif URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles import views
from django.urls import path, include, re_path
from mehr_takhfif.settings_var import SAFE_IP

from mehr_takhfif import settings
from django.contrib.sitemaps.views import sitemap, index
from server.sitemap import *

sitemap = [
    path('sitemap.xml', index, {'sitemaps': {'product': ProductSitemap, 'category': CategorySitemap}},
         name='django.contrib.sitemaps.views.index'),
    path('<section>-sitemap.xml', sitemap, {'sitemaps': {'product': ProductSitemap, 'category': CategorySitemap}},
         name='django.contrib.sitemaps.views.sitemap')]

urlpatterns = [
                  path('admin/', include('mtadmin.urls')),
                  path('jet/', include('jet.urls', 'jet')),
                  path('jet/dashboard/', include('jet.dashboard.urls', 'jet-dashboard')),
                  path('superuser/', admin.site.urls),
                  path('', include('server.urls')),
                  # path('iprestrict/', include('iprestrict.urls', namespace='iprestrict')),
                  path('admin/dashboard/', include('mtadmin.dashboard_urls')),
                  path('admin/doc/', include('django.contrib.admindocs.urls')),
              ] + sitemap

handler404 = 'server.views.error.not_found'

if settings.DEBUG and SAFE_IP == 'localhost':
    urlpatterns += [path(r'silk/', include('silk.urls', namespace='silk'))]
urlpatterns += [re_path(r'^static/(?P<path>.*)$', views.serve), ]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
# # urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
#
import debug_toolbar

urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
