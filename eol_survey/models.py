# -*- coding: utf-8 -*-


from django.db import models

# Create your models here.
class Survey(models.Model):
    header = models.TextField()
    description = models.TextField()
    content = models.TextField()
