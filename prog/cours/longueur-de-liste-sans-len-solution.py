liste = [17, 89, 56, 23, 10]

longueur = 0

while liste:
    longueur = longueur + 1
    liste.pop()
    print("longueur:", longueur, ", liste restante :", liste)

print()
print("Longueur de la liste : ", longueur)
