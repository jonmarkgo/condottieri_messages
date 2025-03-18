from django.urls import path, re_path
from django.views.generic import RedirectView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import ListView
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.http import Http404
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from .models import Letter
from .forms import letter_form_factory
from .views import compose, reply, view, delete, undelete, BoxListView

app_name = 'condottieri_messages'

## urls that call the views in messages
urlpatterns = [
    path('', RedirectView.as_view(url='inbox/'), name='messages_redirect'),
]

## urls that call the custom views in condottieri_messages
urlpatterns += [
    path('inbox/', BoxListView.as_view(), name='inbox'),
    path('outbox/', BoxListView.as_view(), name='outbox'),
    path('trash/', BoxListView.as_view(), name='trash'),
    re_path(r'^compose/$', compose, name='compose'),
    re_path(r'^reply/(?P<message_id>[\d]+)/$', reply, name='reply'),
    re_path(r'^view/(?P<message_id>[\d]+)/$', view, name='view'),
    re_path(r'^delete/(?P<message_id>[\d]+)/$', delete, name='delete'),
    re_path(r'^undelete/(?P<message_id>[\d]+)/$', undelete, name='undelete'),
]
