# documents.py

from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry
from elasticsearch_dsl import analyzer, tokenizer

from .models import Product, User, Category, Tag, Media, Brand, Storage

ngram = analyzer('ngram', tokenizer=tokenizer('trigram', 'nGram', min_gram=2, max_gram=3), filter=["lowercase"])
standard = analyzer('standard', tokenizer='standard')


@registry.register_document
class ProductDocument(Document):
    id = fields.IntegerField()
    category = fields.ObjectField(properties={
        'id': fields.IntegerField(),
        'name': fields.TextField("__str__"),
        'permalink': fields.KeywordField(),
    })
    name_fa = fields.TextField(analyzer=standard, attr='get_name_fa')
    name_fa2 = fields.TextField(analyzer=ngram, attr='get_name_fa')
    thumbnail = fields.TextField(attr='get_thumbnail')
    type = fields.TextField(attr='get_type_display')
    tags = fields.ListField(fields.TextField("get_tags"))
    categories = fields.NestedField(properties={
        'id': fields.IntegerField(),
        'name': fields.TextField(),
        'permalink': fields.KeywordField()
    }, attr="get_categories")
    disable = fields.BooleanField(attr='is_disable')
    default_storage = fields.ObjectField(properties={
        'title': fields.TextField("__str__"),
        'discount_price': fields.IntegerField(),
        'discount_percent': fields.IntegerField(),
        'final_price': fields.IntegerField(),
        'sold_count': fields.IntegerField()
    })
    brand = fields.ObjectField(properties={
        'id': fields.IntegerField(),
        'name': fields.TextField("__str__"),
        'permalink': fields.KeywordField(),
    })
    colors = fields.NestedField(properties={
        'id': fields.IntegerField(),
        'name': fields.TextField(),
        'color': fields.TextField()
    }, attr="get_colors")

    class Index:
        # Name of the Elasticsearch index
        name = 'product'
        # See Elasticsearch Indices API reference for available settings
        settings = {'number_of_shards': 2,
                    'number_of_replicas': 2}

    class Django:
        model = Product  # The model associated with this Document

        # The fields of the model you want to be indexed in Elasticsearch
        fields = ['permalink', 'available']
        related_models = [Tag, Storage, Brand, Category]

    def get_queryset(self):
        """Not mandatory but to improve performance we can select related in one sql request"""
        return super(ProductDocument, self).get_queryset().select_related(
            'brand', 'thumbnail', 'default_storage'
        )

    def get_instances_from_related(self, related_instance):
        """If related_models is set, define how to retrieve the Car instance(s) from the related model.
        The related_models option should be used with caution because it can lead in the index
        to the updating of a lot of items.
        """
        if isinstance(related_instance, Brand):
            return related_instance.products.all()
        elif isinstance(related_instance, Tag):
            return related_instance.products.all()
        elif isinstance(related_instance, Media):
            return related_instance.products.all()
        elif isinstance(related_instance, Storage):
            return related_instance.product_default_storage
        elif isinstance(related_instance, Category):
            return related_instance.products.all()


@registry.register_document
class CategoryDocument(Document):
    name_fa = fields.TextField(analyzer=standard, attr='get_name_fa')
    # name_fa2 = fields.TextField(analyzer=ngram, attr='get_name_fa')
    # name = fields.TextField(attr='get_name_fa')
    parent = fields.TextField(attr='get_parent_fa')
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
        fields = []


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
