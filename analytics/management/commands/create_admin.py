from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        User = get_user_model()
        username = 'admin'
        password = 'admin123'
        email = 'admin@menz.com'
        
        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username, email, password)
            self.stdout.write(f'Superuser created: {username}')
        else:
            self.stdout.write('Superuser already exists')