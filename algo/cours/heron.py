n = 2
x = 1
while abs(x ** 2 - n) >= 0.000001:
    x = (x + n / x) / 2
print(x)
