# documents.py

from django_elasticsearch_dsl import Document, fields
from elasticsearch_dsl import analyzer, tokenizer
from django_elasticsearch_dsl.registries import registry
from .models import Product

ngram = analyzer('ngram', tokenizer=tokenizer('trigram', 'nGram', min_gram=3, max_gram=3), filter=["lowercase"])


@registry.register_document
class ProductDocument(Document):

    name_fa = fields.TextField(analyzer=ngram, attr='get_name_fa')
    name_en = fields.TextField(attr='get_name_en')
    name_ar = fields.TextField(attr='get_name_ar')

    category_fa = fields.TextField(attr='get_category_fa')
    category_en = fields.TextField(attr='get_category_en')
    category_ar = fields.TextField(attr='get_category_ar')

    thumbnail = fields.TextField(attr='get_thumbnail')

    class Index:
        # Name of the Elasticsearch index
        name = 'products'
        # See Elasticsearch Indices API reference for available settings
        settings = {'number_of_shards': 1,
                    'number_of_replicas': 0}


    class Django:
        model = Product  # The model associated with this Document

        # The fields of the model you want to be indexed in Elasticsearch
        fields = []
