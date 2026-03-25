from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    Institution, Faculty, Department, Course, Session, 
    Semester, User, Profile, Admin, Teacher, Student, Verification
)

# --- Inlines (The "Secret Sauce" for UX) ---

class FacultyInline(admin.TabularInline):
    model = Faculty
    extra = 1

class DepartmentInline(admin.TabularInline):
    model = Department
    extra = 1

class SemesterInline(admin.TabularInline):
    model = Semester
    extra = 2

# --- Model Admin Customizations ---

@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'id')
    search_fields = ('name', 'short_name')
    inlines = [FacultyInline]

@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ('name', 'institution')
    list_filter = ('institution',)
    search_fields = ('name',)
    inlines = [DepartmentInline]

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'faculty', 'get_institution')
    list_filter = ('faculty__institution', 'faculty')
    search_fields = ('name',)

    def get_institution(self, obj):
        return obj.faculty.institution
    get_institution.short_description = 'Institution'

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('name', 'institution', 'start_date', 'end_date', 'activated_at')
    list_filter = ('institution',)
    inlines = [SemesterInline]

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Extending the built-in UserAdmin to handle our custom UUID User"""
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Role Information', {'fields': ('role',)}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Role Information', {'fields': ('role', 'email', 'first_name', 'last_name')}),
    )

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'user', 'institution', 'department', 'created_at')
    list_filter = ('institution', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at',)

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('matric_number', 'get_name', 'verification_status', 'entry_date')
    list_filter = ('verification_status', 'entry_date')
    search_fields = ('matric_number', 'profile__user__first_name', 'profile__user__last_name')
    actions = ['mark_as_verified']

    def get_name(self, obj):
        return obj.profile.full_name
    get_name.short_description = 'Student Name'

    @admin.action(description='Verify selected students')
    def mark_as_verified(self, request, queryset):
        queryset.update(verification_status='VERIFIED')

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('staff_number', 'title', 'get_name', 'rank')
    list_filter = ('rank',)
    search_fields = ('staff_number', 'profile__user__last_name')

    def get_name(self, obj):
        return obj.profile.full_name
    get_name.short_description = 'Teacher Name'

@admin.register(Verification)
class VerificationAdmin(admin.ModelAdmin):
    list_display = ('student', 'verifier', 'status', 'session', 'created_at')
    list_filter = ('status', 'session')
    search_fields = ('student__username', 'verifier__username')

# Register remaining simple models
admin.site.register(Course)
admin.site.register(Semester)
admin.site.register(Admin)