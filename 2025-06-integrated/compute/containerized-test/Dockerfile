# https://github.com/globus/globus-compute/blob/main/endpoint_dev.Dockerfile

FROM python:3.12.10-slim-bullseye

#RUN pip install --no-cache-dir -U pip && \
#    pip --no-cache-dir install globus_sdk==3.56.0 globus_compute_sdk==3.7.0


# Josh says compute containers need endpoint: https://groups.google.com/a/globus.org/g/discuss/c/0Glqx_7pj7Y
# .....+ any task specific dependencies
RUN pip install --no-cache-dir -U pip && \
    pip --no-cache-dir install globus-compute-endpoint==3.7.0

# TODO: Improve container image, building on this base