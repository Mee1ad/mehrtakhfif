from django.test import TestCase
from django.test import Client
from server.models import *


# models test
class WhateverTest(TestCase):

    def create_whatever(self, name="only a test", body="yes, this is only a test"):
        return Box.objects.create(title=title, body=body, created_at=timezone.now())

    def test_whatever_creation(self):
        w = self.create_whatever()
        self.assertTrue(isinstance(w, Whatever))
        self.assertEqual(w.__unicode__(), w.title)


# class SimpleTest(TestCase):
#     def setUp(self):
#         self.c = Client()
#         fixtures = ['db']
#
#     def test(self):
#         res = self.c.get('/user_comments', {'name': 'fred', 'age': 7})
#         # Check that the response is 200 OK.
#         self.assertEqual(res.status_code, 200)
#
#         # Check that the rendered context contains 5 customers.
#         self.assertEqual(len(res.context['customers']), 5)
