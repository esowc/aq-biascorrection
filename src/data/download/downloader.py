from pathlib import Path
from dataclasses import dataclass
from typing import Dict
from math import sin, cos, sqrt, atan2, radians

import pandas as pd
import numpy as np
import os
import openaq


tol = 1e-3


@dataclass
class Location:
    """
    Class to define specific location of interest
    with its correspondent attributes
    """
    location_id: str
    city: str
    country: str
    latitude: float
    longitude: float
    distance: float = 0.0

    def __str__(self):
        return f'Location(location_id={self.location_id}, ' \
               f'city={self.city}, country={self.country}, ' \
               f'latitude={self.latitude}, longitude={self.longitude}, ' \
               f'with a distance to the nearest OpenAQ ' \
               f'station of {self.distance} km)'
    

class OpenAQDownloader:
    """
    Class to download data from the OpenAQ platform
    for a specific location of interest
    """
    def __init__(
            self,
            location: Location,
            output_dir: Path,
            variable: str,
            time_range: Dict[str, str] = None
    ):
        self.api = openaq.OpenAQ()
        if time_range is None:
            time_range = dict(start='2019-01-01', end='2021-03-31')
        self.location = location
        self.time_range = time_range
        self.output_dir = output_dir
        if variable in ['o3', 'no2', 'so2', 'pm10', 'pm25']:
            self.variable = variable
        else:
            raise NotImplementedError(f"The variable {variable} do"
                                      f" not correspond to any known one")

    def run(self) -> str:
        """
        Main method to download data from OpenAQ.
        """
        output_path_data = self.get_output_path()
        output_path_metadata = self.get_output_path(is_metadata=True)
        station = self.get_closest_station_to_location()
        data = self.get_data(station)
        self.save_data_and_metadata(data,
                                    output_path_data,
                                    output_path_metadata)
        return f"Data has been correctly downloaded in {str(output_path_data)}"

    def get_closest_station_to_location(self) -> pd.Series:
        """
        Method to check which station is closer to the point of interest.
        """
        stations = self.get_stations_in_city()
        # First of all, we check if any of the stations match the
        # exact location of the point of interest
        if len(stations[stations['is_in_location']]):
            station = stations[stations['is_in_location']].iloc[0]
        # If not, we calculate the distances to that point
        else:
            distances = []
            for station in stations.iterrows():
                station = station[1]
                distance = get_distance_between_two_points_on_earth(
                    station['coordinates.latitude'],
                    self.location.latitude,
                    station['coordinates.longitude'],
                    self.location.longitude
                )
                distances.append(distance)
            stations['distance'] = distances
            station = stations.iloc[stations['distance'].idxmax()]
            self.location.distance = round(station.distance, 2)
        self.check_variable_in_station(station)
        return station

    def get_stations_in_city(self) -> pd.DataFrame:
        """
        Method to check whether there are stations or not in the city
        where the location of interest is located.
        """
        coord_labels = ['coordinates.latitude', 'coordinates.longitude']
        stations = self.api.locations(city=self.location.city, df=True)
        is_in_location = []
        for station in stations.iterrows():
            station_loc = station[1][coord_labels].astype(float)
            loc = np.array([self.location.latitude, self.location.longitude])
            if not np.allclose(station_loc, loc, atol=tol):
                print('The OpenAQ station coordinates do not match'
                      ' with the location of interest coordinates')
                is_in_location.append(False)
            else:
                is_in_location.append(True)
        stations['is_in_location'] = is_in_location
        return stations

    def get_output_path(self, is_metadata: bool = False):
        """
        Method to get the output paths where the data and metadata are stored.
        """
        city = self.location.city.lower()
        station_id = self.location.location_id.lower()
        variable = self.variable
        time_range = '_'.join(self.time_range.values()).replace('-', '')
        ext = '_metadata.csv' if is_metadata else '.csv'
        output_path = Path(
            self.output_dir,
            city,
            station_id,
            f"{variable}_{city}_{station_id}_{time_range}{ext}"
        )
        return output_path

    def get_data(self, station: pd.Series) -> pd.DataFrame:
        """
        This methods retrieves data from the OpenAQ platform in pd.DataFrame 
        format. The specific self.time_range, given by the user, is selected 
        afterwards. It also takes out every value under 0 (which are considered 
        as NaN).
        """
        data = self.api.measurements(
            city=station['city'],
            location=station['location'],
            parameter=self.variable,
            limit=100000,
            df=True)
        data_in_time = data[
            (data['date.utc'] > self.time_range['start']) & 
            (data['date.utc'] <= self.time_range['end'])
        ]
        # The date.utc columns is set as index in order to have always the
        # same time reference
        data_in_time.reset_index(inplace=True)
        data_in_time.set_index('date.utc', inplace=True)
        data_in_time = data_in_time[data_in_time['value'] >= 0]
        return data_in_time

    def check_variable_in_station(self, station: pd.Series):
        """
        This method checks whether the stations has available data for the
        variable of interest
        """
        if self.variable not in station['parameters']:
            raise Exception('The variable intended to download is not'
                            ' available for the nearest / exact location')

    def save_data_and_metadata(
            self,
            data: pd.DataFrame,
            output_path_data: Path,
            output_path_metadata: Path
    ):
        """
        This function saves the data (.csv format) or the metadata (.txt format)
        """
        # Directory initialization if they do not exist
        if not output_path_data.parent.exists():
            os.makedirs(output_path_data.parent, exist_ok=True)
        if not output_path_metadata.parent.exists():
            os.makedirs(output_path_metadata.parent, exist_ok=True)
        # Store data in [datetime, value] format
        data['value'].to_csv(output_path_data)
        # Store metadata in [variable, units,
        dict_metadata = {
            'variable': self.variable,
            'units': np.unique(data['unit'].values),
            'latitude_openaq': np.unique(data['coordinates.latitude'].values),
            'longitude_openaq': np.unique(data['coordinates.longitude'].values),
            'total_values': len(data),
            'initial_time': data.index.values[0],
            'final_time': data.index.values[-1],
            'location_obj': str(self.location)
        }
        metadata = pd.DataFrame(dict_metadata)
        metadata.to_csv(output_path_metadata)


def get_distance_between_two_points_on_earth(
        lat1: float,
        lat2: float,
        lon1: float,
        lon2: float
):
    """
    Function to calculate the distance between an station from OpenAQ
    and the coordinates of interest. Use Haversine distance.
    """
    R = 6373.0
    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c
    return distance
