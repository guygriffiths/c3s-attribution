FROM mambaorg/micromamba:1.5.8

WORKDIR /app
USER root

RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    make \
    wget \
    && apt-get clean

COPY pyenv.yml .

ENV DOCKER_USER=docker \
    CONDA_DIR=/opt/conda \
    MAMBA_DOCKERFILE_ACTIVATE=1 \
    PATH=/opt/conda/bin:$PATH

RUN micromamba create -n c3s-pyenv --file pyenv.yml -y -c conda-forge
RUN micromamba clean --all --yes

# Install Miniconda to get conda-pack working properly
# RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh && \
#     bash miniconda.sh -b -p /opt/conda && \
#     rm miniconda.sh && \
# RUN conda install -n c3s-pyenv conda-pack -c conda-forge

# # Run conda-pack using *real* conda
# RUN /opt/conda/envs/c3s-pyenv/bin/conda-pack -n c3s-pyenv -o /tmp/pyenv.tar


# FROM debian:bullseye-slim

# COPY --from=0 /tmp/pyenv.tar /tmp/pyenv.tar

RUN apt-get update && apt-get install -y \
    fontconfig 
    # && mkdir /venv && cd /venv && tar xf /tmp/pyenv.tar && ./bin/conda-unpack && rm /tmp/pyenv.tar

# ENV PATH="/venv/bin:$PATH" \
#     PYTHONPATH=/git/

# WORKDIR /git

CMD ["micromamba", "activate", "c3s-pyenv"]


