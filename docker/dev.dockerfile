FROM debian:bookworm-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        jq graphviz p7zip-full wget ca-certificates build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Miniconda (arch-aware)
ENV PATH="/opt/conda/bin:${PATH}"
RUN MINICONDA_ARCH=$([ "$(arch)" = aarch64 ] && echo aarch64 || echo x86_64) \
    && wget -O /tmp/miniconda.sh "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-${MINICONDA_ARCH}.sh" \
    && bash /tmp/miniconda.sh -b -p /opt/conda \
    && rm /tmp/miniconda.sh

ENV CONDA_PLUGINS_AUTO_ACCEPT_TOS=yes

RUN conda config --set plugins.auto_accept_tos yes \
    && conda config --set channel_priority strict \
    && conda install -y python=3.11 \
    && conda install -y --override-channels -c conda-forge -c bioconda bcalm minimap2 \
    && conda clean -afy

# Boost headers (required by custom backend)
RUN wget -O /tmp/boost.7z https://sourceforge.net/projects/boost/files/latest/download \
    && cd /usr/local/include && p7zip -d /tmp/boost.7z \
    && rm -f /tmp/boost.7z

WORKDIR /opt/project

COPY requirements.txt requirements.txt
COPY requirements-dev.txt requirements-dev.txt

RUN pip3 install --upgrade pip \
    && pip3 install --no-cache-dir -r requirements.txt \
    && pip3 install --no-cache-dir -r requirements-dev.txt 

RUN --mount=type=secret,id=gitlab_token,env=GITLAB_API_TOKEN \
    pip install multiverse-singularity-optimization-backend \
    --index-url https://gitlab-ci-token:${GITLAB_API_TOKEN}@gitlab.com/api/v4/projects/43016030/packages/pypi/simple
COPY . /opt/project

ENV PYTHONPATH=/opt/project

RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /opt/project /opt/conda
USER appuser