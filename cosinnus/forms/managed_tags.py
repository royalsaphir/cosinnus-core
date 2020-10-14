# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from annoying.functions import get_object_or_None
from django import forms
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext_lazy as _

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.managed_tags import CosinnusManagedTag, \
    CosinnusManagedTagAssignment


if getattr(settings, 'COSINNUS_MANAGED_TAGS_ENABLED', False) and getattr(settings, 'COSINNUS_MANAGED_TAGS_USERS_MAY_ASSIGN_SELF'):
    class _ManagedTagFormMixin(object):
        
        # the attribute name of the object/instance that should be assigned with the tag
        # None means the instance/object itself should be assigned
        managed_tag_assignment_attribute_name = None
        
        def __init__(self, *args, **kwargs):
            super(_ManagedTagFormMixin, self).__init__(*args, **kwargs)
            if 'managed_tag_field' in self.fields:
                setattr(self.fields['managed_tag_field'], 'all_managed_tags', CosinnusManagedTag.objects.all_in_portal())
            # set initial tag
            if 'managed_tag_field' in self.initial:
                self.fields['managed_tag_field'].initial = self.initial['managed_tag_field']
            elif self.instance and self.instance.pk:
                tag_assignment_instance = self.instance
                if self.managed_tag_assignment_attribute_name:
                    # if for this form, another attribute than the instance itself is being assigned, resolve it
                    if not getattr(tag_assignment_instance, self.managed_tag_assignment_attribute_name, None):
                        raise ImproperlyConfigured(f'Managed tag instance assignment could not be found: \
                                "{self.managed_tag_assignment_attribute_name}" for model {type(tag_assignment_instance)}')
                    tag_assignment_instance = getattr(tag_assignment_instance, self.managed_tag_assignment_attribute_name)
                qs = tag_assignment_instance.managed_tag_assignments.all()
                managed_tag_slugs = qs.filter(approved=True).values_list('managed_tag__slug', flat=True)
                if managed_tag_slugs:
                    self.fields['managed_tag_field'].initial = ','.join(list(managed_tag_slugs))
        
        def clean_managed_tag_field(self):
            """ Todo: This method supports only single-tag cleaning for now! """
            self.save_managed_tags = []
            tag_value = self.cleaned_data['managed_tag_field']
            if tag_value:
                found_tag = get_object_or_None(CosinnusManagedTag, portal=CosinnusPortal.get_current(), slug=tag_value)
                if not found_tag:
                    raise forms.ValidationError(_('The selected choice was not found or invalid! Please choose a different value!'))
                self.save_managed_tags = [tag_value]
            return tag_value
        
        def save(self, commit=True):
            """ Set the username equal to the userid """
            obj = super(_ManagedTagFormMixin, self).save(commit=True)
            tag_assignment_instance = obj
            if self.managed_tag_assignment_attribute_name:
                # if for this form, another attribute than the object itself is being assigned, resolve it
                if not getattr(tag_assignment_instance, self.managed_tag_assignment_attribute_name, None):
                    raise ImproperlyConfigured(f'Managed tag instance assignment could not be found: \
                        "{self.managed_tag_assignment_attribute_name}" for model {type(obj)}')
                tag_assignment_instance = getattr(tag_assignment_instance, self.managed_tag_assignment_attribute_name)
                
            # create new managed tag assignments and delete old ones
            CosinnusManagedTagAssignment.update_assignments_for_object(tag_assignment_instance, self.save_managed_tags)
            return obj
        
else:
    class _ManagedTagFormMixin(object):
        pass
    
ManagedTagFormMixin = _ManagedTagFormMixin
