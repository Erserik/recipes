from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from shopping_app.models import ShoppingList

User = get_user_model()

@receiver(post_save, sender=User)
def create_shopping_list_for_user(sender, instance, created, **kwargs):
    if created:
        ShoppingList.objects.create(user=instance, title="Мой список")
