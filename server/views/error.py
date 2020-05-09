from django.http import HttpResponseNotFound


def not_found(request, exception):
    return HttpResponseNotFound()

