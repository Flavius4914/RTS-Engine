from typing import Dict
from enum import Enum

class ResourceType(Enum):
    GOLD = "gold"
    WOOD = "wood"
    STONE = "stone"
    FOOD = "food"

class ResourceManager:
    def __init__(self):
        self.resources: Dict[ResourceType, int] = {
            ResourceType.GOLD: 1000,
            ResourceType.WOOD: 500,
            ResourceType.STONE: 500,
            ResourceType.FOOD: 1000
        }
        
        self.production_rates: Dict[ResourceType, float] = {
            ResourceType.GOLD: 0,
            ResourceType.WOOD: 0,
            ResourceType.STONE: 0,
            ResourceType.FOOD: 0
        }
        
    def add_resource(self, resource_type: ResourceType, amount: int):
        self.resources[resource_type] += amount
        
    def remove_resource(self, resource_type: ResourceType, amount: int) -> bool:
        if self.resources[resource_type] >= amount:
            self.resources[resource_type] -= amount
            return True
        return False
        
    def get_resource(self, resource_type: ResourceType) -> int:
        return self.resources[resource_type]
        
    def set_production_rate(self, resource_type: ResourceType, rate: float):
        self.production_rates[resource_type] = rate
        
    def update(self):
        # Update resources based on production rates
        for resource_type, rate in self.production_rates.items():
            if rate > 0:
                self.add_resource(resource_type, int(rate))
                
    def can_afford(self, costs: Dict[ResourceType, int]) -> bool:
        for resource_type, cost in costs.items():
            if self.resources[resource_type] < cost:
                return False
        return True
        
    def pay_costs(self, costs: Dict[ResourceType, int]) -> bool:
        if self.can_afford(costs):
            for resource_type, cost in costs.items():
                self.remove_resource(resource_type, cost)
            return True
        return False 