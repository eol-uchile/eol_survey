# -*- coding: utf-8 -*-

# Installed packages (via pip)
from django.contrib import admin

# Internal project dependencies
from .models import Survey

# Register your models here.

admin.site.register(Survey)
