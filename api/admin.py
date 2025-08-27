from django.contrib import admin
from django.db.models import Sum, Count
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Transaction, Budget, Category, Goal, 
    RecurringTransaction, UserProfile
)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'color_preview', 'icon', 'is_default', 'transaction_count', 'created_at')
    list_filter = ('is_default', 'created_at')
    search_fields = ('name', 'user__username', 'user__email')
    readonly_fields = ('created_at',)
    
    def color_preview(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 3px 10px; color: white; border-radius: 3px;">{}</span>',
            obj.color, obj.color
        )
    color_preview.short_description = 'Color'
    
    def transaction_count(self, obj):
        count = obj.transaction_set.count()
        if count > 0:
            url = reverse('admin:api_transaction_changelist') + f'?category__id__exact={obj.id}'
            return format_html('<a href="{}">{} transactions</a>', url, count)
        return '0 transactions'
    transaction_count.short_description = 'Transactions'

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('description', 'user', 'amount', 'category', 'transaction_type', 'date', 'created_at')
    list_filter = ('transaction_type', 'date', 'category', 'is_recurring')
    search_fields = ('description', 'user__username', 'user__email', 'notes')
    date_hierarchy = 'date'
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user', 'category')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'description', 'amount', 'transaction_type', 'date')
        }),
        ('Categorization', {
            'fields': ('category',)
        }),
        ('Additional Details', {
            'fields': ('notes', 'receipt_image', 'is_recurring'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('user', 'category')

@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('category', 'user', 'amount', 'period', 'spent_amount_display', 'progress_bar', 'start_date', 'end_date', 'is_active')
    list_filter = ('period', 'is_active', 'start_date')
    search_fields = ('category__name', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at', 'spent_amount', 'remaining_amount', 'percentage_used')
    raw_id_fields = ('user', 'category')
    
    fieldsets = (
        ('Budget Setup', {
            'fields': ('user', 'category', 'amount', 'period')
        }),
        ('Time Period', {
            'fields': ('start_date', 'end_date')
        }),
        ('Settings', {
            'fields': ('alert_threshold', 'is_active')
        }),
        ('Current Status', {
            'fields': ('spent_amount', 'remaining_amount', 'percentage_used'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def spent_amount_display(self, obj):
        spent = obj.spent_amount
        if obj.is_over_budget:
            return format_html('<span style="color: red; font-weight: bold;">${:,.2f}</span>', spent)
        elif obj.is_near_limit:
            return format_html('<span style="color: orange; font-weight: bold;">${:,.2f}</span>', spent)
        return f'${spent:,.2f}'
    spent_amount_display.short_description = 'Spent'
    
    def progress_bar(self, obj):
        percentage = min(float(obj.percentage_used), 100)
        if percentage > 100:
            color = 'red'
        elif percentage > float(obj.alert_threshold):
            color = 'orange'
        else:
            color = 'green'
        
        return format_html(
            '<div style="width: 100px; background-color: #f0f0f0; border: 1px solid #ccc;">'
            '<div style="width: {}%; background-color: {}; height: 20px; text-align: center; color: white; font-size: 12px; line-height: 20px;">'
            '{:.1f}%'
            '</div>'
            '</div>',
            min(percentage, 100), color, percentage
        )
    progress_bar.short_description = 'Progress'

@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'goal_type', 'target_amount', 'current_amount', 'progress_percentage_display', 'target_date', 'is_achieved')
    list_filter = ('goal_type', 'is_achieved', 'target_date')
    search_fields = ('name', 'description', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at', 'progress_percentage', 'remaining_amount', 'days_remaining', 'monthly_savings_needed')
    raw_id_fields = ('user',)
    
    fieldsets = (
        ('Goal Information', {
            'fields': ('user', 'name', 'description', 'goal_type')
        }),
        ('Target & Progress', {
            'fields': ('target_amount', 'current_amount', 'target_date', 'is_achieved')
        }),
        ('Calculated Fields', {
            'fields': ('progress_percentage', 'remaining_amount', 'days_remaining', 'monthly_savings_needed'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def progress_percentage_display(self, obj):
        percentage = float(obj.progress_percentage)
        if obj.is_achieved:
            color = 'green'
            text = f'{percentage:.1f}% ✓'
        elif percentage >= 75:
            color = 'orange'
            text = f'{percentage:.1f}%'
        else:
            color = 'blue'
            text = f'{percentage:.1f}%'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, text
        )
    progress_percentage_display.short_description = 'Progress'

@admin.register(RecurringTransaction)
class RecurringTransactionAdmin(admin.ModelAdmin):
    list_display = ('description', 'user', 'amount', 'frequency', 'next_occurrence', 'is_active', 'created_at')
    list_filter = ('frequency', 'transaction_type', 'is_active')
    search_fields = ('description', 'user__username', 'user__email')
    readonly_fields = ('created_at',)
    raw_id_fields = ('user', 'category')
    
    fieldsets = (
        ('Transaction Details', {
            'fields': ('user', 'description', 'amount', 'category', 'transaction_type')
        }),
        ('Recurrence Settings', {
            'fields': ('frequency', 'start_date', 'end_date', 'next_occurrence', 'is_active')
        }),
        ('Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'currency', 'timezone', 'monthly_income', 'created_at')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user',)
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Preferences', {
            'fields': ('currency', 'timezone', 'notification_preferences')
        }),
        ('Financial Info', {
            'fields': ('monthly_income',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

# Custom admin site header
admin.site.site_header = "Financial Management Admin"
admin.site.site_title = "Financial Management"
admin.site.index_title = "Welcome to Financial Management Administration"