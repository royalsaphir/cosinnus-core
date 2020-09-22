import argparse
import urllib
import requests

from hashlib import sha1, sha256

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext as _
from django_bigbluebutton.bbb import BigBlueButton
from cosinnus.utils import bigbluebutton as bbb_utils
from cosinnus.utils.functions import is_number
import logging

logger = logging.getLogger('cosinnus')


""" 
This is a wrapper for django-bigbluebutton.bbb

Some features are not present in bbb.py; for instance a meeting creation with a `max_attendees` value.
Therefore we create a create_verbose_meeting function, to address these properties of a BBBRoom 
we need in the WeChange project.

Functions that are not included in bbb.py are called `manually` via urllib.
For a full documentation on BigBlueButton API parameters have a look at: https://docs.bigbluebutton.org/dev/api.html

Checksum for API parameters is generated with SHA1 instead of SHA256 hash by default. Set the used hash algorithm in the 
global settings in `BBB_HASH_ALGORITHM`.
All wrapped functions from bbb.py are called with sha1, regardless of the `BBB_HASH_ALGORITHM` setting.
"""


def join_url_tokenized(meeting_id, name, password):
    url = join_url(meeting_id, name, password)
    return requests.get(url).url


def is_meeting_remote(meeting_id):
    remote_rooms = BigBlueButton().get_meetings()
    for room in remote_rooms:
        if room.get('name', '') == meeting_id:
            return True

    return False


def api_call(query, call):
    prepared = '{}{}{}'.format(call, query, settings.BBB_SECRET_KEY)

    if settings.BBB_HASH_ALGORITHM == "SHA1":
        checksum = sha1(str(prepared).encode('utf-8')).hexdigest()
    elif settings.BBB_HASH_ALGORITHM == "SHA256":
        checksum = sha256(str(prepared).encode('utf-8')).hexdigest()
    else:
        raise ImproperlyConfigured("BBB_HASH_ALGORITHM setting is not set to SHA1 or SHA256")

    result = "%s&checksum=%s" % (query, checksum)
    return result


def start(
        name, meeting_id, welcome="Welcome to the conversation",
        moderator_password="", attendee_password="", max_participants=None, voice_bridge=None,
        parent_meeting_id=None, options=None):
    """ This function calls the BigBlueButton API directly to create a meeting with all available parameters available
        in the cosinnus-core.BBBRoom model.

    :param name: Human readable name for the meeting
    :type: str

    :param meeting_id: Human readable ID for the meeting
    :type: str

    :param welcome: Welcome message when joining the meeting
    :type: str

    :param moderator_password: Password for users to join with moderator privileges
    :type: str

    :param attendee_password: Password for users to join with default attendee privileges
    :type: str

    :param max_participants: Number of users allowed in the conference
    :type: int

    :param voice_bridge: Dial in PIN for telephone users
    :type: int

    :param parent_meeting_id: Breaking room for a running conference
    :type: str

    :param options: BBBRoom options according to the listed options in the BigBlueButton API
    :type: dict

    :return: XML representation of the API result
    :rtype: XML
    """
    call = 'create'

    # set default values
    voice_bridge = voice_bridge if voice_bridge and is_number(voice_bridge) else bbb_utils.random_voice_bridge()
    attendee_password = attendee_password if attendee_password else bbb_utils.random_password()
    moderator_password = moderator_password if moderator_password else bbb_utils.random_password()

    query = (
        ("name", name),
        ('meetingID', meeting_id),
        ("welcome", welcome),
        ("voiceBridge", voice_bridge),
    )

    if max_participants and is_number(max_participants):
        query += (("maxParticipants", int(max_participants)),)

    if parent_meeting_id:
        query += (("parentMeetingID", parent_meeting_id),)

    if options:
        for key, value in options.items():
            query += ((key, value),)

    query = urllib.parse.urlencode(query)

    hashed = api_call(query, call)
    url = settings.BBB_API_URL + call + '?' + hashed
    response = requests.get(url)
    result = bbb_utils.parse_xml(response.content.decode('utf-8'))

    if result:
        return result
    else:
        logger.error('BBB Room eror: Server request was not successful.',
                     extra={'response_status_code': response.status_code, 'result': response.text})
        raise Exception('BBB Room exception: Server request was not successful: ' + str(response.text))


def end_meeting(meeting_id, password):
    """ This function is a wrapper for the `end_meeting` function in bbb.py """
    return BigBlueButton().end_meeting(meeting_id, password)


def get_meetings():
    """ This function is a wrapper for the `get_meetings` function in bbb.py

    :return: XML representation of the API result
    :rtype: XML
    """
    return BigBlueButton().get_meetings()


def meeting_info(meeting_id, password):
    """ This function is a wrapper for the `meeting_info` function in bbb.py

    :return: dict representation of the API result
    :rtype: dict
    """
    return BigBlueButton().meeting_info(meeting_id, password)


def verbose_meeting_info(meeting_id, password):
    call = 'getMeetingInfo'
    query = urllib.parse.urlencode((
        ('meetingID', meeting_id),
        ('password', password),
    ))
    hashed = api_call(query, call)
    url = settings.BBB_API_URL + call + '?' + hashed
    response = bbb_utils.parse_xml(requests.get(url).content)
    if response:
        return bbb_utils.xml_to_json(response)
    else:
        return None


def is_running(self, meeting_id):
    """ This function is a wrapper for the `is_running` function in bbb.py

    :return: XML representation of the API result
    :rtype: XML
    """
    return BigBlueButton().is_running(meeting_id)


def xml_join(name, meeting_id, password):
    """ Returns a XML representation of the join call. !! Use only in Testing !!

    :param name: Name of the user shown to other attendees in the conversation
    :type: str

    :param meeting_id: Identifier of the meeting
    :type: str

    :param password: Password for the user to join
    :type: str
    """

    call = 'join'
    query = urllib.parse.urlencode((
        ('fullName', name),
        ('meetingID', meeting_id),
        ('password', password),
        ('redirect', "false"),
    ))

    hashed = api_call(query, call)
    url = settings.BBB_API_URL + call + '?' + hashed
    result = bbb_utils.parse_xml(requests.get(url).content.decode('utf-8'))

    return result


def join_url(meeting_id, name, password):
    """ This function is a wrapper for the `join_url` function in bbb.py

    :return: XML representation of the API result
    :rtype: XML
    """
    return BigBlueButton().join_url(meeting_id, name, password)
