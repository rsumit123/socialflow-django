from django.contrib import admin
from .models import Category, SubCategory, Lesson, LessonProgress, UserContentAccess

admin.site.register(Category)
admin.site.register(SubCategory)
admin.site.register(Lesson)
admin.site.register(LessonProgress)
admin.site.register(UserContentAccess)

