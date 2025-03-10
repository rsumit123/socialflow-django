from django.contrib import admin
from .models import Category, SubCategory, Lesson, LessonProgress, UserContentAccess

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'order')
    list_display_links = ('id', 'name')
    search_fields = ('name',)
    ordering = ('order',)

class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'order')
    list_display_links = ('id', 'name')
    list_filter = ('category',)
    search_fields = ('name',)
    ordering = ('category', 'order')
    readonly_fields = ('id',)  # This makes the ID visible in the detail view

class LessonAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'subcategory', 'order')
    list_display_links = ('id', 'title')
    list_filter = ('subcategory__category', 'subcategory')
    search_fields = ('title',)
    ordering = ('subcategory', 'order')
    readonly_fields = ('id',)

class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'lesson', 'completed', 'score', 'attempted_at')
    list_filter = ('completed', 'lesson__subcategory__category', 'lesson__subcategory')
    search_fields = ('user__email', 'lesson__title')
    readonly_fields = ('id',)

class UserContentAccessAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'content_type', 'object_id', 'allowed')
    list_filter = ('allowed', 'content_type')
    search_fields = ('user__email',)
    readonly_fields = ('id',)

admin.site.register(Category, CategoryAdmin)
admin.site.register(SubCategory, SubCategoryAdmin)
admin.site.register(Lesson, LessonAdmin)
admin.site.register(LessonProgress, LessonProgressAdmin)
admin.site.register(UserContentAccess, UserContentAccessAdmin)

