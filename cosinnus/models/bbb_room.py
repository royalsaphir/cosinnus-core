from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from django.contrib.postgres.fields import JSONField


class BBBRoom(models.Model):
    """ This model represents a video/audio conference call with participants and/or presenters

    :var presenter: User that has the presenter role if any
    :type: auth.User

    :var members: Users, that can join the meeting
    :type: list of auth.User

    :var member_token: User -> BBB-Token mapping
    :type: dict

    :var moderators: Users with moderator/admin permissions for this meeting
    :type: list of auth.User

    :var name: (optional) name of the room
    :type: str
    """

    presenter = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="presenter",
                                  help_text=_("this user will enter the BBB presenter mode for this conversation"))
    members = models.ManyToManyField(User, related_name="members")
    member_token = JSONField(default={}, verbose_name="member token mapping")
    moderators = models.ManyToManyField(User)
    token = models.CharField(max_length=200, null=True, blank=True)
    name = models.CharField(max_length=160, null=True, blank=True, verbose_name=_("room name or title"))

    def __str__(self):
        return str(self.token)
