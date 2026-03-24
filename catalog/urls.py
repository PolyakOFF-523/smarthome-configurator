from django.urls import path
from . import views

urlpatterns = [
    # Главная
    path('', views.index, name='index'),
    
    # Подбор сборок
    path('start/', views.start_project, name='start_project'),
    path('builds/', views.build_selection, name='build_selection'),
    path('build/<int:build_id>/', views.build_detail, name='build_detail'),
    path('check-compatibility/<int:build_id>/<int:component_id>/<int:room_id>/', 
         views.check_compatibility, name='check_compatibility'),
    path('report/<int:build_id>/', views.final_report, name='final_report'),
    
    # Экосистемы (каталог)
    path('ecosystems/', views.ecosystem_list, name='ecosystem_list'),
    path('ecosystem/<slug:slug>/', views.ecosystem_detail, name='ecosystem_detail'),
    
    # Категории и подкатегории
    path('catalog/<slug:slug>/', views.category_detail, name='category_detail'),
    path('catalog/<slug:category_slug>/<slug:subcategory_slug>/', 
         views.subcategory_detail, name='subcategory_detail'),
    
    # Товары
    path('product/<slug:slug>/', views.component_detail, name='component_detail'),
    
    # Поиск
    path('search/', views.search, name='search'),

    # Модерация
    path('moderation/', views.moderation_queue, name='moderation_queue'),
    path('moderation/<int:build_id>/', views.moderation_detail, name='moderation_detail'),
    path('moderation/<int:build_id>/approve/', views.moderation_approve, name='moderation_approve'),
    path('moderation/<int:build_id>/reject/', views.moderation_reject, name='moderation_reject'),
    path('moderation/<int:build_id>/delete/', views.moderation_delete, name='moderation_delete'),  # Добавить
    path('build/<int:build_id>/submit/', views.submit_to_moderation, name='submit_to_moderation'),

    # Управление сборками
    path('my-builds/', views.my_builds, name='my_builds'),
    path('build/<int:build_id>/delete/', views.delete_build, name='delete_build'),
    path('builds/bulk-delete/', views.bulk_delete_builds, name='bulk_delete_builds'),
    path('build/<int:build_id>/select/', views.select_build, name='select_build'),
    path('build/<int:build_id>/remove/<int:component_id>/', views.remove_component, name='remove_component'),
    path('build/<int:build_id>/add/', views.add_component_page, name='add_component_page'),
    path('build/<int:build_id>/add/<int:component_id>/', views.add_component_to_build, name='add_component_to_build'),
    path('new-project/', views.new_project, name='new_project'),
    path('public-builds/', views.public_builds, name='public_builds'),
    path('public-build/<int:build_id>/', views.public_build_detail, name='public_build_detail'),
    path('like-build/<int:build_id>/', views.like_build, name='like_build'),
    path('build/<int:build_id>/rename/', views.rename_build, name='rename_build'),

    # Профиль
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/change-password/', views.change_password, name='change_password'),
]