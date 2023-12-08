from typing import Optional


async def no_filters(filter_value: str):
    if filter_value == 'Без фильтра':
        return 'любой'
    return filter_value


async def convert_sex(gender: Optional[str]) -> Optional[str]:

    if gender is not None:
        gender = gender.split('.')[-1]
        if gender.startswith('male'):
            return 'М'
        elif gender.startswith('female'):
            return 'Ж'

    return gender

