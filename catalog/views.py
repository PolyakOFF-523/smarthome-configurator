from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.http import JsonResponse
from .models import Ecosystem, Category, Component, UserProject, Room, Build, BuildComponent, Comment, Guide, GuideImage
from .build_generator import BuildGenerator
from .compatibility import CompatibilityChecker
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.utils.text import slugify

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
                    # Удаляем все сборки старого проекта
                    Build.objects.filter(project=old_project).delete()
                    old_project.delete()
                except UserProject.DoesNotExist:
                    pass
            
            total_area = sum(float(area) for area in room_areas if area)
            
            project = UserProject.objects.create(
                total_area=total_area,
                user=request.user if request.user.is_authenticated else None
            )
            
            for i in range(len(room_types)):
                if room_types[i] and room_areas[i]:
                    room = Room.objects.create(
                        name=room_types[i],
                        area=float(room_areas[i])
                    )
                    project.rooms.add(room)
            
            request.session['project_id'] = project.id
            
            # Генерируем сборки только один раз
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
    
    # Получаем существующие сборки
    builds = {
        'economy': Build.objects.filter(project=project, price_segment='ECONOMY', name__icontains='Эконом').first(),
        'standard': Build.objects.filter(project=project, price_segment='STANDARD', name__icontains='Стандарт').first(),
        'premium': Build.objects.filter(project=project, price_segment='PREMIUM', name__icontains='Премиум').first(),
        'custom': Build.objects.filter(project=project, name__icontains='Своя').first(),
    }
    
    # Если какая-то сборка не найдена, создаём её
    generator = BuildGenerator(project)
    
    if not builds['economy']:
        builds['economy'] = generator.generate_build('🌱 Эконом', 'ECONOMY', max_price=5000)
    if not builds['standard']:
        builds['standard'] = generator.generate_build('⭐ Стандарт', 'STANDARD', max_price=15000)
    if not builds['premium']:
        builds['premium'] = generator.generate_build('👑 Премиум', 'PREMIUM', max_price=50000)
    if not builds['custom']:
        builds['custom'] = Build.objects.create(
            name="🔧 Своя сборка", 
            price_segment='ECONOMY', 
            status='DRAFT',
            project=project,
            user=project.user if project.user else None
        )
    
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
    
    # Проверка доступа
    if request.user.is_authenticated:
        # Авторизованный пользователь может редактировать только свои сборки
        if build.user and build.user != request.user:
            messages.error(request, 'У вас нет доступа к этой сборке')
            return redirect('public_builds')
    else:
        # Неавторизованный пользователь может просматривать:
        # 1. Публичные сборки
        # 2. Свои сборки из сессии (созданные в текущей сессии)
        project_id = request.session.get('project_id')
        
        # Проверяем, принадлежит ли сборка проекту из сессии
        if build.project and build.project.id == project_id:
            # Это сборка из текущей сессии, разрешаем
            pass
        elif build.status != 'PUBLISHED':
            # Не публичная и не принадлежит сессии - запрещаем
            messages.error(request, 'Доступ запрещён')
            return redirect('index')
    
    # Если сборка в статусе DRAFT, переводим в CONFIGURING
    if build.status in ['DRAFT', 'VERIFIED', 'NEEDS_FIX', 'REJECTED']:
        build.status = 'CONFIGURING'
        build.save()
    
    project_id = request.session.get('project_id')
    project = get_object_or_404(UserProject, id=project_id) if project_id else None
    
    context = {
        'build': build,
        'project': project,
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
    
    # Проверяем, есть ли проект в сессии
    project_id = request.session.get('project_id')
    
    # Если проект в сессии есть, используем его
    if project_id:
        project = get_object_or_404(UserProject, id=project_id)
    else:
        # Если нет проекта в сессии, но сборка привязана к пользователю
        if build.user == request.user:
            # Берём проект из сборки
            project = build.project
        else:
            # Если пользователь не владелец, показываем публичный отчёт без редактирования
            messages.error(request, 'Доступ запрещён')
            return redirect('public_build_detail', build_id=build.id)
    
    # Если проекта всё ещё нет, перенаправляем
    if not project:
        messages.error(request, 'Не найден проект для этой сборки')
        return redirect('my_builds')
    
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
    
    # Добавляем гайды
    guides_pending = Guide.objects.filter(status='PENDING').order_by('-created_at')
    guides_published = Guide.objects.filter(status='PUBLISHED').order_by('-created_at')[:10]
    guides_rejected = Guide.objects.filter(status='REJECTED').order_by('-created_at')[:10]
    
    context = {
        'builds_pending': builds_pending,
        'builds_published': builds_published,
        'builds_rejected': builds_rejected,
        'guides_pending': guides_pending,
        'guides_published': guides_published,
        'guides_rejected': guides_rejected,
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
    
    # Проверяем, что пользователь авторизован и является владельцем сборки
    if not request.user.is_authenticated:
        messages.error(request, 'Необходимо войти в систему для отправки на модерацию')
        return redirect('login')
    
    if build.user != request.user:
        messages.error(request, 'Вы не можете отправить на модерацию чужую сборку')
        return redirect('build_detail', build_id=build.id)
    
    if build.status in ['VERIFIED', 'SAVED', 'CONFIGURING']:
        build.status = 'PENDING_MODERATION'
        build.save()
        messages.success(request, 'Сборка отправлена на модерацию')
    else:
        messages.error(request, 'Нельзя отправить эту сборку на модерацию')
    
    return redirect('build_detail', build_id=build.id)

@staff_member_required
def moderation_delete(request, build_id):
    """Удаление сборки модератором"""
    build = get_object_or_404(Build, id=build_id)
    
    if request.method == 'POST':
        build_name = build.name
        build.delete()
        messages.success(request, f'✅ Сборка "{build_name}" успешно удалена модератором')
        return redirect('moderation_queue')
    
    context = {'build': build}
    return render(request, 'catalog/moderation/delete.html', context)

# ================ УПРАВЛЕНИЕ СБОРКАМИ ================

def my_builds(request):
    if not request.user.is_authenticated:
        messages.warning(request, 'Войдите, чтобы просматривать свои сборки')
        return redirect('login')
    
    # Получаем сборки текущего пользователя
    builds = request.user.builds.all().order_by('-id')
    
    context = {'all_builds': builds}
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
    if request.user.is_authenticated:
        build.user = request.user   # привязываем к пользователю
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

def update_description(request, build_id):
    """Обновление описания сборки"""
    build = get_object_or_404(Build, id=build_id)
    
    # Проверяем права доступа
    if request.user.is_authenticated and build.user == request.user:
        if request.method == 'POST':
            description = request.POST.get('description', '').strip()
            build.description = description
            build.save()
            messages.success(request, '✅ Описание сборки обновлено!')
        else:
            messages.error(request, '❌ Неверный метод запроса')
    else:
        messages.error(request, '❌ У вас нет прав для редактирования этой сборки')
    
    return redirect('build_detail', build_id=build.id)

# ================ ПОЛЬЗОВАТЕЛИ ================

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно!')
            return redirect('index')
        else:
            # Выводим конкретные ошибки
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserCreationForm()
    
    return render(request, 'catalog/register.html', {'form': form})

@login_required
def profile(request):
    """Личный кабинет пользователя"""
    builds = request.user.builds.all().order_by('-id')
    
    # Статистика
    stats = {
        'total_builds': builds.count(),
        'published_builds': builds.filter(status='PUBLISHED').count(),
        'pending_builds': builds.filter(status='PENDING_MODERATION').count(),
        'rejected_builds': builds.filter(status='REJECTED').count(),
        'total_views': sum(build.views_count for build in builds),
        'total_likes': sum(build.likes.count() for build in builds),
    }
    
    context = {
        'user': request.user,
        'builds': builds,
        'stats': stats,
    }
    return render(request, 'catalog/profile.html', context)

@login_required
def profile_edit(request):
    """Редактирование профиля"""
    if request.method == 'POST':
        # Обновляем имя и email
        request.user.username = request.POST.get('username', request.user.username)
        request.user.email = request.POST.get('email', request.user.email)
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.save()
        
        messages.success(request, '✅ Профиль успешно обновлён!')
        return redirect('profile')
    
    return render(request, 'catalog/profile_edit.html', {'user': request.user})

@login_required
def change_password(request):
    """Смена пароля"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Важно: чтобы не разлогинило
            messages.success(request, '✅ Пароль успешно изменён!')
            return redirect('profile')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'catalog/change_password.html', {'form': form})

def add_comment(request, build_id):
    """Добавление комментария к сборке"""
    build = get_object_or_404(Build, id=build_id, status='PUBLISHED')
    
    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        
        if not text:
            messages.error(request, '❌ Комментарий не может быть пустым')
            return redirect('public_build_detail', build_id=build.id)
        
        if len(text) > 2000:
            messages.error(request, '❌ Комментарий не должен превышать 2000 символов')
            return redirect('public_build_detail', build_id=build.id)
        
        # Создаём комментарий
        comment = Comment.objects.create(
            build=build,
            user=request.user if request.user.is_authenticated else None,
            text=text
        )
        
        messages.success(request, '✅ Комментарий добавлен!')
        return redirect('public_build_detail', build_id=build.id)
    
    return redirect('public_build_detail', build_id=build.id)

def delete_comment(request, comment_id):
    """Удаление комментария (только автор или модератор)"""
    comment = get_object_or_404(Comment, id=comment_id)
    build_id = comment.build.id
    
    # Проверка прав: автор комментария, модератор или автор сборки
    if request.user.is_authenticated:
        is_author = comment.user == request.user
        is_moderator = request.user.is_staff
        is_build_author = comment.build.user == request.user
        
        if is_author or is_moderator or is_build_author:
            comment.delete()
            messages.success(request, '🗑️ Комментарий удалён')
        else:
            messages.error(request, '❌ У вас нет прав для удаления этого комментария')
    else:
        messages.error(request, '❌ Требуется авторизация')
    
    return redirect('public_build_detail', build_id=build_id)

# ================ РУКОВОДСТВО ================

def guide_list(request):
    """Список всех гайдов"""
    guides = Guide.objects.filter(status='PUBLISHED').order_by('-created_at')
    
    # Фильтры по категории
    category = request.GET.get('category')
    if category:
        guides = guides.filter(category=category)
    
    context = {
        'guides': guides,
        'selected_category': category,
        'guide': Guide,
    }
    return render(request, 'catalog/guide_list.html', context)

def guide_detail(request, slug):
    """Детальная страница гайда"""
    # Показываем только опубликованные гайды для обычных пользователей
    if request.user.is_staff:
        # Модераторы могут видеть гайды в любом статусе
        guide = get_object_or_404(Guide, slug=slug)
    else:
        # Обычные пользователи видят только опубликованные
        guide = get_object_or_404(Guide, slug=slug, status='PUBLISHED')
    
    # Увеличиваем счётчик просмотров
    guide.views_count += 1
    guide.save(update_fields=['views_count'])
    
    # Похожие гайды
    similar_guides = Guide.objects.filter(
        category=guide.category, 
        status='PUBLISHED'
    ).exclude(id=guide.id)[:3]
    
    context = {
        'guide': guide,
        'similar_guides': similar_guides,
    }
    return render(request, 'catalog/guide_detail.html', context)

@login_required
def guide_create(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        category = request.POST.get('category')
        content = request.POST.get('content', '').strip()
        
        if not title or not content:
            messages.error(request, '❌ Заполните заголовок и содержание')
            return redirect('guide_create')
        
        guide = Guide.objects.create(
            title=title,
            category=category,
            content=content,
            author=request.user,
            status='PENDING'
        )
        
        # Обработка загруженных изображений
        images = request.FILES.getlist('images')
        if images:
            # Добавляем информацию о загруженных изображениях в текст
            image_links = []
            for img in images:
                # Сохраняем изображение
                guide_image = GuideImage.objects.create(
                    guide=guide,
                    image=img
                )
                image_links.append(
                    f'<img src="{guide_image.image.url}" alt="Изображение" style="max-width: 100%; margin: 20px 0; border-radius: 8px;">'
                )
            
            # Добавляем ссылки на изображения в конец текста
            if image_links:
                guide.content += '\n\n' + '\n'.join(image_links)
                guide.save()
        
        messages.success(request, '✅ Гайд отправлен на модерацию!')
        return redirect('guide_list')
    
    context = {
        'categories': Guide.CATEGORY_CHOICES,
    }
    return render(request, 'catalog/guide_form.html', context)

@login_required
@login_required
def guide_edit(request, guide_id):
    guide = get_object_or_404(Guide, id=guide_id, author=request.user)
    
    if request.method == 'POST':
        guide.title = request.POST.get('title', '').strip()
        guide.category = request.POST.get('category')
        guide.content = request.POST.get('content', '').strip()
        
        # Удаление отмеченных изображений
        for img in guide.images.all():
            if request.POST.get(f'delete_image_{img.id}'):
                img.delete()
        
        # Обработка новых изображений
        images = request.FILES.getlist('images')
        if images:
            image_links = []
            for img in images:
                guide_image = GuideImage.objects.create(
                    guide=guide,
                    image=img
                )
                image_links.append(
                    f'<img src="{guide_image.image.url}" alt="Изображение" style="max-width: 100%; margin: 20px 0; border-radius: 8px;">'
                )
            
            if image_links:
                guide.content += '\n\n' + '\n'.join(image_links)
        
        if guide.status == 'REJECTED':
            guide.status = 'PENDING'
        
        guide.save()
        
        messages.success(request, '✅ Гайд обновлён и отправлен на повторную модерацию!')
        return redirect('guide_detail', slug=guide.slug)
    
    context = {
        'guide': guide,
        'categories': Guide.CATEGORY_CHOICES,
    }
    return render(request, 'catalog/guide_form.html', context)

@login_required
def guide_delete(request, guide_id):
    """Удаление своего гайда"""
    guide = get_object_or_404(Guide, id=guide_id, author=request.user)
    
    if request.method == 'POST':
        guide.delete()
        messages.success(request, '🗑️ Гайд удалён')
        return redirect('guide_list')
    
    return render(request, 'catalog/guide_confirm_delete.html', {'guide': guide})

@staff_member_required
def guide_moderation_queue(request):
    """Очередь модерации гайдов"""
    pending_guides = Guide.objects.filter(status='PENDING').order_by('-created_at')
    published_guides = Guide.objects.filter(status='PUBLISHED').order_by('-created_at')[:10]
    rejected_guides = Guide.objects.filter(status='REJECTED').order_by('-created_at')[:10]
    
    context = {
        'pending_guides': pending_guides,
        'published_guides': published_guides,
        'rejected_guides': rejected_guides,
    }
    return render(request, 'catalog/moderation/guide_queue.html', context)

@staff_member_required
def guide_moderation_approve(request, guide_id):
    """Одобрение гайда"""
    guide = get_object_or_404(Guide, id=guide_id)
    guide.status = 'PUBLISHED'
    guide.save()
    messages.success(request, f'✅ Гайд "{guide.title}" опубликован')
    return redirect('guide_moderation_queue')

@staff_member_required
def guide_moderation_reject(request, guide_id):
    """Отклонение гайда"""
    guide = get_object_or_404(Guide, id=guide_id)
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        guide.status = 'REJECTED'
        guide.save()
        messages.success(request, f'❌ Гайд "{guide.title}" отклонён')
        return redirect('guide_moderation_queue')
    
    return render(request, 'catalog/moderation/guide_reject.html', {'guide': guide})

