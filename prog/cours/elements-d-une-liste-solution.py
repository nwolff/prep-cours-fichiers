liste = [42, 17, 89, 56, 23, 10, 95]

# Quand on va faire des pop() sur liste (un peu plus bas dans le code), on va consommer la liste.
# A la fin de l'itération la liste sera vide et il sera impossible de la parcourir à nouveau.

# On garde donc une copie avec tous les éléments, on utilisera cette copie pour énumérer les éléments la seconde fois.
copie_de_liste = liste.copy()

print("A l'envers :")
while liste:
    element = liste.pop()
    print(element, " . Il reste:", liste)  # On affiche ce qui reste juste pour aider à comprendre ce qui se passe

print()
print("A l'endroit :")
while copie_de_liste:
    print(copie_de_liste.pop(0), " . Il reste:", copie_de_liste)  # Ici, contrairement à avant, on print directement, sans passser par une variable "element"
