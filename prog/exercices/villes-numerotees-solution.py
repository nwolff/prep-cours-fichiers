villes = [
    "Zürich", "Genève", "Bâle", "Lausanne",
    "Berne", "Winterthur", "Lucerne",
    "Saint-Gall", "Lugano", "Bienne",
]

numero = 1

while villes:
    print(numero, villes.pop(0))
    numero = numero + 1
