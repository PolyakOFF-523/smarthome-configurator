from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.http import JsonResponse
from .models import Ecosystem, Category, Component
from .models import UserProject, Room, Build, BuildComponent
from .build_generator import BuildGenerator
from .compatibility import CompatibilityChecker

# ================ КАТАЛОГ ================

def index(request):
    """Главная страница"""
    popular_components = Component.objects.filter(is_popular=True, in_stock=True)[:8]
    new_components = Component.objects.filter(is_new=True, in_stock=True)[:8]
    ecosystems = Ecosystem.objects.all()[:6]
    
    context = {
        'popular_components': popular_components,
        'new_components': new_components,
        'ecosystems': ecosystems,
    }
    return render(request, 'catalog/index.html', context)

def ecosystem_list(request):
    ecosystems = Ecosystem.objects.all()
    return render(request, 'catalog/ecosystem_list.html', {'ecosystems': ecosystems})

def ecosystem_detail(request, slug):
    ecosystem = get_object_or_404(Ecosystem, slug=slug)
    components = Component.objects.filter(ecosystem=ecosystem, in_stock=True)
    categories = Category.objects.filter(components__in=components).distinct()
    context = {
        'ecosystem': ecosystem,
        'components': components,
        'categories': categories,
    }
    return render(request, 'catalog/ecosystem_detail.html', context)

def category_detail(request, slug):
    """Страница категории устройств"""
    category = get_object_or_404(Category, slug=slug, parent__isnull=True)
    subcategories = category.children.all()
    components = Component.objects.filter(category=category, in_stock=True)
    context = {
        'category': category,
        'subcategories': subcategories,
        'components': components,
    }
    return render(request, 'catalog/category_detail.html', context)

def subcategory_detail(request, category_slug, subcategory_slug):
    parent = get_object_or_404(Category, slug=category_slug)
    subcategory = get_object_or_404(Category, slug=subcategory_slug, parent=parent)
    components = Component.objects.filter(category=subcategory, in_stock=True)
    context = {
        'category': subcategory,
        'parent_category': parent,
        'components': components,
    }
    return render(request, 'catalog/subcategory_detail.html', context)

def component_detail(request, slug):
    component = get_object_or_404(Component, slug=slug, in_stock=True)
    similar_components = Component.objects.filter(
        category=component.category, 
        in_stock=True
    ).exclude(id=component.id)[:4]
    compatible = component.compatible_with.filter(in_stock=True)[:6]
    context = {
        'component': component,
        'similar_components': similar_components,
        'compatible': compatible,
    }
    return render(request, 'catalog/component_detail.html', context)

def search(request):
    query = request.GET.get('q', '')
    if query:
        components = Component.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(ecosystem__name__icontains=query)
        ).filter(in_stock=True)
    else:
        components = Component.objects.none()
    context = {
        'query': query,
        'components': components,
    }
    return render(request, 'catalog/search.html', context)


# ================ ПОДБОР СБОРОК ================

def start_project(request):
    """Шаг 1: Ввод параметров квартиры"""
    saved_rooms = request.session.get('saved_rooms', [])
    
    if request.method == 'GET':
        if request.session.get('project_id'):
            context = {'saved_rooms': saved_rooms}
        else:
            context = {'saved_rooms': []}
        return render(request, 'catalog/project_form.html', context)
    
    if request.method == 'POST':
        room_types = request.POST.getlist('room_type[]')
        room_areas = request.POST.getlist('room_area[]')
        
        if not room_types or not room_areas or not room_types[0]:
            messages.error(request, 'Добавьте хотя бы одну комнату')
            return render(request, 'catalog/project_form.html', {'saved_rooms': []})
        
        try:
            rooms_data = []
            for i in range(len(room_types)):
                if room_types[i] and room_areas[i]:
                    rooms_data.append({
                        'type': room_types[i],
                        'area': float(room_areas[i])
                    })
            request.session['saved_rooms'] = rooms_data
            
            old_project_id = request.session.get('project_id')
            if old_project_id:
                try:
                    old_project = UserProject.objects.get(id=old_project_id)
                    old_project.delete()
                except UserProject.DoesNotExist:
                    pass
            
            total_area = sum(float(area) for area in room_areas if area)
            project = UserProject.objects.create(total_area=total_area)
            
            for i in range(len(room_types)):
                if room_types[i] and room_areas[i]:
                    room = Room.objects.create(
                        name=room_types[i],
                        area=float(room_areas[i])
                    )
                    project.rooms.add(room)
            
            request.session['project_id'] = project.id
            
            generator = BuildGenerator(project)
            builds = generator.generate_all_builds()
            
            messages.success(request, '✅ Новые сборки созданы! Выберите одну для настройки.')
            return redirect('build_selection')
            
        except ValueError as e:
            messages.error(request, 'Пожалуйста, введите корректные числа')
            return render(request, 'catalog/project_form.html', {'saved_rooms': []})

def build_selection(request):
    project_id = request.session.get('project_id')
    if not project_id:
        return redirect('start_project')
    
    project = get_object_or_404(UserProject, id=project_id)
    generator = BuildGenerator(project)
    builds = generator.generate_all_builds()
    
    # Добавляем даты создания для каждой сборки
    for key in builds:
        if builds[key] and builds[key].created_at:
            builds[key].created_at_formatted = builds[key].created_at.strftime('%d.%m.%Y %H:%M')
    
    context = {
        'project': project,
        'builds': builds,
    }
    return render(request, 'catalog/build_selection.html', context)

def build_detail(request, build_id):
    build = get_object_or_404(Build, id=build_id)
    
    if build.status in ['DRAFT', 'VERIFIED', 'NEEDS_FIX', 'REJECTED']:
        build.status = 'CONFIGURING'
        build.save()
    
    project_id = request.session.get('project_id')
    project = get_object_or_404(UserProject, id=project_id) if project_id else None
    
    available_components = Component.objects.all()[:10]
    
    context = {
        'build': build,
        'project': project,
        'available_components': available_components,
    }
    return render(request, 'catalog/build_detail.html', context)

def check_compatibility(request, build_id, component_id, room_id):
    build = get_object_or_404(Build, id=build_id)
    component = get_object_or_404(Component, id=component_id)
    
    if room_id == 0:
        room_id = request.POST.get('room_id')
    
    if not room_id:
        messages.error(request, '❌ Не выбрана комната')
        return redirect('add_component_to_build', build_id=build.id, component_id=component.id)
    
    try:
        room = Room.objects.get(id=room_id)
    except Room.DoesNotExist:
        messages.error(request, '❌ Выбранная комната не найдена')
        return redirect('add_component_to_build', build_id=build.id, component_id=component.id)
    
    if build.status == 'NEEDS_FIX':
        build.status = 'CONFIGURING'
        build.save()
    
    project_id = request.session.get('project_id')
    project = get_object_or_404(UserProject, id=project_id)
    
    checker = CompatibilityChecker(project)
    
    is_compatible, issues, alternative = checker.check_all(
        build, component, room, 
        distance_from_hub=request.POST.get('distance', 5)
    )
    
    if is_compatible:
        BuildComponent.objects.create(
            build=build,
            component=component,
            room=room,
            quantity=1
        )
        
        generator = BuildGenerator(project)
        generator.calculate_totals(build)
        
        messages.success(request, f'✅ {component.name} успешно добавлен в сборку')
        return redirect('build_detail', build_id=build.id)
    else:
        build.status = 'NEEDS_FIX'
        build.save()
        
        context = {
            'build': build,
            'component': component,
            'room': room,
            'issues': issues,
            'alternative': alternative,
        }
        return render(request, 'catalog/incompatible.html', context)

def rename_build(request, build_id):
    """Переименование сборки"""
    if request.method == 'POST':
        build = get_object_or_404(Build, id=build_id)
        new_name = request.POST.get('name', '').strip()
        
        if new_name:
            old_name = build.name
            build.name = new_name
            build.save()
            messages.success(request, f'✅ Сборка переименована: "{old_name}" → "{new_name}"')
        else:
            messages.error(request, '❌ Имя не может быть пустым')
            
        return redirect('build_detail', build_id=build.id)
    
    return redirect('build_detail', build_id=build.id)

def final_report(request, build_id):
    build = get_object_or_404(Build, id=build_id)
    project_id = request.session.get('project_id')
    project = get_object_or_404(UserProject, id=project_id) if project_id else None
    
    if not project:
        return redirect('start_project')
    
    from .compatibility import analyze_placement
    placement_advice = analyze_placement(build, project)
    
    context = {
        'build': build,
        'project': project,
        'placement_advice': placement_advice,
        'total_price': build.total_price,
        'total_power': build.total_power,
    }
    return render(request, 'catalog/final_report.html', context)


# ================ МОДЕРАЦИЯ ================

@staff_member_required
def moderation_queue(request):
    builds_pending = Build.objects.filter(status='PENDING_MODERATION').order_by('-id')
    builds_published = Build.objects.filter(status='PUBLISHED').order_by('-id')[:10]
    builds_rejected = Build.objects.filter(status='REJECTED').order_by('-id')[:10]
    
    context = {
        'builds_pending': builds_pending,
        'builds_published': builds_published,
        'builds_rejected': builds_rejected,
    }
    return render(request, 'catalog/moderation/queue.html', context)

@staff_member_required
def moderation_approve(request, build_id):
    build = get_object_or_404(Build, id=build_id)
    if build.status == 'PENDING_MODERATION':
        build.status = 'PUBLISHED'
        build.save()
        messages.success(request, f'Сборка "{build.name}" опубликована')
    else:
        messages.error(request, 'Сборка не находится на модерации')
    return redirect('moderation_queue')

@staff_member_required
def moderation_reject(request, build_id):
    build = get_object_or_404(Build, id=build_id)
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        if build.status == 'PENDING_MODERATION':
            build.status = 'REJECTED'
            build.save()
            messages.success(request, f'Сборка "{build.name}" отклонена')
        else:
            messages.error(request, 'Сборка не находится на модерации')
        return redirect('moderation_queue')
    
    context = {'build': build}
    return render(request, 'catalog/moderation/reject.html', context)

@staff_member_required
def moderation_detail(request, build_id):
    build = get_object_or_404(Build, id=build_id)
    project_id = request.session.get('project_id')
    project = get_object_or_404(UserProject, id=project_id) if project_id else None
    
    context = {
        'build': build,
        'project': project,
        'moderation_view': True,
    }
    return render(request, 'catalog/moderation/detail.html', context)

def submit_to_moderation(request, build_id):
    build = get_object_or_404(Build, id=build_id)
    
    if build.status in ['VERIFIED', 'SAVED', 'CONFIGURING']:
        build.status = 'PENDING_MODERATION'
        build.save()
        messages.success(request, 'Сборка отправлена на модерацию')
    else:
        messages.error(request, 'Нельзя отправить эту сборку на модерацию')
    
    return redirect('build_detail', build_id=build.id)


# ================ УПРАВЛЕНИЕ СБОРКАМИ ================

def my_builds(request):
    selected_builds = Build.objects.filter(is_selected=True).order_by('-id')
    active_builds = Build.objects.filter(
        status__in=['CONFIGURING', 'NEEDS_FIX', 'PENDING_MODERATION', 'REJECTED']
    ).order_by('-id')
    all_builds = (selected_builds | active_builds).distinct()
    
    context = {'all_builds': all_builds}
    return render(request, 'catalog/my_builds.html', context)

def delete_build(request, build_id):
    build = get_object_or_404(Build, id=build_id)
    
    if request.method == 'POST':
        build_name = build.name
        build.delete()
        messages.success(request, f'Сборка "{build_name}" успешно удалена')
        return redirect('my_builds')
    
    context = {'build': build}
    return render(request, 'catalog/delete_build.html', context)

def bulk_delete_builds(request):
    if request.method == 'POST':
        build_ids = request.POST.getlist('build_ids')
        if not build_ids:
            messages.error(request, 'Не выбрано ни одной сборки для удаления')
            return redirect('my_builds')
        
        builds = Build.objects.filter(id__in=build_ids)
        count = builds.count()
        builds.delete()
        messages.success(request, f'✅ Успешно удалено {count} сборок')
        return redirect('my_builds')
    
    return redirect('my_builds')

def select_build(request, build_id):
    build = get_object_or_404(Build, id=build_id)
    project_id = request.session.get('project_id')
    
    print(f"select_build: build_id={build_id}, build.project_id={build.project_id}, session project_id={project_id}")
    
    if not project_id:
        messages.error(request, '❌ Сессия истекла. Начните сначала.')
        return redirect('start_project')
    
    if build.project and build.project.id != project_id:
        messages.error(request, f'Ошибка: сборка не принадлежит текущему проекту')
        return redirect('build_selection')
    
    Build.objects.filter(project_id=project_id).update(is_selected=False)
    
    build.is_selected = True
    build.status = 'CONFIGURING'
    build.save()
    
    messages.success(request, f'✅ Вы выбрали сборку "{build.name}". Теперь её можно настраивать!')
    return redirect('build_detail', build_id=build.id)

def remove_component(request, build_id, component_id):
    build = get_object_or_404(Build, id=build_id)
    component = get_object_or_404(Component, id=component_id)
    
    build_component = BuildComponent.objects.filter(
        build=build, 
        component=component
    ).first()
    
    if build_component:
        build_component.delete()
        
        project_id = request.session.get('project_id')
        project = get_object_or_404(UserProject, id=project_id) if project_id else None
        if project:
            generator = BuildGenerator(project)
            generator.calculate_totals(build)
        
        messages.success(request, f'✅ Устройство "{component.name}" удалено из сборки')
    else:
        messages.error(request, '❌ Устройство не найдено в сборке')
    
    return redirect('build_detail', build_id=build.id)

def add_component_page(request, build_id):
    build = get_object_or_404(Build, id=build_id)
    project_id = request.session.get('project_id')
    project = get_object_or_404(UserProject, id=project_id) if project_id else None
    
    components = Component.objects.filter(in_stock=True).order_by('category', 'name')
    categories = Category.objects.filter(components__in=components).distinct()
    
    categories_with_components = []
    for category in categories:
        categories_with_components.append({
            'category': category,
            'components': components.filter(category=category)
        })
    
    context = {
        'build': build,
        'project': project,
        'categories_with_components': categories_with_components,
        'categories': categories,
    }
    return render(request, 'catalog/add_component.html', context)

def add_component_to_build(request, build_id, component_id):
    build = get_object_or_404(Build, id=build_id)
    component = get_object_or_404(Component, id=component_id)
    project_id = request.session.get('project_id')
    project = get_object_or_404(UserProject, id=project_id) if project_id else None
    
    context = {
        'build': build,
        'component': component,
        'project': project,
        'rooms': project.rooms.all() if project else [],
    }
    return render(request, 'catalog/add_component_form.html', context)

def new_project(request):
    if 'project_id' in request.session:
        del request.session['project_id']
    if 'saved_rooms' in request.session:
        del request.session['saved_rooms']
    
    messages.info(request, '🆕 Начинаем новый подбор сборки')
    return redirect('start_project')

def public_builds(request):
    """Страница со всеми опубликованными сборками"""
    builds = Build.objects.filter(status='PUBLISHED').order_by('-created_at')
    
    # Фильтры
    ecosystem = request.GET.get('ecosystem')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    
    if ecosystem:
        builds = builds.filter(components__ecosystem__slug=ecosystem).distinct()
    if min_price:
        builds = builds.filter(total_price__gte=min_price)
    if max_price:
        builds = builds.filter(total_price__lte=max_price)
    
    # Все экосистемы для фильтра
    ecosystems = Ecosystem.objects.all()
    
    context = {
        'builds': builds,
        'ecosystems': ecosystems,
    }
    return render(request, 'catalog/public_builds.html', context)

def public_build_detail(request, build_id):
    """Публичный просмотр сборки (без редактирования)"""
    build = get_object_or_404(Build, id=build_id, status='PUBLISHED')
    
    # Увеличиваем счётчик просмотров
    build.views_count += 1
    build.save(update_fields=['views_count'])
    
    context = {
        'build': build,
        'is_public_view': True,  # флаг для шаблона, чтобы скрыть кнопки редактирования
    }
    return render(request, 'catalog/public_build_detail.html', context)

def like_build(request, build_id):
    """Лайк сборки (AJAX)"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Требуется авторизация'}, status=403)
    
    build = get_object_or_404(Build, id=build_id, status='PUBLISHED')
    
    if request.user in build.likes.all():
        build.likes.remove(request.user)
        liked = False
    else:
        build.likes.add(request.user)
        liked = True
    
    return JsonResponse({
        'liked': liked,
        'likes_count': build.likes.count()
    })
