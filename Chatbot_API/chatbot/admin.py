from django.contrib import admin

from .models import Query

@admin.register(Query)
class QueryAdmin(admin.ModelAdmin):
    list_display = ('question', 'timestamp')
    search_fields = ('question', 'answer')
    readonly_fields = ('timestamp',)