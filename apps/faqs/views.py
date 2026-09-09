from django.shortcuts import render

from apps.faqs.models import FAQ, FAQCategory


def faq_list(request):
    categories = FAQCategory.objects.prefetch_related("faqs")
    return render(request, "faqs/list.html", {
        "categories": categories,
        "uncategorised": FAQ.objects.filter(category__isnull=True, is_active=True),
        "meta_title": "Frequently Asked Questions | Dream Spot Global",
    })
