from dataclasses import dataclass, field

import ee

ee.Initialize()


class ImageCollections:
    def __init__(self, parameter: str) -> None:
        self.parameter = parameter
        if self.parameter not in self._imagecollections:
            raise AttributeError(f'{self.parameter} is not a valid parameter')
        self.imagecollection_title, self.imagecollection_id = self._imagecollections[
            self.parameter]
        self.ee_imagecollection = ee.ImageCollection(self.imagecollection_id)

    @property
    def _imagecollections(self) -> dict[str, str]:
        return {
            'IMD Rainfall': 'users/jaltolwelllabs/IMD/rain',
            'IMD Max Temperature': 'users/jaltolwelllabs/IMD/maxTemp',
            'IMD Min Temperature': 'users/jaltolwelllabs/IMD/minTemp',
            'ETa SSEBop': 'users/jaltolwelllabs/ET/etSSEBop',
            'Dynamic World V1': 'GOOGLE/DYNAMICWORLD/V1'
        }


@dataclass
class Reducers:
    reducer: str
    _reducers: dict[str, ee.Reducer] = field(init=False, repr=False, hash=True, compare=False, metadata=None, default={
        'total': ee.Reducer.sum(),
        'mean': ee.Reducer.mean(),
        'median': ee.Reducer.median(),
        'max': ee.Reducer.max(),
        'min': ee.Reducer.min(),
        'mode': ee.Reducer.mode()
    })

    def __post_init__(self) -> None:
        self.ee_reducer: ee.Reducer = self._reducers[self.reducer.lower()]
