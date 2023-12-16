import random
from string import ascii_letters


async def char_generator(n):
    for _ in range(n):
        yield random.choice(ascii_letters)


async def generate_code_for_restoring_password() -> str:

    code = ''
    async for element in char_generator(random.randint(8, 10)):
        code += element

    return code
