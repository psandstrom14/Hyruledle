from django.db import models


class Game(models.Model):
    api_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    release_year = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.name


class Character(models.Model):
    name = models.CharField(max_length=200)
    race = models.CharField(max_length=100, null=True, blank=True)
    gender = models.CharField(max_length=50, null=True, blank=True)
    role = models.CharField(max_length=50, null=True, blank=True)
    first_appearance_year = models.IntegerField(null=True, blank=True)
    game_count = models.IntegerField(default=0)
    games = models.ManyToManyField(Game, related_name="characters")

    def __str__(self):
        return self.name
