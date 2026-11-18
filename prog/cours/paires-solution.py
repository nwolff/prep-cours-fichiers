les_mois = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]

nombres_de_jours = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

while les_mois:
    mois = les_mois.pop(0)
    jours = nombres_de_jours.pop(0)  # Il n'y a pas de risque de tomber sur une liste vide ici
                                     # parce que les deux listes ont la même longueur
    print(mois, ":", jours)