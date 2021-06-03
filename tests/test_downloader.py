from src.data.extraction.openaq_obs import OpenAQDownloader
from src.data.utils import Location
from tests.file_provider import get_remote_file

import tempfile
import filecmp



def test_download_aq():
    lat_dubai = 25.0657
    lon_dubai = 55.17128
    var = 'o3'
    city = 'Dubai'
    country = 'United Arab Emirates'
    station = 'AE001'
    
    filename = f"{country.lower().replace(' ', '-')}/{city.lower()}/" \
               f"{station.lower()}/{var}/{var}_" \
               f"{country.lower().replace(' ', '-')}_{city.lower()}_" \
               f"{station.lower()}_20190601_20210331.nc"

    # Load the data into the temporary directory.     
    tempdir = tempfile.mkdtemp()
    down_path = "/tmp/test_downloading"
    get_remote_file(filename, tempdir)

    loc = Location(station, city, country, lat_dubai, lon_dubai, 1, 1)
    OpenAQDownloader(loc, "/tmp/test_downloading", var).run() 
    
    assert not filecmp.dircmp(down_path, tempdir).diff_files
    assert filecmp.cmp(f"{down_path}/{filename}", f"{tempdir}/{filename}")