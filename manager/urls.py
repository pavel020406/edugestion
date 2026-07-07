"""
URL configuration for manager project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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


# ============================================================
# manager/urls.py — COMPLET avec app eleve
# ============================================================

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/',        admin.site.urls),

    
    path('',              include('administrateur.urls')),

 
    path('enseignant/',   include('enseignant.urls')),

   
    path('eleve/',        include('eleve.urls')),
    path('secretaire/', include('secretaire.urls')),
     path('parent/', include('parent.urls')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
