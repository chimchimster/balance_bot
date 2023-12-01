async def no_filters(filter_value: str):
    if filter_value == 'Без фильтра':
        return 'любой'
    return filter_value