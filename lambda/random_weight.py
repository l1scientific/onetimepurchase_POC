import random

example_ads = {'ad1': 10, 'ad2': 6, 'ad3': 4, 'ad4': 9}

population = list(example_ads.keys())

weights = list(example_ads.values())

print(population)
print(weights)

def test():
    num0 = 0
    num1 = 0
    num2 = 0
    num3 = 0

    for x in range (10000):
        random_weighted_choice = random.choices(population=population, weights=weights, k=1)
        if random_weighted_choice[0] == 'ad1':
            num0 += 1
        elif random_weighted_choice[0] == 'ad2':
            num1 += 1
        elif random_weighted_choice[0] == 'ad3':
            num2 += 1
        elif random_weighted_choice[0] == 'ad4':
            num3 += 1

    print(f"ad1: {num0}/10000\nad2: {num1}/10000\nad3: {num2}/10000\nad4: {num3}/10000")

test()