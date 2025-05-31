"""
URL configuration for project_manage project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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
from django.contrib import admin
from django.urls import path
from manageapp import views as manage_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login_signup/', manage_views.login_signup, name='login_signup'),
    path('logout/', manage_views.logout_view, name='logout'),
    path('upload_excel/', manage_views.upload_excel, name='upload_excel'),
    path('upload_zip/', manage_views.upload_zip, name='upload_zip'),

    path('delete/', manage_views.delete_data, name='delete'),
    path('attendance/', manage_views.attendance_view, name='attendance'),
    path('video_feed/', manage_views.video_feed, name='video_feed'),
    path('get_message/', manage_views.get_message, name='get_message'),
    path('delete_account/', manage_views.delete_account, name='delete_account'),
    path('stop_video_feed/', manage_views.stop_video_feed, name='stop_video_feed'),
    path('mark_message_seen/', manage_views.mark_message_seen, name='mark_message_seen'),
    path('download_attendance/', manage_views.download_attendance, name='download_attendance'),

    path('', manage_views.proindex, name='proindex'),
    path('sarbik/', manage_views.sarbik_view, name='sarbik'),
    path('tania/', manage_views.tania_view, name='tania'),
    path('sarbani/', manage_views.sarbani_view, name='sarbani'),
    path('manish/', manage_views.manish_view, name='manish'),
    path('deblina/', manage_views.deblina_view, name='deblina'),


    path('home/', manage_views.home, name='home'),
    path('contact/', manage_views.contact, name='contact'),
    path('stylesheet/', manage_views.stylesheet, name='stylesheet'),
]