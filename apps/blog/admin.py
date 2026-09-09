from django.contrib import admin

from apps.blog.models import BlogPost, Category, Tag


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "status", "published_at", "view_count")
    list_filter = ("status", "category")
    search_fields = ("title",)
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("tags",)


admin.site.register([Category, Tag])
