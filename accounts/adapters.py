from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class AccountAdapter(DefaultAccountAdapter):
    """Disable all local username/password signup — only Google OAuth allowed."""

    def is_open_for_signup(self, request):
        # Block any attempt to register through regular form signup
        return False


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """Allow signup through Google OAuth only."""

    def is_open_for_signup(self, request, sociallogin):
        # Only allow Google provider
        return sociallogin.account.provider == 'google'
