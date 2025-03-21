## Copyright (c) 2010 by Jose Antonio Martin <jantonio.martin AT gmail DOT com>
## This program is free software: you can redistribute it and/or modify it
## under the terms of the GNU Affero General Public License as published by the
## Free Software Foundation, either version 3 of the License, or (at your option
## any later version.
##
## This program is distributed in the hope that it will be useful, but WITHOUT
## ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
## FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License
## for more details.
##
## You should have received a copy of the GNU Affero General Public License
## along with this program. If not, see <http://www.gnu.org/licenses/agpl.txt>.
##
## This license is also included in the file COPYING
##
## AUTHOR: Jose Antonio Martin <jantonio.martin AT gmail DOT com>

import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404, HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from django.utils.decorators import method_decorator
from django.urls import reverse
from django.conf import global_settings
from django.views.generic.list import ListView
from django.contrib import messages

from machiavelli.models import Player, Game
from machiavelli.views import get_game_context

from condottieri_messages.exceptions import LetterError
from condottieri_messages.forms import letter_form_factory
from condottieri_messages.models import Letter

class LoginRequiredMixin(object):
	""" Mixin to check that the user has authenticated.
	(Always the first mixin in class)
	"""
	@method_decorator(login_required)
	def dispatch(self, *args, **kwargs):
		return super(LoginRequiredMixin, self).dispatch(*args, **kwargs)

def check_errors(request, game, sender_player, recipient_player):
	msg = None
	if sender_player.eliminated or recipient_player.eliminated:
		msg = _("Eliminated players cannot send or receive letters")
	## if the game is inactive, return 404 error
	elif game.phase == 0:
		msg = _("You cannot send letters in an inactive game.")
	## check if the sender has excommunicated the recipient
	elif sender_player.may_excommunicate and recipient_player.is_excommunicated:
		msg = _("You cannot write to a country that you have excommunicated.")
	else:
		return True
	raise LetterError(msg)

@login_required
def compose(request, sender_id=None, recipient_id=None, letter_id=None):
	if sender_id and recipient_id:
		## check that the sender is legitimate
		sender_player = get_object_or_404(Player, user=request.user, id=sender_id)
		game = sender_player.game
		recipient_player = get_object_or_404(Player, id=recipient_id, game=game)
		parent = None
	elif letter_id:
		parent = get_object_or_404(Letter, id=letter_id)
		if parent.sender != request.user and parent.recipient != request.user:
			raise Http404
		sender_player = parent.recipient_player
		recipient_player = parent.sender_player
		game = sender_player.game
	else:
		raise Http404
	if not game.configuration.letters:
		raise Http404
	context = get_game_context(request, game, sender_player)
	try:
		check_errors(request, game, sender_player, recipient_player)
	except LetterError as e:
		messages.error(request, e.value)
		return redirect(game)
	## try to find a common language for the two players
	common_language_code = None
	sender_lang = sender_player.user.profile.spokenlanguage_set.values_list('code', flat=True)
	recipient_lang = recipient_player.user.profile.spokenlanguage_set.values_list('code', flat=True)
	for lang in sender_lang:
		if lang in recipient_lang:
			common_language_code = lang
			break
	if common_language_code is not None:
		lang_dict = dict(global_settings.LANGUAGES)
		if common_language_code in list(lang_dict.keys()):
			common_language = lang_dict[common_language_code]
		context.update({'common_language': common_language })
	LetterForm = letter_form_factory(sender_player, recipient_player)
	if request.method == 'POST':
		letter_form = LetterForm(sender_player, recipient_player, data=request.POST)
		if letter_form.is_valid():
			letter = letter_form.save()
			messages.success(request, _("Letter successfully sent."))
			return redirect(game)
	else:
		initial = {}
		if parent:
			initial = {
				'subject': _("Re: %(subject)s") % {'subject': parent.subject},
				'body': _("\nOn %(sent_at)s, %(sender)s wrote:\n%(body)s") % {
					'sent_at': parent.sent_at.strftime("%Y-%m-%d %H:%M"),
					'sender': parent.sender,
					'body': parent.body
				}
			}
		letter_form = LetterForm(sender_player, recipient_player, initial=initial)
	
	context.update({
		'form': letter_form,
		'sender_player': sender_player,
		'recipient_player': recipient_player,
	})
	return render(request, 'condottieri_messages/compose.html', context)

@login_required
def view(request, message_id):
	"""
	Modified version of condottieri-messages view.
	Shows a single message.``message_id`` argument is required.
	The user is only allowed to see the message, if he is either 
	the sender or the recipient. If the user is not allowed a 404
	is raised. 
	If the user is the recipient and the message is unread 
	``read_at`` is set to the current datetime.
	"""
	user = request.user
	now = datetime.datetime.now()
	message = get_object_or_404(Letter, id=message_id)
	if (message.sender != user) and (message.recipient != user):
		raise Http404
	game = message.sender_player.game
	player = Player.objects.get(user=request.user, game=game)
	context = get_game_context(request, game, player)
	if message.read_at is None and message.recipient == user:
		message.read_at = now
		message.save()
	context.update({'message' : message,})
	return render(request, 'condottieri_messages/view.html', 
							context)

class BoxListView(LoginRequiredMixin, ListView):
	allow_empty = True
	model = Letter
	paginate_by = 25
	context_object_name = 'message_list'
	template_name = 'condottieri_messages/messages_box.html'

	allowed_boxes = ['inbox', 'outbox', 'trash']

	def get_box_type(self):
		"""Get the box type from the URL name."""
		url_name = self.request.resolver_match.url_name
		return url_name if url_name in self.allowed_boxes else None

	def get_queryset(self):
		box_type = self.get_box_type()
		if not box_type:
			return Letter.objects.none()
			
		if box_type == 'inbox':
			message_list = Letter.objects.inbox_for(self.request.user)
		elif box_type == 'outbox':
			message_list = Letter.objects.outbox_for(self.request.user)
		elif box_type == 'trash':
			message_list = Letter.objects.trash_for(self.request.user)
		else:
			return Letter.objects.none()

		try:
			slug = self.kwargs['slug']
		except KeyError:
			pass
		else:
			self.game = get_object_or_404(Game, slug=slug)
			message_list = message_list.filter(sender_player__game=self.game)
		return message_list.order_by('-sent_at')

	def get_context_data(self, **kwargs):
		context = super(BoxListView, self).get_context_data(**kwargs)
		if hasattr(self, 'game'):
			context['game'] = self.game
		context['box'] = self.get_box_type()
		return context

##
## 'delete' and 'undelete' code is taken from django-messages and modified
## to disable notifications when a message is deleted or recovered
##

@login_required
def delete(request, message_id, success_url=None):
    """
    Marks a message as deleted by sender or recipient. The message is not
    really removed from the database, because two users must delete a message
    before it's save to remove it completely. 
    A cron-job should prune the database and remove old messages which are 
    deleted by both users.
    As a side effect, this makes it easy to implement a trash with undelete.
    
    You can pass ?next=/foo/bar/ via the url to redirect the user to a different
    page (e.g. `/foo/bar/`) than ``success_url`` after deletion of the message.
    """
    user = request.user
    now = datetime.datetime.now()
    message = get_object_or_404(Letter, id=message_id)
    deleted = False
    if success_url is None:
        success_url = reverse('condottieri_messages:inbox')
    if 'next' in request.GET:
        success_url = request.GET['next']
    if message.sender == user:
        message.sender_deleted_at = now
        deleted = True
    if message.recipient == user:
        message.recipient_deleted_at = now
        deleted = True
    if deleted:
        message.save()
        messages.success(request, _("Message successfully deleted."))
        return HttpResponseRedirect(success_url)
    raise Http404

@login_required
def undelete(request, message_id, success_url=None):
    """
    Recovers a message from trash. This is achieved by removing the
    ``sender_deleted_at`` or ``recipient_deleted_at`` timestamps, depending
    on the user.
    """
    user = request.user
    message = get_object_or_404(Letter, id=message_id)
    undeleted = False
    if success_url is None:
        success_url = reverse('condottieri_messages:inbox')
    if 'next' in request.GET:
        success_url = request.GET['next']
    if message.sender == user and message.sender_deleted_at:
        message.sender_deleted_at = None
        undeleted = True
    if message.recipient == user and message.recipient_deleted_at:
        message.recipient_deleted_at = None
        undeleted = True
    if undeleted:
        message.save()
        messages.success(request, _("Message successfully recovered."))
        return HttpResponseRedirect(success_url)
    raise Http404

@login_required
def reply(request, message_id):
	parent = get_object_or_404(Letter, id=message_id)
	if parent.sender != request.user and parent.recipient != request.user:
		raise Http404
	return compose(request, letter_id=message_id)

