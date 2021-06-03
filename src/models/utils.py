import yaml
import logging


def read_yaml(yaml_path):
    with open(yaml_path, 'r') as stream:
        try:
            json = yaml.safe_load(stream)
            return json
        except yaml.YAMLError as exc:
            logging.error(exc)
            raise exc

if __name__ == '__main__':
    from pathlib import Path
    read_yaml(Path('../../models/configuration/model_config.yml'))