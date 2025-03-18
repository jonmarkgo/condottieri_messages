from django.urls import path, re_path
from django.views.generic.base import RedirectView

from . import views

## urls that call the views in messages
urlpatterns = [
    path('', RedirectView.as_view(url='inbox/')),
]

## urls that call the custom views in condottieri_messages
urlpatterns += [
    re_path(r'^compose/(?P<sender_id>[\d]+)/(?P<recipient_id>[\d]+)/$', views.compose, name='condottieri_messages_compose'),
    re_path(r'^reply/(?P<letter_id>[\d]+)/$', views.compose, name='condottieri_messages_reply'),
    re_path(r'^view/(?P<message_id>[\d]+)/$', views.view, name='condottieri_messages_detail'),
    path('inbox/', views.BoxListView.as_view(box='inbox'), name='messages_inbox'),
    path('outbox/', views.BoxListView.as_view(box='outbox'), name='messages_outbox'),
    path('trash/', views.BoxListView.as_view(box='trash'), name='messages_trash'),
    re_path(r'^inbox/(?P<slug>[-\w]+)/$', views.BoxListView.as_view(box='inbox'), name='condottieri_messages_inbox'),
    re_path(r'^outbox/(?P<slug>[-\w]+)/$', views.BoxListView.as_view(box='outbox'), name='condottieri_messages_outbox'),
    re_path(r'^delete/(?P<message_id>[\d]+)/$', views.delete, name='messages_delete'),
    re_path(r'^undelete/(?P<message_id>[\d]+)/$', views.undelete, name='messages_undelete'),
]
