liste = [17, 89, 56, 23, 10]

# Quand on va faire des pop() sur liste (un peu plus bas dans le code),
# on va consommer la liste. À la fin de l'itération la liste sera vide
# et il sera impossible de la parcourir à nouveau.

# On garde donc une copie avec tous les éléments, on utilisera cette
# copie pour parcourir les éléments la seconde fois.
copie_de_liste = liste.copy()

print("À l'envers :")
while liste:
    element = liste.pop()
    print(element)
    # À décommenter pour voir ce qui se passe :
    # print("Il reste :", liste)

print("À l'endroit :")
while copie_de_liste:
    # Ici, contrairement à avant, on affiche directement,
    # sans passer par une variable « element »
    print(copie_de_liste.pop(0))
    # À décommenter pour voir ce qui se passe :
    # print("Il reste :", copie_de_liste)
