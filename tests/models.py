from django.db import models

# Create your models here.

from django.contrib.auth.models import User

from django.db import models, transaction
from simple_history.models import HistoricalRecords

def json_defa():
    return []


CON_TYPES = (
    (1, 'Income'),
    (0, 'Outcome'),
)

CONTACT_EXTRA_TYPES = (
    (0, 'First'),
    (1, 'Second'),
)

CONTACT_SOURCES = (
    (1, 'Visit'),
    (2, 'Call'),
)

class Project(models.Model):
    class Meta():
        verbose_name = 'Проект'
        verbose_name_plural = 'Проекты'

    name = models.CharField('Наименование', max_length=300, blank=False, null=False)
    description = models.CharField('Описание', max_length=300, blank=True, null=True, default='-')
    history = HistoricalRecords()


class Client(models.Model):
    class Meta():
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'

    phone = models.CharField('Телефон', max_length=20, blank=False, null=False, default='-')
    fio = models.CharField('Ф.И.O.', max_length=300, blank=False, null=False, default='-')
    project = models.ForeignKey(Project, verbose_name='Проект', related_name='clients', blank=True, null=True, on_delete=models.CASCADE)
    user = models.ForeignKey(User, verbose_name='Пользователь', blank=True, null=True, on_delete=models.CASCADE)
    history = HistoricalRecords()

    def __str__(self):
        return '%s' % (self.id)


class Contact(models.Model):
    class Meta():
        verbose_name = 'Контакт'
        verbose_name_plural = 'Контакты'

    typex = models.PositiveSmallIntegerField('Вид', blank=False, null=False, default=1, choices=CON_TYPES)
    extra_type = models.PositiveSmallIntegerField('Тип', blank=False, null=True, default=0, choices=CONTACT_EXTRA_TYPES)
    source = models.PositiveSmallIntegerField('Источник', blank=False, null=False, default=1, choices=CONTACT_SOURCES)
    client = models.ForeignKey(Client, verbose_name='Клиент', related_name='contacts', blank=True, null=True,
                               on_delete=models.PROTECT)
    time = models.DateTimeField('Время обращения', blank=True, null=True)
    user = models.ForeignKey(User, verbose_name='Пользователь', blank=True, null=True, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, verbose_name='Проект', related_name='contacts', blank=True, null=True, on_delete=models.CASCADE)
    history = HistoricalRecords()