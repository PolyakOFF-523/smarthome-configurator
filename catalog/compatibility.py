# compatibility.py
from .models import Component
from decimal import Decimal

class CompatibilityChecker:
    def __init__(self, project):
        self.project = project
        
    def check_protocol(self, component1, component2):
        """Проверка совместимости протоколов"""
        if component1.protocol != component2.protocol:
            return False, f"Протоколы {component1.get_protocol_display()} и {component2.get_protocol_display()} несовместимы"
        return True, "Протоколы совместимы"
    
    def check_range(self, component, distance_from_hub):
        """Проверка радиуса действия"""
        # Если радиус действия 0, значит устройство должно быть рядом с хабом или подключено по проводу
        if component.range_meters == 0:
            if distance_from_hub > 1:  # Если расстояние больше 1 метра
                # Ищем альтернативу с большим радиусом
                max_price = component.price * Decimal(str(1.3))
                alternative = Component.objects.filter(
                    protocol=component.protocol,
                    range_meters__gt=5,  # Радиус больше 5 метров
                    price__lte=max_price,
                    category=component.category  # Та же категория
                ).exclude(id=component.id).first()
                
                if alternative:
                    return False, f"Устройство {component.name} должно находиться рядом с хабом. Рекомендуем беспроводную альтернативу", alternative
                else:
                    return False, f"Устройство {component.name} должно находиться рядом с хабом (на расстоянии не более 1 метра)", None
            return True, "Устройство подключается напрямую, радиус не учитывается", None
        
        # Обычная проверка радиуса
        if distance_from_hub > component.range_meters:
            # Ищем альтернативу с большим радиусом
            max_price = component.price * Decimal(str(1.3))
            alternative = Component.objects.filter(
                protocol=component.protocol,
                range_meters__gte=distance_from_hub,
                price__lte=max_price,
                category=component.category  # Та же категория
            ).exclude(id=component.id).first()
            
            if alternative:
                return False, f"Радиус действия {component.range_meters}м недостаточен (нужно {distance_from_hub}м)", alternative
            else:
                return False, f"Радиус действия {component.range_meters}м недостаточен (нужно {distance_from_hub}м)", None
        
        return True, "Радиус действия достаточен", None
    
    def check_power_source(self, component, room_type):
        """Проверка источника питания для типа комнаты"""
        if room_type == 'BATHROOM' and component.power_source == 'MAINS':
            # В ванной лучше использовать батарейки
            max_price = component.price * Decimal(str(1.2))
            alternative = Component.objects.filter(
                protocol=component.protocol,
                power_source='BATTERY',
                price__lte=max_price
            ).exclude(id=component.id).first()
            return False, "В ванной комнате рекомендуется использовать устройства на батарейках", alternative
        return True, "Питание подходит", None
    
    def get_dominant_protocol(self, build):
        """Определяет основной протокол в сборке"""
        components = [bc.component for bc in build.buildcomponent_set.all()]
        if not components:
            return None
        
        # Считаем количество устройств по протоколам
        protocol_count = {}
        for comp in components:
            protocol_count[comp.protocol] = protocol_count.get(comp.protocol, 0) + 1
        
        # Возвращаем самый популярный протокол
        if protocol_count:
            return max(protocol_count, key=protocol_count.get)
        return None
    
    def find_compatible_alternative(self, component, build, distance_from_hub):
        """Поиск альтернативы, совместимой с существующей сборкой"""
        # Определяем доминирующий протокол в сборке
        main_protocol = self.get_dominant_protocol(build)
        
        # Базовая цена с запасом 30%
        max_price = component.price * Decimal(str(1.3))
        
        # Базовый запрос
        base_query = Component.objects.filter(
            price__lte=max_price,
            category=component.category  # Та же категория
        ).exclude(id=component.id)
        
        # Если устройство имеет радиус 0, ищем с радиусом > 5
        if component.range_meters == 0:
            base_query = base_query.filter(range_meters__gt=5)
        else:
            base_query = base_query.filter(range_meters__gte=distance_from_hub)
        
        # Если есть доминирующий протокол, ищем с ним
        if main_protocol:
            alternative = base_query.filter(protocol=main_protocol).first()
            if alternative:
                return alternative
        
        # Если не нашли, ищем с протоколом исходного устройства
        alternative = base_query.filter(protocol=component.protocol).first()
        if alternative:
            return alternative
        
        # Если всё равно не нашли, ищем любое в той же категории
        return base_query.first()
    
    def check_all(self, build, new_component, room, distance_from_hub):
        """Полная проверка совместимости"""
        issues = []
        alternative = None
        
        # Проверяем радиус (теперь с учётом нулевого радиуса)
        range_ok, range_msg, alt = self.check_range(new_component, float(distance_from_hub))
        if not range_ok:
            issues.append(range_msg)
            if alt and not alternative:
                alternative = alt
        
        # Проверяем с каждым существующим компонентом в сборке
        existing_components = [bc.component for bc in build.buildcomponent_set.all()]
        
        if existing_components:
            # Проверяем протокол с первым устройством
            first_component = existing_components[0]
            compatible, msg = self.check_protocol(new_component, first_component)
            if not compatible:
                issues.append(msg)
                # Если ещё нет альтернативы, ищем совместимую
                if not alternative:
                    alternative = self.find_compatible_alternative(new_component, build, float(distance_from_hub))
        
        # Проверяем питание для специфичных комнат
        if room.name == 'BATHROOM':
            power_ok, power_msg, alt = self.check_power_source(new_component, 'BATHROOM')
            if not power_ok:
                issues.append(power_msg)
                if alt and not alternative:
                    alternative = alt
        
        # Убираем дубликаты ошибок
        issues = list(dict.fromkeys(issues))
        
        if issues:
            return False, issues, alternative
        return True, [], None

def analyze_placement(build, project):
    """Анализ расстановки устройств"""
    advice = []
    
    for room in project.rooms.all():
        room_components = build.buildcomponent_set.filter(room=room)
        
        if room_components.exists():
            # Советы для конкретной комнаты
            tips = []
            
            # Проверяем достаточно ли устройств
            total_devices = room_components.count()
            if total_devices < 2:
                tips.append("💡 В этой комнате мало устройств, рекомендуется добавить базовые датчики")
            
            # Считаем потребление
            total_power_room = sum(bc.component.power_consumption_watts * bc.quantity 
                                  for bc in room_components)
            if total_power_room > 50:
                tips.append(f"⚡ Высокое энергопотребление в комнате: {total_power_room} Вт")
            
            # Проверяем разнообразие протоколов
            protocols = set(bc.component.protocol for bc in room_components)
            if len(protocols) > 1:
                tips.append(f"🔄 В комнате используются разные протоколы: {', '.join(protocols)}")
            
            advice.append({
                'room': room.get_name_display(),
                'components': room_components,
                'tips': tips,
                'total_power': total_power_room
            })
    
    return advice