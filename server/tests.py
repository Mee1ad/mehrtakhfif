from datetime import timedelta

import django_rq
import pysnooper
from django.http import JsonResponse
from django.views import View


def add(a, b):
    return a + b


class Add(View):
    @pysnooper.snoop()
    def get(self, request):
        scheduler = django_rq.get_scheduler('basket_sync')
        job = scheduler.enqueue_at(timedelta(minutes=30), add, 2, 3)
        added = False
        if job in scheduler:
            added = True
        return JsonResponse({'added': added, 'job': job})


class Get(View):
    @pysnooper.snoop()
    def get(self, request):
        worker = django_rq.get_worker()
        scheduler = django_rq.get_scheduler('basket_sync')
        jobs = scheduler.get_jobs(with_times=True)
        return JsonResponse({'worker': worker, 'jobs': jobs})


class Delete(View):
    @pysnooper.snoop()
    def get(self, request, job):
        scheduler = django_rq.get_scheduler('basket_sync')
        scheduler.cancel(job)
        return JsonResponse({'message': 'remove successfully'})
