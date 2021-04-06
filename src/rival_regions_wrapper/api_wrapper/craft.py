"""Craft class"""

import re

from bs4 import BeautifulSoup

from rival_regions_wrapper import data_structures

from .abstract_wrapper import AbstractWrapper


class Craft(AbstractWrapper):
    """Wrapper class for crafting"""
    def info(self, item):
        """Get craft"""
        if isinstance(item, str) and item in data_structures.ITEM_KEYS:
            item = data_structures.ITEM_KEYS[item]
        path = 'storage/produce/{}'.format(item)
        response = self.api_wrapper.get(path)
        soup = BeautifulSoup(response, 'html.parser')
        resources = soup.select_one('.storage_produce_exp')
        resource_dict = {
            'cash': 'white',
            'oil': 'oil',
            'ore': 'ore',
            'uranium': 'uranium',
            'diamond': 'diamond',
            'oxygen': 'oxygen',
        }
        resource_cost = {}
        for name, selector in resource_dict.items():
            element = resources.select_one(
                    '.{} .produce_discount'.format(selector)
                )
            if element:
                resource_cost[name] = int(
                    re.sub(r'-|\.', '', element.text)
                )
        craft = {
            'market_price': int(
                re.sub(r'\.|\s\$', '', soup.select('.small .imp')[1].text)
            ),
            'resources': resource_cost
        }
        return craft

    def produce(self, item, amount):
        """Craft item"""
        if isinstance(item, str) and item in data_structures.ITEM_KEYS:
            item = data_structures.ITEM_KEYS[item]
        self.api_wrapper.post('storage/newproduce/{}/{}'.format(item, amount))
        return True
