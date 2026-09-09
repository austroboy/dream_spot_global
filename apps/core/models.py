"""Core models: abstract bases, site settings, static pages, audit log (SRS 9.3, FR-USR-03/04)."""
from django.conf import settings
from django.db import models
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    """SRS DM-01: every model carries created/updated stamps and authorship."""
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="+")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="+")

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(is_deleted=False)


class SoftDeleteManager(models.Manager):
    """SRS DM-02: default manager hides soft-deleted rows."""
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)


class SoftDeleteModel(TimeStampedModel):
    is_deleted = models.BooleanField(default=False, db_index=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def soft_delete(self):
        self.is_deleted = True
        self.save(update_fields=["is_deleted", "updated_at"])


class SEOFields(models.Model):
    """SRS FR-CMS-05 / SEO-01."""
    meta_title = models.CharField(max_length=180, blank=True)
    meta_description = models.CharField(max_length=320, blank=True)
    canonical_url = models.URLField(blank=True)
    og_image = models.ImageField(upload_to="seo/", blank=True, null=True)
    noindex = models.BooleanField(default=False)

    class Meta:
        abstract = True


class PublishableModel(models.Model):
    STATUS = [("draft", "Draft"), ("scheduled", "Scheduled"), ("published", "Published")]
    status = models.CharField(max_length=12, choices=STATUS, default="draft", db_index=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        abstract = True

    @property
    def is_live(self):
        from django.utils import timezone
        return self.status == "published" and (self.published_at is None
                                               or self.published_at <= timezone.now())


class SingletonModel(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class SiteSettings(SingletonModel):
    """SRS 2.3 / FR-USR-03 — all company info is editable, never hard-coded (CON-05)."""
    company_name = models.CharField(max_length=120, default="Dream Spot Global")
    tagline = models.CharField(max_length=160, default="Education • Career • Immigration")
    business_type = models.CharField(max_length=120, default="Study Abroad Education Consultancy")
    about_short = models.TextField(blank=True)

    logo = models.ImageField(upload_to="brand/", blank=True, null=True)
    logo_light = models.ImageField(upload_to="brand/", blank=True, null=True)
    favicon = models.ImageField(upload_to="brand/", blank=True, null=True)

    address = models.CharField(max_length=255,
                               default="House 21, Road 01, Sector 9, Uttara, Dhaka, Bangladesh")
    phone_primary = models.CharField(max_length=32, default="+880 1410-157209")
    phone_secondary = models.CharField(max_length=32, blank=True, default="+880 1612649451")
    email = models.EmailField(default="dreamspotglobal@gmail.com")
    whatsapp = models.CharField(max_length=32, blank=True, default="8801410157209")
    office_hours = models.CharField(max_length=160, blank=True,
                                    default="Saturday – Thursday, 10:00 AM – 7:00 PM")
    map_embed = models.TextField(blank=True, help_text="Google Maps iframe embed code")

    facebook = models.URLField(blank=True, default="https://www.facebook.com/dreamspotglobalpage")
    instagram = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    youtube = models.URLField(blank=True)

    stat_students = models.CharField(max_length=20, default="1,200+")
    stat_universities = models.CharField(max_length=20, default="450+")
    stat_visa_success = models.CharField(max_length=20, default="97%")
    stat_countries = models.CharField(max_length=20, default="8")

    ga4_id = models.CharField(max_length=40, blank=True)
    gtm_id = models.CharField(max_length=40, blank=True)
    meta_pixel_id = models.CharField(max_length=40, blank=True)
    search_console_token = models.CharField(max_length=120, blank=True)

    lead_assignment_mode = models.CharField(
        max_length=20, default="round_robin",
        choices=[("round_robin", "Round robin"), ("by_country", "By destination country"),
                 ("manual", "Manual only")])
    maintenance_mode = models.BooleanField(default=False)
    maintenance_message = models.CharField(max_length=255, blank=True)

    default_meta_title = models.CharField(max_length=180, blank=True)
    default_meta_description = models.CharField(max_length=320, blank=True)

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def __str__(self):
        return self.company_name

    @property
    def whatsapp_link(self):
        return f"https://wa.me/{self.whatsapp}" if self.whatsapp else ""

    @property
    def social_links(self):
        return [(n, u, i) for n, u, i in [
            ("Facebook", self.facebook, "facebook"),
            ("Instagram", self.instagram, "instagram"),
            ("LinkedIn", self.linkedin, "linkedin"),
            ("YouTube", self.youtube, "youtube"),
        ] if u]


class HomepageSection(TimeStampedModel):
    """SRS FR-HOM-02: every homepage band is toggleable and reorderable."""
    KEYS = [
        ("hero", "Hero"), ("stats", "Trust bar"), ("destinations", "Study destinations"),
        ("services", "Our services"), ("why_us", "Why Dream Spot Global"),
        ("journey", "Your study abroad journey"), ("universities", "Featured universities"),
        ("scholarships", "Scholarship highlights"), ("events", "Upcoming events"),
        ("testimonials", "Success stories"), ("blog", "Latest from the blog"),
        ("faq", "FAQ"), ("cta", "Free assessment CTA"),
    ]
    key = models.CharField(max_length=32, choices=KEYS, unique=True)
    eyebrow = models.CharField(max_length=80, blank=True)
    heading = models.CharField(max_length=160, blank=True)
    subheading = models.CharField(max_length=320, blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order"]

    def __str__(self):
        return self.get_key_display()


class HeroSlide(TimeStampedModel):
    """SRS FR-HOM-03."""
    heading = models.CharField(max_length=180)
    subheading = models.CharField(max_length=320, blank=True)
    image = models.ImageField(upload_to="hero/", blank=True, null=True)
    cta_text = models.CharField(max_length=60, blank=True, default="Book Free Counselling")
    cta_url = models.CharField(max_length=255, blank=True, default="/book-counselling/")
    cta2_text = models.CharField(max_length=60, blank=True, default="Explore Destinations")
    cta2_url = models.CharField(max_length=255, blank=True, default="/study-abroad/")
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order"]

    def __str__(self):
        return self.heading


class WhyUsPoint(TimeStampedModel):
    icon = models.CharField(max_length=40, default="award")
    title = models.CharField(max_length=120)
    description = models.CharField(max_length=300)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order"]

    def __str__(self):
        return self.title


class JourneyStep(TimeStampedModel):
    """SRS §4.5 item 6 — the six-step process band."""
    number = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=120)
    description = models.CharField(max_length=300, blank=True)
    icon = models.CharField(max_length=40, default="compass")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["number"]

    def __str__(self):
        return f"{self.number}. {self.title}"


class TeamMember(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    designation = models.CharField(max_length=120)
    photo = models.ImageField(upload_to="team/", blank=True, null=True)
    bio = models.TextField(blank=True)
    email = models.EmailField(blank=True)
    linkedin = models.URLField(blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:140]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Page(TimeStampedModel, SEOFields, PublishableModel):
    """SRS FR-CMS-02: admins can add static pages without a developer."""
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True)
    body = models.TextField(blank=True)
    show_in_footer = models.BooleanField(default=False)

    class Meta:
        ordering = ["title"]

    def get_absolute_url(self):
        return f"/{self.slug}/"

    def __str__(self):
        return self.title


class Redirect(TimeStampedModel):
    """SRS URL-02 / SEO-07 — 301s created automatically on slug change."""
    old_path = models.CharField(max_length=300, unique=True, db_index=True)
    new_path = models.CharField(max_length=300)
    is_permanent = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.old_path} -> {self.new_path}"


class AuditLog(models.Model):
    """SRS FR-USR-04 — read-only trail of every business data change."""
    ACTIONS = [("create", "Create"), ("update", "Update"), ("delete", "Delete"),
               ("login", "Login"), ("view", "Sensitive view")]
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="audit_entries")
    action = models.CharField(max_length=12, choices=ACTIONS)
    model_name = models.CharField(max_length=80)
    object_id = models.CharField(max_length=40, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["model_name", "object_id"])]

    def __str__(self):
        return f"{self.action} {self.model_name}#{self.object_id}"


class ContactMessage(TimeStampedModel):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=32, blank=True)
    subject = models.CharField(max_length=180, blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} — {self.subject or 'Message'}"
