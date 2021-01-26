from django.db.models.signals import post_save
from django.dispatch import receiver

from server.models import Invoice, Storage
from server.utils import add_one_off_job


@receiver(post_save, sender=Invoice, dispatch_uid="invoice_job_handler")
def invoice_job_maker(sender, instance, **kwargs):
    if kwargs.get('created', False):
        task_name = f'{instance.id}: cancel reservation'
        kwargs = {"invoice_id": instance.id, "task_name": task_name}
        if instance.final_price:
            instance.sync_task = add_one_off_job(name=task_name, kwargs=kwargs, interval=30,
                                                 task='server.tasks.cancel_reservation')


@receiver(post_save, sender=Storage, dispatch_uid="inventory_alert_handler")
def inventory_alert(sender, instance, **kwargs):
    if kwargs.get('update_fields', None) and 'sold_count' in kwargs.get('update_fields', []):
        if instance.special_products.all() and instance.available_count_for_sale == 0:
            subject = "هشدار اتمام موجودی محصول ویژه"
            message = f"موجودی {instance.title['fa']} به اتمام رسیده است"
            task_name = f'{instance.id} inventory_alert'
            kwargs = {"to": instance.product.box.owner.email, "subject": subject, 'message': message}
            add_one_off_job(name=task_name, kwargs=kwargs, interval=0, task='server.tasks.email_task')

        elif instance.available_count_for_sale <= instance.min_count_alert:
            subject = "هشدار اتمام موجودی انبار"
            message = f"نام محصول: {instance.title['fa']}\nتعداد باقی مانده: {instance.available_count_for_sale}"
            task_name = f'{instance.id} inventory_alert'
            kwargs = {"to": instance.product.box.owner.email, "subject": subject, 'message': message}
            add_one_off_job(name=task_name, kwargs=kwargs, interval=0, task='server.tasks.email_task')
