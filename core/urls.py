from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from .views import contact, faq, health, home, privacy, robots, sitemap, terms


urlpatterns = [
    path('admin/', admin.site.urls),

    path('', home, name='home'),
    path('faq/', faq, name='faq'),
    path('privacy/', privacy, name='privacy'),
    path('terms/', terms, name='terms'),
    path('contact/', contact, name='contact'),
    path('health/', health, name='health'),
    path('robots.txt', robots, name='robots'),
    path('sitemap.xml', sitemap, name='sitemap'),

    path('accounts/', include('accounts.urls')),
    path('exams/', include('exams.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
