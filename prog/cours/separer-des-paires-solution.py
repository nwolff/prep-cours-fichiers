mois_et_jours = [
    "janvier", 31,
    "février", 28,
    "mars", 31,
    "avril", 30,
    "mai", 31,
    "juin", 30,
    "juillet", 31,
    "août", 31,
    "septembre", 30,
    "octobre", 31,
    "novembre", 30,
    "décembre", 31,
]


while mois_et_jours:
    mois = mois_et_jours.pop(0)
    jours = mois_et_jours.pop(0)
    print(jours, "jours en", mois)
