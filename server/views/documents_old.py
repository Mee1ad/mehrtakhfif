from django_elasticsearch_dsl import Document
from elasticsearch_dsl import Index
from django_elasticsearch_dsl.registries import registry
from server.models import Product


products = Index('products')
products.settings(
    number_of_shards=1,
    number_of_replicas=0
)


@registry.register_document
@products.document
class ProductDocument(Document):

    # name = fields.ObjectField(properties={
    #     'persian': fields.TextField(),
    #     'english': fields.TextField(),
    #     'arabic': fields.TextField(),
    # })

    class Index:
        # Name of the Elasticsearch index
        name = 'products'
        # See Elasticsearch Indices API reference for available settings
        settings = {'number_of_shards': 1,
                    'number_of_replicas': 0}

    class Django:
        model = Product
        fields = ['type', ]

        # Ignore auto updating of Elasticsearch when a model is saved
        # or deleted:
        # ignore_signals = True

        # Don't perform an index refresh after every update (overrides global setting):
        # auto_refresh = False

        # Paginate the django queryset used to populate the index with the specified size
        # (by default it uses the database driver's default setting)
        # queryset_pagination = 5000
