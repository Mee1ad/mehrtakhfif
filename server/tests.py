# from datetime import timedelta
# from django.utils.timezone import timedelta
from datetime import timedelta, datetime
import django_rq
import pysnooper
from django.http import JsonResponse
from django.views import View


#  python manage.py rqscheduler
#  python manage.py rqworker high

def add(a, b):
    return a + b


class Add(View):
    @pysnooper.snoop()
    def get(self, request):
        # scheduler = django_rq.get_scheduler('basket_sync')
        scheduler = django_rq.get_scheduler()
        job = scheduler.enqueue_in(timedelta(minutes=1), add, 2, 3)
        # job = scheduler.enqueue_at(datetime(2019, 12, 18, 16, 30), add, 2, 3)
        added = False
        if job in scheduler:
            added = True
        print(job)
        return JsonResponse({'added': added, 'job': job.id})


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
        scheduler = django_rq.get_scheduler('basket_sync')
        scheduler.cancel(job)
        return JsonResponse({'message': 'remove successfully'})
