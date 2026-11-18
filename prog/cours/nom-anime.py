def générer_nom_anime(prénom, âge):
    parties_nom = [
        "Takahashi",
        "Fujimoto",
        "Yamamoto",
        "Kobayashi",
        "Hoshino",
        "Abe",
        "Tanaka",
        "Matsumoto",
        "Sasaki",
        "Inoue",
    ]

    # Un nombre calculé à partir du prénom : la somme des codes de ses lettres
    nombre = sum(ord(lettre) for lettre in prénom.lower())

    nom = parties_nom[nombre % len(parties_nom)]

    if âge < 13:
        honorifique = "-chan"
    elif âge < 18:
        honorifique = "-kun" if nombre % 2 == 0 else "-san"
    elif âge < 30:
        honorifique = "-san"
    elif âge < 50:
        honorifique = "-sama"
    else:
        honorifique = "-sensei"

    return f"{nom}{honorifique} {prénom}"


prénom = input("Entrez votre vrai prénom : ")
âge = int(input("Entrez votre âge : "))
nom_anime = générer_nom_anime(prénom, âge)
print(f"Votre nom d'anime est : {nom_anime}")
