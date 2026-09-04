from django.contrib import admin

from .models import Character, Game


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("name", "release_year", "api_id")


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ("name", "race", "gender", "role", "first_appearance_year", "game_count")
