# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.models.group import CosinnusGroup, CosinnusPortalMembership, \
    MEMBERSHIP_MEMBER, CosinnusGroupMembership, CosinnusPortal
from cosinnus.utils.user import assign_user_to_default_auth_group, \
    ensure_user_to_default_portal_groups
from django.contrib.auth import get_user_model
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch.dispatcher import receiver

from cosinnus.models.tagged import ensure_container, LikeObject
from cosinnus.core.registries.group_models import group_model_registry
from cosinnus.core import signals

import logging
from django.contrib.auth.signals import user_logged_in, user_logged_out
from cosinnus.models.profile import GlobalBlacklistedEmail,\
    GlobalUserNotificationSetting
from cosinnus.models.feedback import CosinnusFailedLoginRateLimitLog
from django.db import transaction

from cosinnus.core.middleware.login_ratelimit_middleware import login_ratelimit_triggered
from django.utils.encoding import force_text

from cosinnus.conf import settings
from cosinnus.utils.group import get_cosinnus_group_model
from django.contrib.contenttypes.models import ContentType
from annoying.functions import get_object_or_None

logger = logging.getLogger('cosinnus')

User = get_user_model()


@receiver(post_delete)
def clear_cache_on_group_delete(sender, instance, **kwargs):
    """ Clears the cache on CosinnusGroups after deleting one of them. """
    if sender == CosinnusGroup or issubclass(sender, CosinnusGroup):
        instance._clear_cache(slug=instance.slug)    


def ensure_user_in_group_portal(sender, created, **kwargs):
    """ Whenever a group membership is created, make sure the user is in the Portal for this group """
    if created:
        try:
            membership = kwargs.get('instance')
            CosinnusPortalMembership.objects.get_or_create(user=membership.user, group=membership.group.portal, defaults={'status': MEMBERSHIP_MEMBER})
        except:
            # We fail silently, because we never want to 500 here unexpectedly
            logger.error("Error while trying to add User Portal Membership for user that has just joined a group.")


# makes sure that users gain membership in a Portal when they are added into a group in that portal
post_save.connect(ensure_user_in_group_portal, sender=CosinnusGroupMembership)

post_save.connect(assign_user_to_default_auth_group, sender=User)
post_save.connect(ensure_user_to_default_portal_groups, sender=CosinnusPortalMembership)

@receiver(user_logged_in)
def ensure_user_in_logged_in_portal(sender, user, request, **kwargs):
    """ Make sure on user login, that the user becomes a member of this portal """
    try:
        CosinnusPortalMembership.objects.get_or_create(user=user, group=CosinnusPortal.get_current(), defaults={'status': MEMBERSHIP_MEMBER})
    except:
        # We fail silently, because we never want to 500 here unexpectedly
        logger.error("Error while trying to add User Portal Membership for user that has just logged in.")


@receiver(user_logged_in)
def ensure_user_blacklist_converts_to_setting(sender, user, request, **kwargs):
    """ Make sure on user login, that the user becomes a member of this portal """
    try:
        email = user.email
        if GlobalBlacklistedEmail.is_email_blacklisted(email):
            with transaction.atomic():
                GlobalBlacklistedEmail.remove_for_email(email)
                settings_obj = GlobalUserNotificationSetting.objects.get_object_for_user(user)
                settings_obj.setting = GlobalUserNotificationSetting.SETTING_NEVER
                settings_obj.save()
    except:
        # We fail silently, because we never want to 500 here unexpectedly
        logger.error("Error while trying to add User Portal Membership for user that has just logged in.")
        if settings.DEBUG:
            raise

post_save.connect(ensure_container, sender=CosinnusGroup)
for url_key in group_model_registry:
    group_model = group_model_registry.get(url_key)
    post_save.connect(ensure_container, sender=group_model)
    
    
def on_login_ratelimit_triggered(sender, username, ip, **kwargs):
    """ Log rate limit attempts """
    try:
        CosinnusFailedLoginRateLimitLog.objects.create(username=username, ip=None, portal=CosinnusPortal.get_current())
    except Exception as e:
        logger.error('Error while trying to log failed login ratelimit trigger!', extra={'exception': force_text(e)})

login_ratelimit_triggered.connect(on_login_ratelimit_triggered)


@receiver(user_logged_in)
def set_cookie_expiry_for_authenticated_user(sender, user, request, **kwargs):
    """ Default for cookies for anonymous users is browser-session and as set in 
        `COSINNUS_SESSION_EXPIRY_AUTHENTICATED_IN_USERS` logged in users """
    request.session.set_expiry(settings.COSINNUS_SESSION_EXPIRY_AUTHENTICATED_IN_USERS)

@receiver(user_logged_out)
def reset_cookie_expiry_for_anonymous_user(sender, user, request, **kwargs):
    """ Default for cookies for anonymous users is browser-session and as set in 
        `COSINNUS_SESSION_EXPIRY_AUTHENTICATED_IN_USERS` logged in users """
    request.session.set_expiry(0)
    
    
if getattr(settings, 'COSINNUS_USER_FOLLOWS_GROUP_WHEN_JOINING', True):
    
    @receiver(signals.user_joined_group)
    def user_follow_joined_group_trigger(sender, user, group, **kwargs):
        """ Will automatically make a user follow a group after they joined it """
        group_ct = ContentType.objects.get_for_model(get_cosinnus_group_model())
        # create a new followed likeobject
        likeobj, created = LikeObject.objects.get_or_create(
            content_type=group_ct, 
            object_id=group.id, 
            user=user,
            defaults={'liked': False, 'followed': True}
        )
        # or make the existing likeobject followed
        if not created:
            if not likeobj.followed:
                likeobj.followed = True
                likeobj.save(update_fields=['followed'])
        group.clear_likes_cache()
    
    @receiver(signals.user_left_group)
    def user_unfollow_left_group_trigger(sender, user, group, **kwargs):
        """ Will automatically make a user unfollow a group after they left it """
        group_ct = ContentType.objects.get_for_model(get_cosinnus_group_model())
        # get an existing following object
        likeobj = get_object_or_None(LikeObject, 
            content_type=group_ct,
            object_id=group.id, 
            user=user,
            followed=True
        )
        # make the followed likeobject unfollowed if it exists
        if likeobj:
            likeobj.followed = False
            likeobj.save(update_fields=['followed'])
            group.clear_likes_cache()
        

""" User account activation/deactivation logic """
def user_pre_save(sender, **kwargs):
    """ Saves a user's is_active value as it was before saving """
    user = kwargs['instance']
    actual_value = user.is_active
    user.refresh_from_db(fields=['is_active'])
    user._is_active = user.is_active
    user.is_active = actual_value
    
def user_post_save(sender, **kwargs):
    """ Compares the saved is_active value and sends signals if it was changed """
    user = kwargs['instance']
    if hasattr(user, '_is_active'):
        if user.is_active != user._is_active:
            if user.is_active:
                signals.user_activated.send(sender=sender, user=user)
            else:
                signals.user_deactivated.send(sender=sender, user=user)

pre_save.connect(user_pre_save, sender=get_user_model())
post_save.connect(user_post_save, sender=get_user_model())


from cosinnus.apis.cleverreach import *
from cosinnus.models.wagtail_models import * # noqa
