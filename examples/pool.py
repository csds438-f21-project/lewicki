from lewicki import ActorPool


def add_one(v):
    return v + 1


if __name__ == '__main__':
    pool = ActorPool(4)
    print(pool.map(add_one, [1, 2, 3, 5, 6, 7, 8]))
