########
#
# Il y a plusieurs manières de résoudre ce problème.
# En voici deux
#
#########


####### Solution a

n = int(input("donnez moi un nombre : "))

somme = 0
i = 1
while i <= n:
    somme = somme + i
    i = i + 1

print(somme)


####### Solution b
# Un utilise l'idée que la somme
#  1, 2, 3, 4, 5, 6, ...... n est égale à
#  n, n-1, ............     3, 2, 1
#
# On calcule donc la somme en partant de n et en descendant jusqu'à 1

n = int(input("donnez moi un nombre : "))

somme = 0
while n >= 1:
    somme = somme + n
    n = n - 1

print(somme)
