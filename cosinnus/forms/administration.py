# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.validators import MaxLengthValidator
from django.db.models.fields import BLANK_CHOICE_DASH
from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _

from cosinnus.models.managed_tags import CosinnusManagedTag
from cosinnus.models.newsletter import Newsletter
from cosinnus.utils.user import create_base_user

class UserWelcomeEmailForm(forms.Form):
    is_active = forms.BooleanField(required=False)
    email_text = forms.CharField(required=False, strip=False, widget=forms.Textarea)


class NewsletterForManagedTagsForm(forms.ModelForm):
    managed_tags = forms.ModelMultipleChoiceField(
            queryset=CosinnusManagedTag.objects.all(),
            widget=forms.CheckboxSelectMultiple,
            required=True)

    class Meta(object):
        model = Newsletter
        fields = ['subject', 'body', 'managed_tags']


class UserAdminForm(forms.ModelForm):
    email = forms.EmailField(label=_('email address'), required=True, validators=[MaxLengthValidator(220)])
    first_name = forms.CharField(label=_('first name'), required=True)

    class Meta(object):
        model = get_user_model()
        fields = ['first_name', 'last_name', 'email']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not self.instance.pk:
            email_exists = get_user_model().objects.filter(
                email=email).exists()
        else:
            email_exists = get_user_model().objects.filter(
                email=email).exclude(pk=self.instance.pk).exists()
        if email_exists:
            raise forms.ValidationError(_('This email address already has a registered user!'))
        else:
            return email.lower()

    def save(self, commit=True):
        if not self.instance.pk:
            self.instance.username = self.cleaned_data.get('email')[:150]
            user = super().save()
            user.username = str(user.id)
            user.is_active = False
            user.save()
        else:
            user = super().save()
        return user

