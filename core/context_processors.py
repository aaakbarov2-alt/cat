from django.conf import settings


def site_settings(request):
    return {
        "site_support_email": settings.SUPPORT_EMAIL,
        "social_facebook_url": settings.SOCIAL_FACEBOOK_URL,
        "social_instagram_url": settings.SOCIAL_INSTAGRAM_URL,
        "social_youtube_url": settings.SOCIAL_YOUTUBE_URL,
        "social_telegram_url": settings.SOCIAL_TELEGRAM_URL,
    }
