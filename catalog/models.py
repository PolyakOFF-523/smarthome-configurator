from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User


class Ecosystem(models.Model):
    """Экосистема умного дома (Яндекс, Xiaomi, Apple и т.д.)"""
    name = models.CharField("Название", max_length=100)
    slug = models.SlugField("URL", unique=True)
    logo = models.ImageField("Логотип", upload_to='ecosystems/', blank=True, null=True)
    description = models.TextField("Описание", blank=True)
    website = models.URLField("Сайт", blank=True)
    order = models.IntegerField("Порядок", default=0)
    
    class Meta:
        verbose_name = "Экосистема"
        verbose_name_plural = "Экосистемы"
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('ecosystem_detail', kwargs={'slug': self.slug})

class Category(models.Model):
    name = models.CharField("Название", max_length=100)
    slug = models.SlugField("URL", unique=True)
    icon = models.CharField("Иконка", max_length=50, blank=True, help_text="Класс иконки Bootstrap")
    image = models.ImageField("Изображение", upload_to='categories/', blank=True, null=True)
    description = models.TextField("Описание", blank=True)
    
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        verbose_name="Родительская категория", 
        related_name='children'
    )
    
    order = models.IntegerField("Порядок", default=0)
    
    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ['order', 'name']  # убрали main_category
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} → {self.name}"
        return self.name
    
    def get_absolute_url(self):
        if self.parent:
            return reverse('subcategory_detail', kwargs={
                'category_slug': self.parent.slug,
                'subcategory_slug': self.slug
            })
        return reverse('category_detail', kwargs={'slug': self.slug})

class Tag(models.Model):
    """Теги для устройств (для кухни, энергоэффективное и т.д.)"""
    name = models.CharField("Название", max_length=50)
    slug = models.SlugField("URL", unique=True)
    
    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Component(models.Model):
    """Комплектующее"""
    PROTOCOL_CHOICES = [
        ('ZIGBEE', 'ZigBee'),
        ('Z_WAVE', 'Z-Wave'),
        ('WIFI', 'Wi-Fi'),
        ('BLE', 'Bluetooth'),
        ('MATTER', 'Matter'),
        ('THREAD', 'Thread'),
        ('RF', 'Радиочастотный'),
        ('IR', 'ИК-пульт'),
    ]
    
    POWER_CHOICES = [
        ('BATTERY', 'Батарейки'),
        ('USB', 'USB'),
        ('MAINS', 'От сети 220V'),
        ('SOLAR', 'Солнечная батарея'),
        ('CR2032', 'CR2032'),
        ('AA', 'AA (пальчиковые)'),
        ('AAA', 'AAA (мизинчиковые)'),
    ]
    
    name = models.CharField("Название", max_length=250)
    slug = models.SlugField("URL", unique=True, max_length=250)
    
    # Связи
    ecosystem = models.ForeignKey(
        Ecosystem, 
        on_delete=models.CASCADE, 
        verbose_name="Экосистема", 
        related_name='components'
    )
    category = models.ForeignKey(
        Category, 
        on_delete=models.CASCADE, 
        verbose_name="Категория", 
        related_name='components'
    )
    
    tags = models.ManyToManyField(
            Tag,
            blank=True,
            verbose_name="Теги",
            related_name='components'
        )

    # Характеристики
    protocol = models.CharField("Протокол", max_length=20, choices=PROTOCOL_CHOICES)
    power_source = models.CharField("Питание", max_length=20, choices=POWER_CHOICES)
    range_meters = models.FloatField("Радиус действия (м)", default=0)
    power_consumption_watts = models.FloatField("Энергопотребление (Вт)", default=0)
    price = models.DecimalField("Цена", max_digits=10, decimal_places=2)
    
    # Внешний вид
    image = models.ImageField("Основное изображение", upload_to='components/', blank=True, null=True)
    description = models.TextField("Описание", blank=True)
    specifications = models.JSONField("Характеристики", default=dict, blank=True)
    
    # Совместимость
    requires_hub = models.BooleanField("Требует хаб", default=True)
    compatible_with = models.ManyToManyField(
        'self', 
        symmetrical=True, 
        blank=True, 
        verbose_name="Совместимо с"
    )
    
    # Статус
    in_stock = models.BooleanField("В наличии", default=True)
    is_popular = models.BooleanField("Популярное", default=False)
    is_new = models.BooleanField("Новинка", default=False)
    
    # Метаданные
    #created_at = models.DateTimeField("Дата добавления", auto_now_add=True)
    #updated_at = models.DateTimeField("Дата обновления", auto_now=True)
    
    class Meta:
        verbose_name = "Комплектующее"
        verbose_name_plural = "Комплектующие"
        ordering = ['-is_popular', '-is_new', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.ecosystem.name})"
    
    def get_absolute_url(self):
        return reverse('component_detail', kwargs={'slug': self.slug})

class ComponentImage(models.Model):
    """Дополнительные изображения компонента"""
    component = models.ForeignKey(Component, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField("Изображение", upload_to='components/gallery/')
    is_main = models.BooleanField("Главное", default=False)
    order = models.IntegerField("Порядок", default=0)
    
    class Meta:
        verbose_name = "Изображение"
        verbose_name_plural = "Изображения"
        ordering = ['-is_main', 'order']
    
    def __str__(self):
        return f"Изображение для {self.component.name}"

# Модели для сборок (старый функционал)
class Room(models.Model):
    """Комната в квартире пользователя"""
    ROOM_TYPES = [
        ('LIVING', 'Гостиная'),
        ('BEDROOM', 'Спальня'),
        ('KITCHEN', 'Кухня'),
        ('BATHROOM', 'Ванная'),
        ('CHILDREN', 'Детская'),
        ('OFFICE', 'Кабинет'),
        ('HALL', 'Прихожая'),
        ('OTHER', 'Другое'),
    ]
    
    name = models.CharField("Название", max_length=50, choices=ROOM_TYPES)
    area = models.FloatField("Площадь (м²)")
    
    def __str__(self):
        return self.get_name_display()

class UserProject(models.Model):
    """Проект пользователя (введенные параметры)"""
    rooms = models.ManyToManyField(Room)
    total_area = models.FloatField("Общая площадь")
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='projects'
    )

class Build(models.Model):
    """Готовая сборка"""
    PRICE_SEGMENT = [
        ('ECONOMY', 'Эконом'),
        ('STANDARD', 'Стандарт'),
        ('PREMIUM', 'Премиум'),
    ]
    
    STATUS_CHOICES = [
        ('DRAFT', 'Создана'),
        ('CONFIGURING', 'В настройке'),
        ('CHECKING', 'Проверяется'),
        ('NEEDS_FIX', 'Требует исправления'),
        ('VERIFIED', 'Проверена'),
        ('SAVED', 'Сохранена'),
        ('PENDING_MODERATION', 'На модерации'),
        ('PUBLISHED', 'Опубликована'),
        ('REJECTED', 'Отклонена'),
        ('ARCHIVED', 'Архивирована'),
    ]
    
    name = models.CharField(max_length=200)
    price_segment = models.CharField(max_length=20, choices=PRICE_SEGMENT)
    components = models.ManyToManyField(Component, through='BuildComponent')
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_power = models.FloatField("Общее энергопотребление (Вт)", default=0)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        verbose_name='Статус сборки'
    )

    description = models.TextField(
        "Описание сборки",
        blank=True,
        help_text="Расскажите о целях, особенностях и идее вашей сборки"
    )

    is_selected = models.BooleanField(
        default=False,
        verbose_name='Выбрана пользователем'
    )
    project = models.ForeignKey(
        UserProject, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='builds',
        verbose_name='Проект'
    )
    created_at = models.DateTimeField("Дата создания", auto_now_add=True, null=True)

    # Новые поля для социального функционала
    views_count = models.IntegerField("Просмотры", default=0)
    likes = models.ManyToManyField(
        User, 
        blank=True, 
        related_name='liked_builds',
        verbose_name='Лайки'
    )
    saved_by = models.ManyToManyField(
        User,
        blank=True,
        related_name='saved_builds',
        verbose_name='Сохранено пользователями'
    )

    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='builds'
    )

class BuildComponent(models.Model):
    """Компонент в конкретной сборке (с привязкой к комнате)"""
    build = models.ForeignKey(Build, on_delete=models.CASCADE)
    component = models.ForeignKey(Component, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.IntegerField(default=1)

class Comment(models.Model):
    """Комментарий к сборке"""
    build = models.ForeignKey(
        Build, 
        on_delete=models.CASCADE, 
        related_name='comments',
        verbose_name="Сборка"
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='comments',
        verbose_name="Пользователь",
        null=True,
        blank=True
    )
    text = models.TextField("Текст комментария")
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)
    is_active = models.BooleanField("Активен", default=True)
    
    class Meta:
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"
        ordering = ['-created_at']
    
    def __str__(self):
        author = self.user.username if self.user else "Аноним"
        return f"{author}: {self.text[:50]}"
    
class Guide(models.Model):
    """Гайд или руководство по умному дому"""
    CATEGORY_CHOICES = [
        ('BEGINNER', 'Для начинающих'),
        ('SETUP', 'Настройка'),
        ('SCENARIOS', 'Сценарии'),
        ('TROUBLESHOOTING', 'Решение проблем'),
        ('ADVANCED', 'Продвинутые советы'),
    ]
    
    STATUS_CHOICES = [
        ('DRAFT', 'Черновик'),
        ('PENDING', 'На модерации'),
        ('PUBLISHED', 'Опубликован'),
        ('REJECTED', 'Отклонён'),
    ]
    
    title = models.CharField("Заголовок", max_length=200)
    slug = models.SlugField("URL", unique=True, blank=True)
    category = models.CharField("Категория", max_length=20, choices=CATEGORY_CHOICES, default='BEGINNER')
    content = models.TextField("Содержание")
    excerpt = models.CharField("Краткое описание", max_length=300, blank=True)
    image = models.ImageField("Изображение", upload_to='guides/', blank=True, null=True)
    author = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='guides',
        verbose_name="Автор"
    )
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default='PENDING')
    views_count = models.IntegerField("Просмотры", default=0)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)
    
    class Meta:
        verbose_name = "Гайд"
        verbose_name_plural = "Гайды"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('guide_detail', kwargs={'slug': self.slug})

class GuideImage(models.Model):
    """Изображения для гайда"""
    guide = models.ForeignKey(Guide, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField("Изображение", upload_to='guides/')
    caption = models.CharField("Подпись", max_length=200, blank=True)
    order = models.IntegerField("Порядок", default=0)
    
    class Meta:
        verbose_name = "Изображение гайда"
        verbose_name_plural = "Изображения гайдов"
        ordering = ['order']
    
    def __str__(self):
        return f"{self.guide.title} - {self.order}"
