# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import functools

from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseForbidden, HttpResponseNotFound
from django.utils.decorators import available_attrs
from django.utils.translation import ugettext_lazy as _

from cosinnus.utils.permissions import check_object_write_access,\
    check_group_create_objects_access, check_object_read_access, get_user_token
from django.contrib import messages
from django.http.response import HttpResponseRedirect
from django.core.urlresolvers import reverse_lazy
from django.core.exceptions import PermissionDenied
from cosinnus.core.registries.group_models import group_model_registry
from django.contrib.auth.models import User
from cosinnus.models.tagged import BaseTagObject


def redirect_to_403(request):
    raise PermissionDenied


def get_group_for_request(group_name, request):
    """ Retrieve the proxy group object depending on the URL path regarding 
        the registered group models.
        A CosinnusGroup will not be returned if it is requested by an URL
        path with a different group_model_key than the one it got registered with. """
    group_url_key = request.path.split('/')[1]
    group_class = group_model_registry.get(group_url_key, None)
    
    if group_class:
        try:
            group = group_class.objects.get(slug=group_name)
            if type(group) is group_class:
                return group
        except group_class.DoesNotExist:
            pass
    return None

    

def staff_required(function):
    """A function decorator to assure a requesting user is a staff user."""
    actual_decorator = user_passes_test(
        lambda u: u.is_staff
    )
    return actual_decorator(function)


def superuser_required(function):
    """A function decorator to assure a requesting user has the superuser flag
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_superuser
    )
    return actual_decorator(function)

def membership_required(function):
    """A function decorator to assure a requesting user is an authenticated member
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated()
    )
    return actual_decorator(function)


def require_admin_access_decorator(group_url_arg='group'):
    def decorator(function):
        @functools.wraps(function, assigned=available_attrs(function))
        def wrapper(request, *args, **kwargs):
            group_name = kwargs.get(group_url_arg, None)
            if not group_name:
                return HttpResponseNotFound(_("No group provided"))

            group = get_group_for_request(group_name, request)
            if not group:
                return HttpResponseNotFound(_("No group found with this name"))
            user = request.user

            if not user.is_authenticated():
                # support for the ajaxable view mixin
                if getattr(self, 'is_ajax_request_url', False):
                    return HttpResponseForbidden('Not authenticated')
                messages.error(request, _('Please log in to access this page.'))
                return HttpResponseRedirect(reverse_lazy('login') + '?next=' + request.path)

            if check_object_write_access(group, user):
                kwargs['group'] = group
                return function(request, *args, **kwargs)

            # Access denied, redirect to 403 page and and display an error message
            return redirect_to_403(request)
            
        return wrapper
    return decorator


def require_logged_in():
    """A method decorator that checks that the requesting user is logged in
    """

    def decorator(function):
        @functools.wraps(function, assigned=available_attrs(function))
        def wrapper(self, request, *args, **kwargs):
            user = request.user
            
            if not user.is_authenticated():
                # support for the ajaxable view mixin
                if getattr(self, 'is_ajax_request_url', False):
                    return HttpResponseForbidden('Not authenticated')
                messages.error(request, _('Please log in to access this page.'))
                return HttpResponseRedirect(reverse_lazy('login') + '?next=' + request.path)
            
            return function(self, request, *args, **kwargs)
            
        return wrapper
    return decorator


def require_admin_access(group_url_kwarg='group', group_attr='group'):
    """A method decorator that takes the group name from the kwargs of a
    dispatch function in CBVs and checks that the requesting user is allowed to
    perform administrative operations.

    Additionally this function populates the group instance to the view
    instance as attribute `group_attr`

    :param str group_url_kwarg: The name of the key containing the group name.
        Defaults to `'group'`.
    :param str group_attr: The attribute name which can later be used to access
        the group from within an view instance (e.g. `self.group`). Defaults to
        `'group'`.
    """

    def decorator(function):
        @functools.wraps(function, assigned=available_attrs(function))
        def wrapper(self, request, *args, **kwargs):
            group_name = kwargs.get(group_url_kwarg, None)
            if not group_name:
                return HttpResponseNotFound(_("No group provided"))

            group = get_group_for_request(group_name, request)
            if not group:
                return HttpResponseNotFound(_("No group found with this name"))
            user = request.user
            
            if not user.is_authenticated():
                # support for the ajaxable view mixin
                if getattr(self, 'is_ajax_request_url', False):
                    return HttpResponseForbidden('Not authenticated')
                messages.error(request, _('Please log in to access this page.'))
                return HttpResponseRedirect(reverse_lazy('login') + '?next=' + request.path)

            if check_object_write_access(group, user):
                setattr(self, group_attr, group)
                return function(self, request, *args, **kwargs)

            # Access denied, redirect to 403 page and and display an error message
            return redirect_to_403(request)
            
        return wrapper
    return decorator


def require_read_access(group_url_kwarg='group', group_attr='group'):
    """A method decorator that takes the group name from the kwargs of a
    dispatch function in CBVs and checks that the requesting user is allowed to
    perform read operations.

    Additionally this function populates the group instance to the view
    instance as attribute `group_attr`

    :param str group_url_kwarg: The name of the key containing the group name.
        Defaults to `'group'`.
    :param str group_attr: The attribute name which can later be used to access
        the group from within an view instance (e.g. `self.group`). Defaults to
        `'group'`.
    """

    def decorator(function):
        @functools.wraps(function, assigned=available_attrs(function))
        def wrapper(self, request, *args, **kwargs):
            group_name = kwargs.get(group_url_kwarg, None)
            if not group_name:
                return HttpResponseNotFound(_("No group provided"))

            group = get_group_for_request(group_name, request)
            if not group:
                return HttpResponseNotFound(_("No group found with this name"))
            user = request.user
            
            setattr(self, group_attr, group)
            
            requested_object = None
            try:
                requested_object = self.get_object()
            except (AttributeError, TypeError):
                pass
            
            obj_public = requested_object and requested_object.media_tag and requested_object.media_tag.visibility == BaseTagObject.VISIBILITY_ALL
            if not (obj_public or group.public or user.is_authenticated()):
                # support for the ajaxable view mixin
                if getattr(self, 'is_ajax_request_url', False):
                    return HttpResponseForbidden('Not authenticated')
                messages.error(request, _('Please log in to access this page.'))
                return HttpResponseRedirect(reverse_lazy('login') + '?next=' + request.path)
            
            if requested_object:
                if check_object_read_access(requested_object, user):
                    return function(self, request, *args, **kwargs)
            else:
                if check_object_read_access(group, user):
                    return function(self, request, *args, **kwargs)

            # Access denied, redirect to 403 page and and display an error message
            return redirect_to_403(request)
            
        return wrapper
    return decorator


def require_write_access(group_url_kwarg='group', group_attr='group'):
    """A method decorator that takes the group name from the kwargs of a
    dispatch function in CBVs and checks that the requesting user is allowed to
    perform write operations.

    Additionally this function populates the group instance to the view
    instance as attribute `group_attr`

    :param str group_url_kwarg: The name of the key containing the group name.
        Defaults to `'group'`.
    :param str group_attr: The attribute name which can later be used to access
        the group from within an view instance (e.g. `self.group`). Defaults to
        `'group'`.
    """

    def decorator(function):
        @functools.wraps(function, assigned=available_attrs(function))
        def wrapper(self, request, *args, **kwargs):
            group_name = kwargs.get(group_url_kwarg, None)
            if not group_name:
                return HttpResponseNotFound(_("No group provided"))
            
            group = get_group_for_request(group_name, request)
            if not group:
                return HttpResponseNotFound(_("No group found with this name"))
            user = request.user
            
            # set the group attr    
            setattr(self, group_attr, group)
            
            requested_object = None
            try:
                requested_object = self.get_object()
            except (AttributeError, TypeError):
                pass
            
            obj_public = requested_object and requested_object.media_tag and requested_object.media_tag.visibility == BaseTagObject.VISIBILITY_ALL
            if not (obj_public or user.is_authenticated()):
                # support for the ajaxable view mixin
                if getattr(self, 'is_ajax_request_url', False):
                    return HttpResponseForbidden('Not authenticated')
                messages.error(request, _('Please log in to access this page.'))
                return HttpResponseRedirect(reverse_lazy('login') + '?next=' + request.path)
            
            if requested_object:
                # editing/deleting an object, check if we are owner or staff member or group admin or site admin
                if (obj_public and request.method == 'GET') or (check_object_write_access(requested_object, user)):
                    return function(self, request, *args, **kwargs)
            else:
                # creating a new object, check if we can create objects in the group
                if check_group_create_objects_access(group, user):
                    return function(self, request, *args, **kwargs)
            
            # Access denied, redirect to 403 page and and display an error message
            return redirect_to_403(request)
            
        return wrapper
    return decorator



def require_user_token_access(token_name, group_url_kwarg='group', group_attr='group'):
    """ A method decorator that allows access only if the URL params
    `user=999&token=1234567` are supplied, and if the token supplied matches
    the specific token (determined by :param ``token_name``) in the supplied 
    user's settings. Please only use different token_names for each specific purpose.
        
    Additionally this function populates the group instance to the view
    instance as attribute `group_attr` and the resolved token user as attribute `user`

    :param str group_url_kwarg: The name of the key containing the group name.
        Defaults to `'group'`.
    :param str group_attr: The attribute name which can later be used to access
        the group from within an view instance (e.g. `self.group`). Defaults to
        `'group'`.
    """

    def decorator(function):
        @functools.wraps(function, assigned=available_attrs(function))
        def wrapper(self, request, *args, **kwargs):
            
            # assume no user is logged in, and check the user id and token from the args
            user_id = request.GET.get('user', None)
            token = request.GET.get('token', None)
            if not user_id or not token:
                return HttpResponseForbidden('No authentication supplied!')
            
            user = None
            user_token = None
            try:
                user = User.objects.get(id=user_id)
                user_token = get_user_token(user, token_name)
            except User.DoesNotExist:
                pass
            if not user or not user_token or not user_token == token:
                return HttpResponseForbidden('Authentication invalid!')
            
            self.user = user
            
            group_name = kwargs.get(group_url_kwarg, None)
            if not group_name:
                return HttpResponseNotFound(_("No group provided"))

            group = get_group_for_request(group_name, request)
            if not group:
                return HttpResponseNotFound(_("No group found with this name"))
            
            
            setattr(self, group_attr, group)
            
            requested_object = None
            try:
                requested_object = self.get_object()
            except (AttributeError, TypeError):
                pass
            
            if requested_object:
                if check_object_read_access(requested_object, user):
                    return function(self, request, *args, **kwargs)
            else:
                if check_object_read_access(group, user):
                    return function(self, request, *args, **kwargs)

            # Access denied, redirect to 403 page and and display an error message
            return redirect_to_403(request)
            
        return wrapper
    return decorator


def require_create_objects_in_access(group_url_kwarg='group', group_attr='group'):
    """A method decorator that takes the group name from the kwargs of a
    dispatch function in CBVs and checks that the requesting user is allowed to
    perform read operations.

    Additionally this function populates the group instance to the view
    instance as attribute `group_attr`

    :param str group_url_kwarg: The name of the key containing the group name.
        Defaults to `'group'`.
    :param str group_attr: The attribute name which can later be used to access
        the group from within an view instance (e.g. `self.group`). Defaults to
        `'group'`.
    """

    def decorator(function):
        @functools.wraps(function, assigned=available_attrs(function))
        def wrapper(self, request, *args, **kwargs):
            group_name = kwargs.get(group_url_kwarg, None)
            if not group_name:
                return HttpResponseNotFound(_("No group provided"))

            group = get_group_for_request(group_name, request)
            if not group:
                return HttpResponseNotFound(_("No group found with this name"))
            user = request.user
            
            if not group.public and not user.is_authenticated():
                # support for the ajaxable view mixin
                if getattr(self, 'is_ajax_request_url', False):
                    return HttpResponseForbidden('Not authenticated')
                messages.error(request, _('Please log in to access this page.'))
                return HttpResponseRedirect(reverse_lazy('login') + '?next=' + request.path)
            
            setattr(self, group_attr, group)
            
            if check_group_create_objects_access(group, user):
                return function(self, request, *args, **kwargs)

            # Access denied, redirect to 403 page and and display an error message
            return redirect_to_403(request)
            
        return wrapper
    return decorator

