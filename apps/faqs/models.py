"""Categorised FAQ bank (SRS 6.x / FR-SRV-02)."""
from django.db import models

from apps.core.models import TimeStampedModel


class FAQCategory(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name_plural = "FAQ categories"

    def save(self, *args, **kwargs):
        from apps.core.utils import unique_slug
        if not self.slug:
            self.slug = unique_slug(self, self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class FAQ(TimeStampedModel):
    category = models.ForeignKey(FAQCategory, null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name="faqs")
    country = models.ForeignKey("destinations.Country", null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="faqs")
    service = models.ForeignKey("services.Service", null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="faqs")
    question = models.CharField(max_length=300)
    answer = models.TextField()
    show_on_homepage = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return self.question
