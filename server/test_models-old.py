import factory

from . import models


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.User

    username = 'admin'


# class BaseFactory(factory.django.DjangoModelFactory):
#     created_by_id = factory.SelfAttribute('created_by.id')
#     updated_by_id = factory.SelfAttribute('updated_by.id')
#
#     class Meta:
#         exclude = ['created_by', 'created_by']
#         abstract = True


class CharityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Charity

    name = 'khorshid'
    deposit_id = 1
    created_by = factory.SubFactory(UserFactory)
    updated_by = factory.SubFactory(UserFactory)


class MenuFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.User

    first_name = 'John'
    last_name = 'Doe'
    admin = False

    type = 'home'
    name = 'John'
    media = None
    url = 'google.com'
    parent = None
    priority = 0
    box = None
