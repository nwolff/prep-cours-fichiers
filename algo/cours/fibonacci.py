n = 10
a = 1
b = 1
etapes = 0
while etapes < n - 2:
    somme = a + b
    a = b
    b = somme
    etapes = etapes + 1
print(b)
