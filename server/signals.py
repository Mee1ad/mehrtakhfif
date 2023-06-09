from django.core.cache import cache
from django.db.models.signals import post_save
from django.dispatch import receiver

from mehr_takhfif.settings import color_feature_id
from server.models import Invoice, Storage, FeatureValue, Category, Box, User, Product
from server.utils import add_one_off_job, get_categories


@receiver(post_save, sender=Invoice, dispatch_uid="invoice_job_handler")
def invoice_job_maker(sender, instance, **kwargs):
    if kwargs.get('created', False):
        task_name = f'{instance.id}: cancel reservation'
        kwargs = {"invoice_id": instance.id, "task_name": task_name}
        if instance.final_price:
            instance.sync_task = add_one_off_job(name=task_name, kwargs=kwargs, interval=30,
                                                 task='server.tasks.cancel_reservation')
            instance.save()


@receiver(post_save, sender=Storage, dispatch_uid="inventory_alert_handler")
def inventory_alert(sender, instance, **kwargs):
    if kwargs.get('update_fields', None) and 'sold_count' in kwargs.get('update_fields', []):
        owner = instance.product.category.owner
        if instance.special_products.all() and instance.available_count_for_sale == 0:
            subject = "هشدار اتمام موجودی محصول ویژه"
            message = f"موجودی {instance.title['fa']} به اتمام رسیده است"
            task_name = f'{instance.id} inventory_alert'
            if owner.email_alert:
                kwargs = {"to": owner.email, "subject": subject, 'message': message}
                add_one_off_job(name=task_name, kwargs=kwargs, interval=0, task='server.tasks.email_task')
            if owner.pm_alert:
                kwargs = {"tg_id": owner.email, 'message': subject + '\n\n' + message}
                add_one_off_job(name=task_name, kwargs=kwargs, interval=0, task='server.tasks.pm_task')

        elif instance.available_count_for_sale <= instance.min_count_alert:
            subject = "هشدار اتمام موجودی انبار"
            message = f"نام محصول: {instance.title['fa']}\nتعداد باقی مانده: {instance.available_count_for_sale}"
            task_name = f'{instance.id} inventory_alert'
            kwargs = {"to": owner.email, "subject": subject, 'message': message}
            add_one_off_job(name=task_name, kwargs=kwargs, interval=0, task='server.tasks.email_task')


@receiver(post_save, sender=FeatureValue, dispatch_uid="update_colors_in_cache")
def update_colors_in_cache(sender, instance, **kwargs):
    if instance.feature_id == color_feature_id:
        caches = cache.keys('color*')
        cache.delete_many(caches)


@receiver(post_save, sender=Category, dispatch_uid="update_categories_in_cache")
def update_categories_in_cache(sender, instance, **kwargs):
    cache.set('categories', get_categories(), 3000000)


@receiver(post_save, sender=Storage, dispatch_uid="manage_product_availability")
def manage_product_availability(sender, instance, **kwargs):
    instance.product.assign_default_value()


