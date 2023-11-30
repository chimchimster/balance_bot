from collections import namedtuple


Item = namedtuple('Item', [
            'id',
            'title',
            'description',
            'price',
            'brand_name',
            'image_path',
        ]
    )


AddressItem = namedtuple('Address', [
            'address_country',
            'address_city',
            'address_street',
            'address_apartment',
            'address_phone',
        ]
    )


__all__ = ['Item', 'AddressItem',]
