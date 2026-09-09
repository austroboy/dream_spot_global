from django.core.paginator import Paginator
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, render

from apps.blog.models import BlogPost, Category, Tag


def post_list(request):
    qs = BlogPost.objects.filter(status="published").select_related("category", "author")
    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(excerpt__icontains=q) | Q(body__icontains=q))
    page = Paginator(qs, 9).get_page(request.GET.get("page"))
    return render(request, "blog/list.html", {
        "page_obj": page, "categories": Category.objects.all(), "q": q,
        "featured": qs.filter(is_featured=True).first(),
        "meta_title": "Study Abroad News & Guides | Dream Spot Global",
    })


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    qs = BlogPost.objects.filter(status="published", category=category)
    page = Paginator(qs, 9).get_page(request.GET.get("page"))
    return render(request, "blog/list.html", {
        "page_obj": page, "categories": Category.objects.all(), "category": category,
        "meta_title": f"{category.name} | Dream Spot Global Blog",
    })


def tag_detail(request, slug):
    tag = get_object_or_404(Tag, slug=slug)
    qs = BlogPost.objects.filter(status="published", tags=tag)
    page = Paginator(qs, 9).get_page(request.GET.get("page"))
    return render(request, "blog/list.html", {
        "page_obj": page, "categories": Category.objects.all(), "tag": tag,
        "meta_title": f"#{tag.name} | Dream Spot Global Blog",
    })


def post_detail(request, slug):
    post = get_object_or_404(
        BlogPost.objects.select_related("author", "category").prefetch_related("tags"),
        slug=slug, status="published")
    BlogPost.objects.filter(pk=post.pk).update(view_count=F("view_count") + 1)
    return render(request, "blog/detail.html", {
        "post": post, "related": post.related_posts(),
        "meta_title": post.meta_title or post.title,
        "meta_description": post.meta_description or post.excerpt,
    })
