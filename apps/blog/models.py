"""Blog / news (SRS 6.10)."""
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags

from apps.core.models import PublishableModel, SEOFields, TimeStampedModel
from apps.core.utils import unique_slug


class Category(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.CharField(max_length=300, blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog:category", args=[self.slug])

    def __str__(self):
        return self.name


class Tag(TimeStampedModel):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class BlogPost(TimeStampedModel, SEOFields, PublishableModel):
    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True, blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                               on_delete=models.SET_NULL, related_name="posts")
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name="posts")
    tags = models.ManyToManyField(Tag, blank=True, related_name="posts")
    featured_image = models.ImageField(upload_to="blog/", blank=True, null=True)
    excerpt = models.CharField(max_length=400, blank=True)
    body = models.TextField()
    reading_time = models.PositiveIntegerField(default=1)
    view_count = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        indexes = [models.Index(fields=["status", "published_at"])]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.title, max_length=240)
        words = len(strip_tags(self.body or "").split())
        self.reading_time = max(1, round(words / 200))
        if self.status == "published" and not self.published_at:
            self.published_at = timezone.now()
        if not self.excerpt:
            self.excerpt = strip_tags(self.body or "")[:300]
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog:detail", args=[self.slug])

    def related_posts(self, limit=3):
        qs = BlogPost.objects.filter(status="published").exclude(pk=self.pk)
        tag_ids = list(self.tags.values_list("id", flat=True))
        if tag_ids:
            qs = qs.filter(tags__in=tag_ids).distinct()
        elif self.category_id:
            qs = qs.filter(category_id=self.category_id)
        return qs.select_related("category")[:limit]

    def __str__(self):
        return self.title
