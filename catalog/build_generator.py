# build_generator.py
from django.db import models
from .models import Build, Component, BuildComponent

class BuildGenerator:
    def __init__(self, project):
        self.project = project
        
    def generate_all_builds(self):
        """Генерирует все варианты сборок"""
        builds = {}
        builds['economy'] = self.generate_build('🌱 Эконом', 'ECONOMY', max_price=5000)
        builds['standard'] = self.generate_build('⭐ Стандарт', 'STANDARD', max_price=15000)
        builds['premium'] = self.generate_build('👑 Премиум', 'PREMIUM', max_price=50000)
        builds['custom'] = Build.objects.create(
            name="🔧 Своя сборка", 
            price_segment='ECONOMY', 
            status='DRAFT',
            project=self.project,
        )
        return builds
    
    def generate_build(self, name, segment, max_price):
        # Проверяем, существует ли уже сборка для этого проекта с таким сегментом
        existing_build = Build.objects.filter(project=self.project, price_segment=segment).first()
        if existing_build:
            return existing_build  # Возвращаем существующую, не создаём новую
        
        # Если не существует, создаём новую
        from datetime import datetime
        date_str = datetime.now().strftime('%d.%m.%Y')
        
        default_names = {
            'ECONOMY': '🌱 Эконом',
            'STANDARD': '⭐ Стандарт',
            'PREMIUM': '👑 Премиум',
        }
        
        build_name = f"{default_names.get(segment, name)} ({date_str})"
        
        build = Build.objects.create(
            name=build_name,
            price_segment=segment, 
            status='DRAFT',
            is_selected=False,
            project=self.project,
        )

        # Найдём подходящий хаб
        hub = self._select_hub(segment, max_price)
        if hub:
            BuildComponent.objects.create(
                build=build, 
                component=hub, 
                quantity=1, 
                room=None
            )
            print(f"Добавлен хаб: {hub.name}")
        
        # Для каждой комнаты добавляем устройства
        for room in self.project.rooms.all():
            # Датчик движения
            motion = self._select_component(['движения', 'motion'], max_price * 0.1, hub)
            if motion:
                existing = BuildComponent.objects.filter(
                    build=build, component=motion, room=room
                ).first()
                if not existing:
                    BuildComponent.objects.create(
                        build=build, component=motion, room=room, quantity=1
                    )
            
            # Датчик открытия
            door = self._select_component(['двери', 'окна', 'door', 'window'], max_price * 0.1, hub)
            if door:
                existing = BuildComponent.objects.filter(
                    build=build, component=door, room=room
                ).first()
                if not existing:
                    BuildComponent.objects.create(
                        build=build, component=door, room=room, quantity=1
                    )
            
            # Датчик температуры (для стандарт и премиум)
            if segment in ['STANDARD', 'PREMIUM']:
                temp = self._select_component(['температуры', 'влажности', 'temperature', 'humidity'], max_price * 0.08, hub)
                if temp:
                    existing = BuildComponent.objects.filter(
                        build=build, component=temp, room=room
                    ).first()
                    if not existing:
                        BuildComponent.objects.create(
                            build=build, component=temp, room=room, quantity=1
                        )
            
            # Умная лампа (количество зависит от площади)
            lamp = self._select_component(['лампа', 'bulb', 'led'], max_price * 0.05, hub)
            if lamp:
                lamp_count = max(1, int(room.area / 10))
                existing = BuildComponent.objects.filter(
                    build=build, component=lamp, room=room
                ).first()
                
                if existing:
                    existing.quantity += lamp_count
                    existing.save()
                else:
                    BuildComponent.objects.create(
                        build=build, component=lamp, room=room, quantity=lamp_count
                    )
            
            # Умная розетка (для премиум)
            if segment == 'PREMIUM':
                plug = self._select_component(['розетка', 'plug'], max_price * 0.05, hub)
                if plug:
                    existing = BuildComponent.objects.filter(
                        build=build, component=plug, room=room
                    ).first()
                    if not existing:
                        BuildComponent.objects.create(
                            build=build, component=plug, room=room, quantity=1
                        )
            
            # Камера (одна на всю квартиру, только для премиум)
            if segment == 'PREMIUM' and room == self.project.rooms.first():
                camera = self._select_component(['камера', 'camera'], max_price * 0.15, hub)
                if camera:
                    existing = BuildComponent.objects.filter(
                        build=build, component=camera, room=room
                    ).first()
                    if not existing:
                        BuildComponent.objects.create(
                            build=build, component=camera, room=room, quantity=1
                        )
        
        self.calculate_totals(build)
        return build
    
    def _select_hub(self, segment, max_price):
        """Выбор хаба в зависимости от сегмента"""
        if segment == 'ECONOMY':
            # Для эконом - самый дешевый хаб
            return Component.objects.filter(
                requires_hub=False,
                price__lte=3000
            ).order_by('price').first()
        
        elif segment == 'STANDARD':
            # Для стандарт - Xiaomi Hub
            return Component.objects.filter(
                requires_hub=False,
                name__icontains='xiaomi',
                price__lte=5000
            ).first()
        
        else:  # PREMIUM
            # Для премиум - Philips Hue или Yandex Station
            hub = Component.objects.filter(
                requires_hub=False,
                name__icontains='philips hue bridge'
            ).first()
            if not hub:
                hub = Component.objects.filter(
                    requires_hub=False,
                    name__icontains='yandex station'
                ).first()
            return hub
    
    def _select_component(self, keywords, max_price, hub=None):
        """Выбор компонента по ключевым словам"""
        query = Component.objects.all()
        
        # Фильтр по ключевым словам в названии
        name_filter = None
        for kw in keywords:
            if name_filter is None:
                name_filter = models.Q(name__icontains=kw)
            else:
                name_filter |= models.Q(name__icontains=kw)
        
        if name_filter:
            query = query.filter(name_filter)
        
        # Фильтр по цене
        query = query.filter(price__lte=max_price)
        
        # Если есть хаб, предпочитаем устройства, совместимые с ним
        if hub:
            compatible = query.filter(compatible_with=hub).first()
            if compatible:
                return compatible
        
        return query.first()
    
    def calculate_totals(self, build):
        """Пересчет общей стоимости и энергопотребления"""
        total_price = 0
        total_power = 0
        
        for bc in build.buildcomponent_set.all():
            total_price += bc.component.price * bc.quantity
            total_power += bc.component.power_consumption_watts * bc.quantity
        
        build.total_price = total_price
        build.total_power = total_power
        build.save()
        return total_price, total_power