# Generated by Django 4.0.8 on 2024-11-17 17:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0007_assignment_submission'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='submission',
            name='assignment',
        ),
        migrations.RemoveField(
            model_name='submission',
            name='student',
        ),
        migrations.DeleteModel(
            name='Assignment',
        ),
        migrations.DeleteModel(
            name='Submission',
        ),
    ]
