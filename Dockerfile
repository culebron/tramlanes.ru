FROM python:3.8
MAINTAINER Dmitri Lebedev <dl@peshemove.org>

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
	build-essential \
	libspatialindex-dev \
	libgdal-dev \
	libgeos-dev \
	locales \
	python3-pip \
	python3-dev \
	python3.8-dev \
	python3-setuptools \
	cython3 \
	proj-bin \
	unzip \
	wget

RUN pip3 install wheel

RUN ldconfig && \
	pip3 install -U \
		argh \
		fastkml \
		geojson \
		geopandas \
		Jinja2 \
		lxml \
		polyline \
		psycopg2 \
		requests_cache \
		rtree \
		pyproj\<3.0

RUN ldconfig && pip3 install -U ipdb

RUN mkdir /calculator
COPY calculator /calculator

RUN locale-gen en_US.UTF-8o
ENV LANG='en_US.UTF-8' LANGUAGE='en_US:en' LC_ALL='en_US.UTF-8'

RUN echo "cd calculator && python3 main.py" > /make-rating.sh
