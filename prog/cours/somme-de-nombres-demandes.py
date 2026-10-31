s = 0
n = int(input("Entrez un nombre (0 pour terminer) "))
while n != 0:
    s = s + n
    print("Somme actuelle: ", s) # Pour aider à comprendre comment s accumule
    n = int(input("Entrez un nombre (0 pour terminer) "))
print("Résultat :", s)