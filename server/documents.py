# documents.py

from django_elasticsearch_dsl import Document, fields
from elasticsearch_dsl import analyzer, tokenizer
from django_elasticsearch_dsl.registries import registry
from .models import Product, User, Category, Tag

ngram = analyzer('ngram', tokenizer=tokenizer('trigram', 'nGram', min_gram=3, max_gram=3), filter=["lowercase"])


@registry.register_document
class ProductDocument(Document):
    name_fa = fields.TextField(analyzer=ngram, attr='get_name_fa')
    # name_en = fields.TextField(attr='get_name_en')
    # name_ar = fields.TextField(attr='get_name_ar')

    category_fa = fields.TextField(attr='get_category_fa')
    # category_en = fields.TextField(attr='get_category_en')
    # category_ar = fields.TextField(attr='get_category_ar')

    thumbnail = fields.TextField(attr='get_thumbnail')
    id = fields.IntegerField()
    box_id = fields.IntegerField()
    type = fields.TextField(attr='get_type_display')

    class Index:
        # Name of the Elasticsearch index
        name = 'product'
        # See Elasticsearch Indices API reference for available settings
        settings = {'number_of_shards': 1,
                    'number_of_replicas': 0}

    class Django:
        model = Product  # The model associated with this Document

        # The fields of the model you want to be indexed in Elasticsearch
        fields = ['permalink']


@registry.register_document
class CategoryDocument(Document):
    name_fa = fields.TextField(analyzer=ngram, attr='get_name_fa')
    name = fields.TextField(attr='get_name_fa')
    media = fields.TextField(attr='get_media')
    id = fields.IntegerField()

    class Index:
        # Name of the Elasticsearch index
        name = 'category'
        # See Elasticsearch Indices API reference for available settings
        settings = {'number_of_shards': 1,
                    'number_of_replicas': 0}

    class Django:
        model = Category  # The model associated with this Document

        # The fields of the model you want to be indexed in Elasticsearch
        fields = ['permalink']


@registry.register_document
class TagDocument(Document):
    name_fa = fields.TextField(analyzer=ngram, attr='get_name_fa')
    name = fields.TextField(attr='get_name_fa')
    id = fields.IntegerField()

    class Index:
        # Name of the Elasticsearch index
        name = 'tag'
        # See Elasticsearch Indices API reference for available settings
        settings = {'number_of_shards': 1,
                    'number_of_replicas': 0}

    class Django:
        model = Tag  # The model associated with this Document

        # The fields of the model you want to be indexed in Elasticsearch
        fields = ['permalink']


@registry.register_document
class SupplierDocument(Document):
    id = fields.IntegerField()
    first_name = fields.TextField(analyzer=ngram, attr='first_name')
    last_name = fields.TextField(analyzer=ngram, attr='last_name')
    username = fields.TextField(analyzer=ngram, attr='username')
    # avatar = fields.TextField(attr='get_avatar')

    class Index:
        # Name of the Elasticsearch index
        name = 'supplier'
        # See Elasticsearch Indices API reference for available settings
        settings = {'number_of_shards': 1,
                    'number_of_replicas': 0}

    class Django:
        model = User  # The model associated with this Document

        # The fields of the model you want to be indexed in Elasticsearch
        fields = ['is_supplier']
