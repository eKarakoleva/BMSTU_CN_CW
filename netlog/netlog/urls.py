"""netlog URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
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
from django.urls import path, include
from django.views.generic.base import TemplateView
from netlogs.views import *


urlpatterns = [
    path('admin/', admin.site.urls),
    path('netlog/', include('django.contrib.auth.urls')),
    path('', TemplateView.as_view(template_name='index.html'), name='index'),
    path('netlogs/signup/user/', UserSignUpView.as_view(), name='user_signup'),

    path('hosts/', include(([
        path('user/<int:pk>/', view_hosts, name='hosts_list'),
        path('user/edit/', edit_profile, name='edit_profile'),
        path('add/', HostCreateView.as_view(template_name='add/add_host.html'), name='add_host'),
        path('monitor/ping/<int:pk>/start/', start_ping, name = "start_ping"),
        path('monitor/ping/stop/', stopPing.as_view(), name='stop_ping'),
        path('monitor/host/<int:pk>/settings/', view_host_settings, name='view_host_settings'),
        path('user/update_status', status_update, name='status_update'),
        path('user/check_finished', check_if_expired, name='check_if_expired'),
        path('monitor/host/settings/test_ping', test_ping, name='test_ping'),
        path('monitor/host/settings/test_ports', scan_given_ports, name='scan_given_ports'), 
        path('monitor/port/<int:pk>/start/', start_port, name = "start_port"),
        path('monitor/port/stop/', stopPort.as_view(), name='stop_port'),
        path('user/status_update_port', status_update_port, name='status_update_port'),
        path('user/monitor/get_monitored_ports', get_monitored_ports, name='get_monitored_ports'), 
        path('user/monitor/get_down_ports', get_down_ports, name='get_down_ports'),
        path('monitor/<int:pk>/ping/stat/', stat_list_ping, name = "stat_list_ping"),
        path('monitor/<int:pk>/port/stat/', stat_list_port, name = "stat_list_port"),
        path('monitor/ping/stat/sort', sort_ping_stats, name = "sort_ping_stats"),
        path('monitor/port/stat/', sort_port_stats, name = "sort_port_stats"),
        path('monitor/host/delete', delete_host, name = "delete_host"), 
        path('monitor/host/geoinfo', get_host_geoinfo, name = "get_host_geoinfo"), 
    ], 'netlogs'), namespace='views')),
]

