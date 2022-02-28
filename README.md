![Python 3.8](https://img.shields.io/badge/Python-3.9-blue.svg)

# GBC Explorer Prometheus exporter
Prometheus exporter for various metrics about GBC explorer (https://beacon.gnosischain.com)


### Configuration
#### Validators list
- Create a file called `validators.json`.
- Fill that file defining the validators list to generate Prometheus metrics  (use `validators.json.example` as a reference).

#### ENV VARIABLES

**NOTE:** The exporter fetches information from gbc-explorer on every scrape, therefore having a too short scrape interval can produce rate limits.

| VARIABLE                 | Description                                                            | Default |
|--------------------------|------------------------------------------------------------------------|---------|
| EXPORTER_PORT            | Port where the exporter will expose metrics.                           | 9877    |
| POLLING_INTERVAL_SECONDS | Frequency to fetch the information from https://beacon.gnosischain.com | 600     |

### RUN

#### Bash
```bash
python main.py
```

#### Docker

```bash
docker pull raulio/gbc-explorer-prometheus-exporter:main
docker run --rm -p 9877:9877 raulio/gbc-explorer-prometheus-exporter:main
```

#### Docker-compose

```bash
docker-compose up -d .
```

### Metrics

| Name                    | Type       | Help                                |
|-------------------------|------------|-------------------------------------|
| validator_effectiveness | gauge      | Validator attestation effectiveness |

Resources:
- GBC explorer API: https://github.com/gnosischain/gbc-explorer/blob/master/cmd/explorer/main.go
- Prometheus exporter example: https://trstringer.com/quick-and-easy-prometheus-exporter/