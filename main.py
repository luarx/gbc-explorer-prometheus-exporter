"""Application exporter"""

import os
import time
from prometheus_client import start_http_server, Gauge
import requests
import json
import logging
from pathlib import Path

# Read log level as environment variable (by default INFO)
LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
assert (LOGLEVEL in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']), 'LOGLEVEL is not valid'
# Configure logs format
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s',
    level=LOGLEVEL)


def divide_list_in_chunks(data, chunk_size):
    """
    Divide list in chunks
    :param data: list
    :param chunk_size:
    :return:
    """

    # looping till length list
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]


class AppMetrics:
    """
    Representation of Prometheus metrics and loop to fetch and transform
    application metrics into Prometheus metrics.
    """

    def __init__(self, polling_interval_seconds=5):
        self.polling_interval_seconds = polling_interval_seconds
        self.validators = self.get_validators_list()

        if not self.validators:
            logging.error(f"Validators list is empty (no validator.json or validator_deposit_address.json file)")
            # When validators list is empty, does not make sense to continue
            exit(1)

        # Prometheus metrics to collect
        self.validator_effectiveness = Gauge("validator_effectiveness", "Validator efectiviness", ['pubkey', 'validator_index'])

    def run_metrics_loop(self):
        """Metrics fetching loop"""

        while True:
            # Split validator list in chunks as there could be a rate limit
            # Max 100 https://github.com/gobitfly/eth2-beaconchain-explorer/blob/94ce05e10766196123cb282a557ed07f70339408/handlers/api.go#L919
            validator_chunks = divide_list_in_chunks(self.validators, 100)
            for validator_chunk in validator_chunks:
                self.fetch_and_set_validators_effectiveness(validators=validator_chunk)

            time.sleep(self.polling_interval_seconds)

    def get_validators_list(self):
        validators_ids_file = "validators.json"
        validators_deposit_addresses_file = "validator_deposit_addresses.json"
        # Use a set so that we can discard duplicates between
        # validators.json and the ones from validators_deposit_addresses.json
        validators_set = set()

        # Validators list: It could be a list of IDs, pub keys or both
        if Path(validators_ids_file).exists():
            logging.info(f"Reading validators.json file...")
            with open(validators_ids_file, "r") as validators_file:
                validators = json.load(validators_file)

                logging.info(f"Validators list of indexex/pubkeys: {validators}")
                # Add validators to validators_set
                validators_set.update(validators)
        else:
            logging.info(f"Not reading validators.json file as it does not exist")

        if Path(validators_deposit_addresses_file).exists():
            logging.info(f"Reading validator_deposit_addresses.json file...")
            with open(validators_deposit_addresses_file, "r") as deposit_addresses_file:
                addresses = json.load(deposit_addresses_file)

                logging.info(f"Deposit addresses: {addresses}")

                for deposit_address in addresses:
                    resp = requests.get(url=f"https://beacon.gnosischain.com/api/v1/validator/eth1/{deposit_address}",
                                        timeout=5)

                    response_json = resp.json()

                    # response_json["data"] can be:
                    # - List. If many validators have been created from the same deposit address
                    # - Dict. If only 1 validator has been created using the deposit address
                    response_data = response_json["data"]
                    if type(response_data) == list:
                        for validator in response_data:
                            public_key = validator["publickey"]
                            logging.info(f"Validator public key {public_key}")
                            validators_set.add(public_key)
                    else:
                        public_key = response_data["publickey"]
                        logging.info(f"Validator public key {public_key}")
                        validators_set.add(public_key)
        else:
            logging.info(f"Not reading validator_deposit_addresses.json file as it does not exist")

        return list(validators_set)

    def set_validator_effectiveness(self, effectiveness):
        """
        Set validator efectiviness
        :param effectiveness:
        :return:
        """

        # Update Prometheus metrics with application metrics
        self.validator_effectiveness. \
            labels(pubkey=effectiveness["pubkey"],
                   validator_index=effectiveness["validatorindex"]). \
            set(effectiveness["attestation_effectiveness"])

    def fetch_and_set_validators_effectiveness(self, validators):
        """
        Get metrics from beacon.gnosischain.com and refresh Prometheus metrics with
        new values.
        """

        try:
            # Convert validator list to a string separated by commas
            validators_serialized = ",".join(validators)
            resp = requests.get(url=f"https://beacon.gnosischain.com/api/v1/validator/{validators_serialized}/attestationeffectiveness",
                                timeout=5)
        except Exception as exception:
            # Unexpected exception when requesting, but show must go on because in the next loop this request
            # could work if it is a temporal issue.
            logging.error(f"Exception when requesting validators effectiveness. "
                          f"Exception: {exception} - Validators: {validators}")
            return

        response_json = resp.json()

        # Common situation of a response that does not contain "data":
        # {'message': 'API rate limit exceeded'}
        if "data" not in response_json:
            logging.error(f"Validator effectiveness response does not contain `data`. "
                          f"Response: {response_json}")
            # When there is not a valid response, skip next actions
            return

        response_data = response_json["data"]
        # Set each validator effectiveness as Prometheus metric
        # response_json["data"] can be:
        # - List. If many validators info have been requested
        # - Dict. If only 1 validator info has been requested
        if type(response_data) == list:
            for effectiveness in response_data:
                logging.info(f"Validator effectiveness {effectiveness}")
                # Update Prometheus metrics with application metrics
                self.set_validator_effectiveness(effectiveness)
        else:
            effectiveness = response_data
            logging.info(f"Validator effectiveness {response_data}")
            # Update Prometheus metrics with application metrics
            self.set_validator_effectiveness(effectiveness)


def main():
    """Main entry point"""

    polling_interval_seconds = int(os.getenv("POLLING_INTERVAL_SECONDS", "600"))
    exporter_port = int(os.getenv("EXPORTER_PORT", "9877"))

    app_metrics = AppMetrics(
        polling_interval_seconds=polling_interval_seconds
    )

    logging.info(f"Starting Prometheus server - Port: {exporter_port}")
    start_http_server(exporter_port)

    logging.info(f"Run metrics loop - Polling interval: {polling_interval_seconds} seconds")
    app_metrics.run_metrics_loop()


if __name__ == "__main__":
    main()
