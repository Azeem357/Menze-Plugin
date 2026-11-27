from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('suggestions', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='aisuggestion',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='aisuggestion',
            name='rule_key',
            field=models.CharField(
                blank=True,
                max_length=100,
                null=True,
                unique=True,
            ),
        ),
        migrations.AlterModelOptions(
            name='aisuggestion',
            options={
                'db_table': 'ai_suggestions',
                'ordering': ['-is_active', 'is_acted_on', '-created_at'],
            },
        ),
    ]
