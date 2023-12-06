from aiogram.types import ShippingOption, LabeledPrice


shipping_options: list[ShippingOption] = [
    ShippingOption(
        id='1',
        title='Экспресс доставка',
        prices=[
            LabeledPrice(label='СДЭК', amount=100)
        ]
    ),
    ShippingOption(
        id='2',
        title='Обычная доставка',
        prices=[
            LabeledPrice(label='Почта РФ', amount=0)
        ]
    )
]
