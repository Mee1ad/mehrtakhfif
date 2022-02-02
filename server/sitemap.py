from datetime import datetime

from django.contrib.sitemaps import Sitemap

from server.models import Product, Category, Tag


class MySitemap(object):
    def __init__(self, model):
        self.model = model

    def get_absolute_url(self):
        return f"/{self.model}-sitemap.xml"


class BaseSitemap(Sitemap):
    changefreq = "monthly"
    priority = 1

    def items(self):
        return [MySitemap("product"), MySitemap("category")]

    def lastmod(self, obj):
        return datetime.now()


class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 1

    def items(self):
        return Product.objects.filter(available=True, disable=False).order_by('-id')

    def lastmod(self, obj):
        return obj.updated_at


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Category.objects.filter(disable=False).order_by('-id')

    def lastmod(self, obj):
        return obj.updated_at
