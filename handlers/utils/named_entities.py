from collections import namedtuple


BoughtItem = namedtuple('Item', [
            'item_title',
            'item_description',
            'item_price',
            'brand_name',
            'image_path',
        ]
    )
