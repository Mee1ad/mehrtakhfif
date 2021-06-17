# documents.py

from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry
from elasticsearch_dsl import analyzer, tokenizer

from .models import Product, User, Category, Tag, Media, Brand

ngram = analyzer('ngram', tokenizer=tokenizer('trigram', 'nGram', min_gram=4, max_gram=4), filter=["lowercase"])
standard = analyzer('standard', tokenizer='standard')


@registry.register_document
class BrandDocument(Document):
    name_fa = fields.TextField(analyzer=standard, attr='__str__')
    id = fields.IntegerField()

    class Index:
        # Name of the Elasticsearch index
        name = 'brand'
        # See Elasticsearch Indices API reference for available settings
        settings = {'number_of_shards': 2,
                    'number_of_replicas': 2}

    class Django:
        model = Brand  # The model associated with this Document

        # The fields of the model you want to be indexed in Elasticsearch
        fields = []


@registry.register_document
class ProductDocument(Document):
    name_fa = fields.TextField(analyzer=standard, attr='get_name_fa')
    name_fa2 = fields.TextField(analyzer=ngram, attr='get_name_fa')
    category_fa = fields.TextField(attr='get_category_fa')
    thumbnail = fields.TextField(attr='get_thumbnail')
    id = fields.IntegerField()
    box_id = fields.IntegerField()
    type = fields.TextField(attr='get_type_display')

    class Index:
        # Name of the Elasticsearch index
        name = 'product'
        # See Elasticsearch Indices API reference for available settings
        settings = {'number_of_shards': 2,
                    'number_of_replicas': 2}

    class Django:
        model = Product  # The model associated with this Document

        # The fields of the model you want to be indexed in Elasticsearch
        fields = ['permalink', 'disable', 'available']


@registry.register_document
class CategoryDocument(Document):
    name_fa = fields.TextField(analyzer=standard, attr='get_name_fa')
    # name_fa2 = fields.TextField(analyzer=ngram, attr='get_name_fa')
    # name = fields.TextField(attr='get_name_fa')
    parent = fields.TextField(attr='get_parent_fa')
    box = fields.TextField(attr="get_box_name")
    media = fields.TextField(attr='get_media')
    id = fields.IntegerField()

    class Index:
        # Name of the Elasticsearch index
        name = 'category'
        # See Elasticsearch Indices API reference for available settings
        settings = {'number_of_shards': 2,
                    'number_of_replicas': 2}

    class Django:
        model = Category  # The model associated with this Document

        # The fields of the model you want to be indexed in Elasticsearch
        fields = ['permalink', 'disable']


@registry.register_document
class TagDocument(Document):
    name_fa = fields.TextField(analyzer=standard, attr='get_name_fa')
    name_fa2 = fields.TextField(analyzer=ngram, attr='get_name_fa')
    id = fields.IntegerField()

    class Index:
        # Name of the Elasticsearch index
        name = 'tag'
        # See Elasticsearch Indices API reference for available settings
        settings = {'number_of_shards': 2,
                    'number_of_replicas': 2}

    class Django:
        model = Tag  # The model associated with this Document

        # The fields of the model you want to be indexed in Elasticsearch
        fields = ['permalink']


@registry.register_document
class SupplierDocument(Document):
    id = fields.IntegerField()
    first_name = fields.TextField(analyzer=standard, attr='first_name')
    last_name = fields.TextField(analyzer=standard, attr='last_name')
    username = fields.TextField(attr='username')

    # avatar = fields.TextField(attr='get_avatar')

    class Index:
        # Name of the Elasticsearch index
        name = 'supplier'
        # See Elasticsearch Indices API reference for available settings
        settings = {'number_of_shards': 2,
                    'number_of_replicas': 2}

    class Django:
        model = User  # The model associated with this Document

        # The fields of the model you want to be indexed in Elasticsearch
        fields = ['is_supplier']


@registry.register_document
class MediaDocument(Document):
    name = fields.TextField(analyzer=standard, attr='__str__')
    id = fields.IntegerField()

    class Index:
        # Name of the Elasticsearch index
        name = 'media'
        # See Elasticsearch Indices API reference for available settings
        settings = {'number_of_shards': 2,
                    'number_of_replicas': 2}

    class Django:
        model = Media  # The model associated with this Document

        # The fields of the model you want to be indexed in Elasticsearch
        fields = []
