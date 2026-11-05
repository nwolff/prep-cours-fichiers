somme = 0
compte = 0

n = int(input("Entrez un nombre (0 pour terminer) "))

while n != 0:
    somme = somme + n
    compte = compte + 1
    n = int(input("Entrez un nombre (0 pour terminer) "))

print("Moyenne :", somme / compte)
