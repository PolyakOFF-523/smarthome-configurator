from django.contrib import admin
from .models import (
    Ecosystem, Category, Component, ComponentImage, Room, UserProject, Build, BuildComponent, Tag  
)

@admin.register(Ecosystem)
class EcosystemAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'website')
    list_editable = ('order',)
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')
    list_filter = ('order',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'order')
    list_editable = ('order',)
    list_filter = ('parent',)
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('parent')

@admin.register(Component)
class ComponentAdmin(admin.ModelAdmin):
    list_display = ('name', 'ecosystem', 'category', 'price', 'in_stock', 'is_popular')
    list_editable = ('in_stock', 'is_popular')
    list_filter = ('ecosystem', 'category', 'protocol', 'power_source', 'in_stock')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ('compatible_with',)
    filter_horizontal = ('compatible_with', 'tags')  # Добавьте 'tags'
    fieldsets = (
        ('Основное', {
            'fields': ('name', 'slug', 'ecosystem', 'category', 'image', 'description')
        }),
        ('Характеристики', {
            'fields': ('protocol', 'power_source', 'range_meters', 'power_consumption_watts', 'price')
        }),
        ('Совместимость', {
            'fields': ('requires_hub', 'compatible_with')
        }),
        ('Статус', {
            'fields': ('in_stock', 'is_popular', 'is_new')
        }),
        ('Дополнительно', {
            'fields': ('specifications',),
            'classes': ('collapse',)
        }),
    )

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

@admin.register(ComponentImage)
class ComponentImageAdmin(admin.ModelAdmin):
    list_display = ('component', 'is_main', 'order')
    list_editable = ('is_main', 'order')
    list_filter = ('component',)

# Регистрация моделей сборок
@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'area')
    search_fields = ('name',)

@admin.register(UserProject)
class UserProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'total_area', 'created_at')
    readonly_fields = ('created_at',)

@admin.register(Build)
class BuildAdmin(admin.ModelAdmin):
    list_display = ('name', 'price_segment', 'total_price', 'total_power', 'status', 'is_selected')
    list_filter = ('price_segment', 'status')
    search_fields = ('name',)

@admin.register(BuildComponent)
class BuildComponentAdmin(admin.ModelAdmin):
    list_display = ('build', 'component', 'room', 'quantity')
    list_filter = ('build', 'room')