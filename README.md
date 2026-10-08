# BFMC - Brain Project

The project contains all the provided code for the RPi, more precisely:
- Firmware for communicating with the Nucleo and control the robot movements (Speed with constant current consumption, speed with constant speed, braking, moving and steering);
- Firmware for gathering data from the sensors (IMU and Camera);
- API's for communicating with the environmental servers at Bosch location;
- Simulated servers for the API's.

## LocSys API key

`setup.cmd` automatically copies `.env.example` to `.env` if `.env` does not
already exist, preserving any existing configuration. To create it manually:

```sh
cp .env.example .env
```

In `.env`, replace `YOUR_API_KEY` in `TRAFFIC_DEVICE_TOKEN=...` with your LocSys API key.

## Develop on PC with Docker

Use Docker to start the Brain and dashboard in development mode on your PC:

```sh
docker compose up --build
```

Open the dashboard at [http://localhost:4200](http://localhost:4200). Press `Ctrl+C` to stop, or run `docker compose down`.

The Brain container automatically starts with `--dev`, as set in the Dockerfile. To disable dev mode, remove `--dev` from the Dockerfile's `CMD` and rebuild with `docker compose up --build`.

## The documentation is available in more details here:
[Documentation](https://bosch-future-mobility-challenge-documentation.readthedocs-hosted.com/)
