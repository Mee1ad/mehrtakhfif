# from django.utils.timezone import timedelta
from datetime import timedelta, datetime
import pysnooper
from django.http import JsonResponse
from django.views import View
from django_celery_beat.models import PeriodicTask, IntervalSchedule
import json


def add(a, b):
    return a + b


class Add(View):
    @pysnooper.snoop()
    def get(self, request):
        t = IntervalSchedule.objects.get(pk=1)
        schedule, created = IntervalSchedule.objects.get_or_create(every=5, period=IntervalSchedule.SECONDS)
        PeriodicTask.objects.create(interval=schedule, name='Importing contacts', task='server.tasks.hello',
                                    args=json.dumps(['arg1', 'arg2']), one_off=True)
        return JsonResponse({})


class Update(View):
    @pysnooper.snoop()
    def get(self, request, id):
        PeriodicTask.objects.filter(pk=id).update()
        return JsonResponse({'worker': worker.name, 'jobs': job_list})


class Get(View):
    @pysnooper.snoop()
    def get(self, request):
        worker = django_rq.get_worker()
        scheduler = django_rq.get_scheduler('basket_sync')
        jobs = scheduler.get_jobs(with_times=True)
        job_list = []
        for job in jobs:
            job = {'id': job[0].id, 'time': job[1]}
            job_list.append(job)
        return JsonResponse({'worker': worker.name, 'jobs': job_list})


class Delete(View):
    @pysnooper.snoop()
    def get(self, request, job):
        task = None
        task.enabled = False
        task.save()
        return JsonResponse({'message': 'remove successfully'})
