from django.contrib.auth.views import PasswordResetView
from django.shortcuts import reverse, redirect
from django.urls import resolve
from cosinnus.views.user import SetInitialPasswordView
from django.http import HttpResponse, HttpResponseRedirect
from cosinnus.models.profile import PROFILE_SETTING_PASSWORD_NOT_SET


class SetPasswordMiddleware:
    """ This middleware checks if a user is created without a password, and will redirect the user to the set
        initial password view, if the token for setting the password was provided.
        When a user tries to leave the set password view without setting a password the token will be saved in
        request.COOKIES helping identifying the user in the redirection.

        Display of 403 or 404 pages respectively is provided by the set_password view.

        Logout view will not be redirected,

        """
    def __init__(self, get_repsonse):
        self.get_response = get_repsonse

    def requested_initial_password(self, func):
        if not hasattr(func, 'view_class'):
            return False
        elif func.view_class == SetInitialPasswordView:
            return True
        return False

    def __call__(self, request):
        func, args, kwargs = resolve(request.path)
        token = kwargs.get('token', '') if 'token' in kwargs else request.COOKIES.get(PROFILE_SETTING_PASSWORD_NOT_SET, '')

        if request.path == reverse('logout') or request.path == '/':
            response = self.get_response(request)
            return response

        elif self.requested_initial_password(func) and token:
            # request.COOKIES[PROFILE_SETTING_PASSWORD_NOT_SET] = token

            response = self.get_response(request)
            if not request.COOKIES.get(PROFILE_SETTING_PASSWORD_NOT_SET):
                response.set_cookie(PROFILE_SETTING_PASSWORD_NOT_SET, token)
            return response
        else:
            return HttpResponseRedirect(reverse('password_set_initial'))

    def process_request(self, request, response):
        return request
        pass