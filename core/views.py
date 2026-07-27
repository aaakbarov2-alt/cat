import logging

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import ContactForm


logger = logging.getLogger(__name__)


def home(request):
    return render(request, "home.html")


def faq(request):
    return render(request, "faq.html")


def privacy(request):
    return render(request, "privacy.html")


def terms(request):
    return render(request, "terms.html")


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        body = (
            f"Name: {form.cleaned_data['name']}\n"
            f"Email: {form.cleaned_data['email']}\n\n"
            f"{form.cleaned_data['message']}"
        )
        email = EmailMessage(
            subject=f"IELTS Mock support: {form.cleaned_data['subject']}",
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.SUPPORT_EMAIL],
            reply_to=[form.cleaned_data["email"]],
        )
        try:
            email.send(fail_silently=False)
        except Exception:
            logger.exception("Support contact email could not be sent")
            messages.error(
                request,
                "We could not send your message. Please try again shortly.",
            )
        else:
            messages.success(
                request,
                "Your message has been sent. We'll reply as soon as possible.",
            )
            return redirect("contact")
    return render(
        request,
        "contact.html",
        {"form": form, "support_email": settings.SUPPORT_EMAIL},
    )


def health(request):
    """Lightweight process and database readiness check for the host."""
    try:
        connection.ensure_connection()
    except Exception:
        return JsonResponse(
            {"status": "unhealthy", "database": "unavailable"}, status=503
        )
    return JsonResponse({"status": "ok", "database": "ok"})


def robots(request):
    sitemap_url = request.build_absolute_uri(reverse("sitemap"))
    body = f"User-agent: *\nAllow: /\nDisallow: /admin/\nSitemap: {sitemap_url}\n"
    return HttpResponse(body, content_type="text/plain")


def sitemap(request):
    urls = [
        request.build_absolute_uri(reverse("home")),
        request.build_absolute_uri(reverse("faq")),
        request.build_absolute_uri(reverse("privacy")),
        request.build_absolute_uri(reverse("terms")),
        request.build_absolute_uri(reverse("contact")),
    ]
    return render(
        request,
        "sitemap.xml",
        {"urls": urls},
        content_type="application/xml",
    )
