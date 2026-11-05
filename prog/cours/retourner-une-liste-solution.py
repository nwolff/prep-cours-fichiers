liste = [17, 89, 56, 23, 10]

liste_inversée = []

while liste:
    e = liste.pop()
    liste_inversée.append(e)
    # pour bien voir comment l'algorithme progresse
    print("element:", e, ", liste restante:", liste, ", liste_inversée:", liste_inversée)

print()
print(liste_inversée)
