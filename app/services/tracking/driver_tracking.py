import asyncio
from typing import Dict, List

from .location_update import update_driver_locations


class DriverTracker:
    def __init__(self, batch_size: int = 10, batch_interval: int = 5):
        self.location_update_queue: Dict[str, Dict] = {}
        self.batch_size = batch_size
        self.batch_interval = batch_interval
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.process_batch_updates())

    def add_location_update(
        self, driver_id: str, latitude: float, longitude: float, vehicle_type: str
    ):
        self.location_update_queue[driver_id] = {
            "driver_id": driver_id,
            "latitude": latitude,
            "longitude": longitude,
            "vehicle_type": vehicle_type,
        }
        if len(self.location_update_queue) >= self.batch_size:
            self.loop.create_task(self.process_batch_updates())

    def get_batch_updates(self, batch_size: int) -> List[Dict]:
        updates = list(self.location_update_queue.values())[:batch_size]
        for update in updates:
            self.location_update_queue.pop(update["driver_id"], None)
        return updates

    async def process_batch_updates(self):
        while True:
            updates = self.get_batch_updates(self.batch_size)
            if updates:
                await update_driver_locations(updates)
            await asyncio.sleep(self.batch_interval)


driver_tracker = DriverTracker()
