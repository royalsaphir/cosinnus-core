# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db import models
from django.dispatch import receiver
from django.utils.functional import cached_property
from django.utils.encoding import python_2_unicode_compatible

from cosinnus.conf import settings


__all__ = ['BaseUserProfile', 'UserProfile', 'get_user_profile_model']


class BaseUserProfileManager(models.Manager):
    use_for_related_fields = True

    def get_for_user(self, user):
        """
        Return the user profile for a given user.

        :param user: Either an int which defines the user's primary key or a
            model instance.
        :return: The user profile for the given model. The concrete subclass of
            ``BaseUserProfile`` as defined by ``COSINNUS_USER_PROFILE_MODEL``.
        :raise TypeError: If user is neither an int nor a model.
        """
        if isinstance(user, int):
            return self.get(user_id=user)
        if isinstance(user, models.Model):
            return self.get(user_id=user.id)
        raise TypeError('user must be of type int or Model but is %s' % type(user))


@python_2_unicode_compatible
class BaseUserProfile(models.Model):
    """
    This is a base user profile used within cosinnus. To use it, create your
    own model inheriting from this model.

    .. code-block:: python

        from django.db import models
        from cosinnus.models import BaseUserProfile

        class MyUserProfile(BaseUserProfile):
            myfield = models.CharField('myfield', max_length=10)

    Additionally set the settings variable ``COSINNUS_USER_PROFILE_MODEL`` to
    the dotted model path (myapp.MyUserProfile). This works the same way as
    Django's custom user model.

    To get a user's profile e.g in a view use the ``get_for_user()`` method
    on the manager:

    .. code-block:: python

        from myapp.models import MyUserProfile

        def myview(request):
            user = request.user
            profile = MyUserProfile.objects.get_for_user(user)
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, editable=False)

    objects = BaseUserProfileManager()

    SKIP_FIELDS = ('id', 'user',)

    class Meta:
        abstract = True

    def __str__(self):
        return six.text_type(self.user)

    def save(self, *args, **kwargs):
        try:
            existing = self._default_manager.get(user=self.user)
            # workaround for http://goo.gl/4I8Ok
            self.id = existing.id  # force update instead of insert
        except ObjectDoesNotExist:
            pass
        super(BaseUserProfile, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('cosinnus:profile-detail')

    @cached_property
    def optional_fields(self):
        """
        Iterates over all fields defiend in the user profile and returns a list
        of dicts with the keys ``name`` and ``value``.

        The list will only contain those fields not listed in ``SKIP_FIELDS``.
        """
        all_fields = self._meta.get_all_field_names()
        optional_fields = []
        for name in all_fields:
            if name in self.SKIP_FIELDS:
                continue
            value = getattr(self, name)
            if value:
                field = self._meta.get_field_by_name(name)[0]
                optional_fields.append({
                    'name': field.verbose_name,
                    'value': value,
                })
        return optional_fields


class UserProfile(BaseUserProfile):

    class Meta:
        app_label = 'cosinnus'
        swappable = 'COSINNUS_USER_PROFILE_MODEL'


def get_user_profile_model():
    "Return the cosinnus user profile model that is active in this project"
    from django.core.exceptions import ImproperlyConfigured
    from django.db.models import get_model
    from cosinnus.conf import settings

    try:
        app_label, model_name = settings.COSINNUS_USER_PROFILE_MODEL.split('.')
    except ValueError:
        raise ImproperlyConfigured("COSINNUS_USER_PROFILE_MODEL must be of the form 'app_label.model_name'")
    user_profile_model = get_model(app_label, model_name)
    if user_profile_model is None:
        raise ImproperlyConfigured("COSINNUS_USER_PROFILE_MODEL refers to model '%s' that has not been installed" %
            settings.COSINNUS_USER_PROFILE_MODEL)
    return user_profile_model


@receiver(models.signals.post_save, sender=get_user_model())
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        upm = get_user_profile_model()
        upm.objects.get_or_create(user=instance)

