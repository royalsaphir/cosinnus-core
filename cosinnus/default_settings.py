# -*- coding: utf-8 -*-

"""
Django settings for cosinnus projects.

For more information on this file, see
https://docs.djangoproject.com/en/dev/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/dev/ref/settings/
"""

import sys
from os.path import dirname, join, realpath

from django.utils.translation import ugettext_lazy as _


# this is the default portal, and will change the location of the staticfiles
COSINNUS_PORTAL_NAME = None


DEBUG = False

ADMINS = ()
MANAGERS = ()

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ()

DATABASES = {}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Europe/Berlin'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'de'

SITE_ID = 1

FILE_CHARSET = 'utf-8'

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True


# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

LOGIN_URL = '/login/'


# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'


# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    # 'django.contrib.staticfiles.finders.DefaultStorageFinder',
    
    'compressor.finders.CompressorFinder',
)

MIDDLEWARE = [
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'cosinnus.core.middleware.cosinnus_middleware.MovedTemporarilyRedirectFallbackMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'cosinnus.core.middleware.cosinnus_middleware.AdminOnlyOTPMiddleware',
    
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    'wagtail.core.middleware.SiteMiddleware',
    'wagtail.contrib.redirects.middleware.RedirectMiddleware',
    
    'cosinnus.core.middleware.cosinnus_middleware.StartupMiddleware',
    #'cosinnus.core.middleware.cosinnus_middleware.ForceInactiveUserLogoutMiddleware',
    'cosinnus.core.middleware.cosinnus_middleware.ConditionalRedirectMiddleware',
    'cosinnus.core.middleware.cosinnus_middleware.AddRequestToModelSaveMiddleware',
    'cosinnus.core.middleware.cosinnus_middleware.GroupPermanentRedirectMiddleware',
    'cosinnus.core.middleware.login_ratelimit_middleware.LoginRateLimitMiddleware',
]


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            # base directory is being put in by the main app's settings file
        ],
        'OPTIONS': {
            'context_processors': (
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.template.context_processors.csrf',
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
                'sekizai.context_processors.sekizai',
                'postman.context_processors.inbox',
                'cosinnus.utils.context_processors.settings',
                'cosinnus.utils.context_processors.cosinnus',
                'cosinnus.utils.context_processors.tos_check',
                'announcements.context_processors.add_custom_announcements',
             ),
            'loaders': (
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
                'cosinnus.loaders.eggs.Loader',
            ),
            'debug': DEBUG,
        }
    },
]


def compile_installed_apps(internal_apps=[]):
    """ Supports gathering INSTALLED_APPS with external-project options.
        Must be called after importing these settings!
    """
    
    _INSTALLED_APPS = [
        # Django Apps
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.humanize',
        'django.contrib.messages',
        'django.contrib.redirects',
        'django.contrib.sessions',
        'django.contrib.sites',
        'django.contrib.staticfiles',
        'suit_overextends',
        'suit',
        'django.contrib.admin',
        'sekizai',
        
        # haystack needs to precede wagtail because wagtail idiotically overrides haystack's mmanagement commands
        'haystack',
        
        # wagtail
        'wagtail_overextends',
        'compressor',
        'modelcluster',
        'wagtail.core',
        'wagtail.admin',
        'wagtail.documents',
        'wagtail.snippets',
        'wagtail.users',
        'wagtail.images',
        'wagtail.embeds',
        'wagtail.search',
        'wagtail.sites',
        'wagtail.contrib.redirects',
        'wagtail.contrib.forms',
        
    ]
    
    # Internal Apps (as defined in external project)
    _INSTALLED_APPS += internal_apps
    
    _INSTALLED_APPS += [
        'cosinnus',
        'cosinnus_etherpad',
        'cosinnus_event',
        'cosinnus_file',
        'cosinnus_marketplace',
        'cosinnus_message',
        'cosinnus_note',
        'cosinnus_notifications',
        'cosinnus_poll',
        'cosinnus_stream',
        'cosinnus_todo',
        'announcements',
        'ajax_forms',
        
        # 'django_extensions',
        'django_filters',
        'django_select2',
        'django_cron',
        'widget_tweaks',
        'django_otp',
        'django_otp.plugins.otp_totp',
        
        # External Apps
        'awesome_avatar',
        'bootstrap3',
        'bootstrap3_datetime',
        'captcha',
        'djajax',
        'django_mailbox',
        'easy_thumbnails',
        'embed_video',
        'el_pagination',
        'honeypot',
        'osm_field',
        'phonenumber_field',
        'postman',
        'raven.contrib.django.raven_compat',
        'oauth2_provider',
        'corsheaders',
        'rest_framework',
        'rest_framework_swagger',
        'taggit',
    ]
    return _INSTALLED_APPS

LANGUAGES = [
    ('de', _('Deutsch--NATIVE-LANGUAGE')),
    ('en', _('English--NATIVE-LANGUAGE')),
    ('ru', _('Russian--NATIVE-LANGUAGE')),
    ('uk', _('Ukrainian--NATIVE-LANGUAGE')),
    # other languages available, but not yet, or not by default
    # (enable them for your specific portals by defining `LANGUAGES` in settings.py
    ('fr', _('French--NATIVE-LANGUAGE')),
    ('pl', _('Polish--NATIVE-LANGUAGE')),
]

SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'root': {
        'level': 'WARNING',
        'handlers': ['sentry'],
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
    },
    'handlers': {
        'sentry': {
            'level': 'INFO',
            'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        }
    },
    'loggers': {
        'django.db.backends': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': False,
        },
        'raven': {
            'level': 'DEBUG',
            'handlers': ['console', 'sentry'],
            'propagate': False,
        },
        'sentry.errors': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
        'cosinnus': {
            'level': 'DEBUG',
            'handlers': ['console', 'sentry'],
            'propagate': False,
        },
    },
}

# allow a lot of POST parameters (notification settings will have many fields)
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000 

# Required for cmsplugin_filer_image
THUMBNAIL_PROCESSORS = (
    'easy_thumbnails.processors.colorspace',
    'easy_thumbnails.processors.autocrop',
    # 'easy_thumbnails.processors.scale_and_crop',
    'filer.thumbnail_processors.scale_and_crop_with_subject_location',
    'easy_thumbnails.processors.filters',
)
# this namer prevents exposing the source file in its path
THUMBNAIL_NAMER = 'easy_thumbnails.namers.hashed'


EL_PAGINATION_PER_PAGE = 8
EL_PAGINATION_PREVIOUS_LABEL = '<b>&#9001;</b> Zurück'
EL_PAGINATION_NEXT_LABEL = 'Weiter <b>&#9002;</b>'

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'


# detect testing mode
TESTING = 'test' in sys.argv

# use session storage for CSRF instead of cookie
# can't use this yet, until we fix the jQuery-POST usage of csrf cookies
CSRF_USE_SESSIONS = False

# leave this on for production, but may want to disable for dev
#SESSION_COOKIE_SECURE = True

# wagtail
WAGTAIL_SITE_NAME = 'Wechange'
WAGTAIL_ENABLE_UPDATE_CHECK = False


""" Default non-cosinnus specific settings i.e. for third-party apps.
    
    These *MUST* be imported in the settings.py of the app using cosinnus!

    Unless you have a good reason and plan to implement replacement solutions
    you should probably leave these as they are.
    
    For cosinnus-specific internal default settings, check cosinnus/conf.py!
"""

AUTHENTICATION_BACKENDS = ['cosinnus.backends.EmailAuthBackend',]

# select2 render static files
AUTO_RENDER_SELECT2_STATICS = False
    
AWESOME_AVATAR = {
    'width': 263,
    'height': 263,
    'select_area_width': 263,
    'select_area_height': 263,
    'save_quality': 100,
    'save_format': 'png',
    'no_resize': True,
}

FORMAT_MODULE_PATH = 'cosinnus.formats'


# this processor is tied to any save/delete signals of models,
# If the model has an associated SearchIndex, the RealtimeSignalProcessor 
# will then trigger an update/delete of that model instance within the search index proper.
HAYSTACK_SIGNAL_PROCESSOR = 'haystack.signals.RealtimeSignalProcessor'


# django-cron cronjob class definitions
# TODO: FIXME: this should be inverted, ie each cosinnus app should set these settings!
# cosinnus-core should not know about other cosinnus apps here!
CRON_CLASSES = [
    'cosinnus_marketplace.cron.DeactivateExpiredOffers',
    'cosinnus_message.cron.ProcessDirectReplyMails',
]
# delete cronjob logs older than 30 days
DJANGO_CRON_DELETE_LOGS_OLDER_THAN = 30


""" -----------  Important Cosinnus-specific settings:  ----------- """


# Tag objects
COSINNUS_TAG_OBJECT_FORM = 'cosinnus.forms.tagged.TagObjectForm'
COSINNUS_TAG_OBJECT_MODEL = 'cosinnus.TagObject'
COSINNUS_TAG_OBJECT_SEARCH_INDEX = 'cosinnus.utils.search.TagObjectIndex'

COSINNUS_GROUP_OBJECT_MODEL = 'cosinnus.CosinnusGroup'

# Microsite
COSINNUS_MICROSITE_RENDER_EMPTY_APPS = False

# Default title for all pages unless the title block is overwritten. 
# This is put through a {% trans %} tag. """
COSINNUS_BASE_PAGE_TITLE_TRANS = ''

# Etherpad config.
# Warning: Etherpad URL and KEY are usually overwritten in settings.py on the server! """
COSINNUS_ETHERPAD_BASE_URL = None
COSINNUS_ETHERPAD_API_KEY = None

# Ethercalc config
COSINNUS_ETHERPAD_ENABLE_ETHERCALC = True
COSINNUS_ETHERPAD_ETHERCALC_BASE_URL = None

# Chat config
COSINNUS_CHAT_BASE_URL = None
COSINNUS_CHAT_GROUP_GENERAL = '%s-general'
COSINNUS_CHAT_GROUP_NEWS = '%s-news'
COSINNUS_CHAT_SETTINGS = {
    # General
    'UTF8_Names_Validation': '[0-9a-zA-Z-_.äÄöÖüÜß]+',

    # Accounts
    #'Accounts_AllowAnonymousRead': False,
    #'Accounts_AllowAnonymousWrite': False,
    #'Accounts_AllowDeleteOwnAccount': False,
    'Accounts_AllowEmailChange': True,
    'Accounts_AllowPasswordChange': False,
    'Accounts_AllowRealNameChange': True,
    'Accounts_AllowUserAvatarChange': True,
    'Accounts_AllowUserProfileChange': False,
    #'Accounts_AllowUserStatusMessageChange': True,
    'Accounts_AllowUsernameChange': False,
    'Accounts_ShowFormLogin': True,
    #'Accounts_Default_User_Preferences_sidebarGroupByType': False,
    #'Accounts_Default_User_Preferences_hideUsernames': True,

    # Layout
    'Layout_Home_Body': '''<p>Willkommen bei Rocket.Chat!</p>
<p>Die Rocket.Chat-Desktops-Apps für Windows, MacOS und Linux stehen <a title="Rocket.Chat desktop apps" href="https://rocket.chat/download" target="_blank" rel="noopener">hier</a> zum Download bereit..</p>
<p>Die native Mobile-App Rocket.Chat für Android und iOS ist bei <a title="Rocket.Chat+ on Google Play" href="https://play.google.com/store/apps/details?id=chat.rocket.android" target="_blank" rel="noopener">Google Play</a> und im  <a title="Rocket.Chat+ on the App Store" href="https://itunes.apple.com/app/rocket-chat/id1148741252" target="_blank" rel="noopener">App Store</a> erhältlich.</p>
<p>Weitere Informationen finden Sie in der <a title="Rocket.Chat Documentation" href="https://rocket.chat/docs/" target="_blank" rel="noopener">Dokumentation</a>.</p>
''',
    'Layout_Terms_of_Service': '<a href="https://plattform-n.org/cms/datenschutz/">Nutzungsbedingungen</a><br><a href="https://wechange.de/cms/datenschutz/">Datenschutz</a>',
    'Layout_Login_Terms': 'Indem Sie fortfahren, stimmen Sie unseren <a href="https://plattform-n.org/cms/nutzungsbedingungen/">Nutzungs-</a> und <a href="https://wechange.de/cms/datenschutz/">Datenschutzbestimmungen</a> zu.',
    'Layout_Privacy_Policy': '<a href="https://wechange.de/cms/datenschutz/">Datenschutz</a>',
    #'UI_Group_Channels_By_Type': False,
    'UI_Use_Real_Name': True,

    # Rate Limiter
    'API_Enable_Rate_Limiter_Limit_Calls_Default': 100,
}

# default from-email:
COSINNUS_DEFAULT_FROM_EMAIL = ''
DEFAULT_FROM_EMAIL = COSINNUS_DEFAULT_FROM_EMAIL

# settings for email-dkim signing. you can follow this guide for creating a key https://blog.codinghorror.com/so-youd-like-to-send-some-email-through-code/ (point 2)
DKIM_DOMAIN = None # e.g. 'example.com'
DKIM_SELECTOR = None # e.g. 'selector' if using selector._domainkey.example.com
DKIM_PRIVATE_KEY = None # full private key string, including """-----BEGIN RSA PRIVATE KEY-----""", etc
# set these settings in your server's settings.py. then if you have all of them, you also need to include this:
if DKIM_SELECTOR and DKIM_DOMAIN and DKIM_PRIVATE_KEY: 
    EMAIL_BACKEND = 'cosinnus.backends.DKIMEmailBackend'

COSINNUS_SITE_PROTOCOL = 'http'

# should microsites be enabled per default for all portals?
# (can be set for each portal individually in their settings.py)
COSINNUS_MICROSITES_ENABLED = True


# CELERY STUFF
# set this in each portal's settings.py!
#COSINNUS_USE_CELERY = True
#BROKER_URL = 'redis://localhost:6379/%d' % SITE_ID
CELERY_RESULT_BACKEND = 'redis://localhost:6379'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json' 
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Berlin'


# django upload restriction settings
# POST body size
DATA_UPLOAD_MAX_MEMORY_SIZE = 20971520 # 20mb (default is 2.5mb)
# File upload size
FILE_UPLOAD_MAX_MEMORY_SIZE = 524288000 # 500mb (default is 2.5mb)

CSRF_FAILURE_VIEW = 'cosinnus.views.common.view_403_csrf'

""" -----------  More configurable Cosinnus settings (for defaults check cosinnus/conf.py!)  ----------- """

#AWESOME_AVATAR = {...}
#COSINNUS_USER_PROFILE_MODEL = 'cosinnus.UserProfile'
#COSINNUS_ATTACHABLE_OBJECTS = {...}
#COSINNUS_ATTACHABLE_OBJECTS_SUGGEST_ALIASES = {...}
#COSINNUS_INITIAL_GROUP_WIDGETS = [...]
#COSINNUS_INITIAL_GROUP_MICROSITE_WIDGETS = [...]
#COSINNUS_INITIAL_USER_WIDGETS = [...]
#COSINNUS_MICROSITE_DISPLAYED_APP_OBJECTS = [...] 
# Navbar display in the apps menu
#COSINNUS_HIDE_APPS = [(...)]

# LOGIN Rate limiting settings:
LOGIN_RATELIMIT_USERNAME_FIELD = 'email'
LOGIN_RATELIMIT_LOGIN_URLS = {
    '/admin/login/': 'username',
    '/login/': 'username',
}
LOGIN_RATELIMIT_LOGGER_NAME = 'cosinnus'


""" -----------  This app's cosinnus-related custom settings  ----------- """

# new users that register will automatically be assigned these django permission groups
NEWW_DEFAULT_USER_AUTH_GROUPS = ['Users']

# new user that register will automatically become members of these groups/projects (supply group slugs!)
NEWW_DEFAULT_USER_GROUPS = ['forum']

# these groups will accept members instantly after requesting membership
COSINNUS_AUTO_ACCEPT_MEMBERSHIP_GROUP_SLUGS = ['forum']

# the "Home" group for this portal. if not set, some things won't work (like attaching files to direct messages)
NEWW_FORUM_GROUP_SLUG = 'forum'

# the resident "Events" group for this portal. set this to thhe `NEWW_FORUM_GROUP_SLUG` if there isn't a seperate group!
NEWW_EVENTS_GROUP_SLUG = NEWW_FORUM_GROUP_SLUG


# if enabled, group admins will see a "rearrange" button and can re-order the widgets.
# pretty wonky and unintuitive right now, so be careful!
COSINNUS_ALLOW_DASHBOARD_WIDGET_REARRANGE = False

# Default country code to assume when none is entered for django-phonenumber-field
PHONENUMBER_DEFAULT_REGION = 'DE'

# PIWIK settings. set individually for each portal. won't load if PIWIK_SITE_ID is not set
PIWIK_SERVER_URL = '//stats.wechange.de/'
PIWIK_SITE_ID = None

# Cookie settings. We will let cookies expire browser-session-based for anonymous users, and keep them
# for 30 days for logged in users
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
COSINNUS_SESSION_EXPIRY_AUTHENTICATED_IN_USERS = 60 * 60 * 24 * 60 # 60 days

# honeypot field name shouldn't be too obvious, but also not trigger browsers' autofill
HONEYPOT_FIELD_NAME = 'phnoenumber_8493'

# API AND SWAGGER SETTINGS
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'oauth2_provider.contrib.rest_framework.OAuth2Authentication',
    )
}
SWAGGER_SETTINGS = {
    'api_version': '2',
    'api_path': '/api/v2/',
    'api_key': 'wechange',
    'info': {
        'contact': 'support@wechange.de',
        'description': '',
        'license': 'AGPL 3.0',
        'licenseUrl': 'https://www.gnu.org/licenses/agpl-3.0.de.html',
        #'termsOfServiceUrl': 'http://helloreverb.com/terms/',
        'title': 'WECHANGE API',
    },
}

SUIT_CONFIG = {
    'ADMIN_NAME': 'Wechange Admin'
}

# 2-factor authentication issuer name for admin backend
OTP_TOTP_ISSUER = 'WECHANGE eG'

# django-simple captcha settings
CAPTCHA_CHALLENGE_FUNCT = 'cosinnus.utils.captcha.dissimilar_random_char_challenge'
CAPTCHA_NOISE_FUNCTIONS = ('captcha.helpers.noise_dots',)
CAPTCHA_TIMEOUT = 30

COSINNUS_ROCKET_ENABLED = False
COSINNUS_ROCKET_EXPORT_ENABLED = False