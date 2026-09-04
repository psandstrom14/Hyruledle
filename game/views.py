from django.shortcuts import render


def index(request):
    target_data = {
        "name": "Midna",
        "race": "Twili",
        "gender": "Female",
        "role": "Ally",
        "first_appearance_year": 2006,
        "game_count": 2,
    }

    guess_data = {
        "name": "Link",
        "race": "Hylian",
        "gender": "Male",
        "role": "Hero",
        "first_appearance_year": 1986,
        "game_count": 20,
    }

    feedback = {
        "name": guess_data["name"],
        "race": "match" if guess_data["race"] == target_data["race"] else "miss",
        "gender": "match" if guess_data["gender"] == target_data["gender"] else "miss",
        "role": "match" if guess_data["role"] == target_data["role"] else "miss",
        "first_appearance": (
            "match"
            if guess_data["first_appearance_year"] == target_data["first_appearance_year"]
            else "higher"
            if guess_data["first_appearance_year"] < target_data["first_appearance_year"]
            else "lower"
        ),
        "game_count": (
            "match"
            if guess_data["game_count"] == target_data["game_count"]
            else "higher"
            if guess_data["game_count"] < target_data["game_count"]
            else "lower"
        ),
    }

    context = {
        "title": "Hyruledle",
        "recent_guess": feedback,
        "guess_raw": guess_data,
    }
    return render(request, "game/index.html", context)
