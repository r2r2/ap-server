###########
# BUILDER #
###########

# pull official base image
FROM python:3.10 as builder

# set work directory
WORKDIR /usr/src/ap-server

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install psycopg2 dependencies
RUN apt-get update \
    && apt-get install netcat -y
RUN apt-get upgrade -y && apt-get install postgresql gcc python3-dev musl-dev -y

# lint
COPY . .

# copy pdm files
COPY ./pyproject.toml .
COPY ./pdm.lock .

#########
# FINAL #
#########

# pull official base image
FROM python:3.10

# create directory for the app user
RUN mkdir -p /home/ap-server

# create the app user
#RUN addgroup -S app && adduser -S app -G app
RUN addgroup --system -gid 1000 app && adduser --system -uid 1000 -gid 1000 app

# create the appropriate directories
ENV HOME=/home/ap-server
ENV APP_HOME=/home/ap-server/web
RUN mkdir $APP_HOME
WORKDIR $APP_HOME

# install dependencies
RUN apt-get update && apt-get install -qq -y build-essential libpq-dev
COPY --from=builder /usr/src/ap-server/pyproject.toml .
COPY --from=builder /usr/src/ap-server/pdm.lock .
RUN python -m pip install -U pdm toml --pre
RUN eval "$(pdm --pep582)"
RUN pdm sync -v

# copy project
COPY . $APP_HOME

# copy entrypoint.sh
COPY ./entrypoint.sh $APP_HOME
COPY asbp_archive.sql /docker-entrypoint-initdb.d/

# chown all the files to the app user
RUN chown -R app:app $APP_HOME

# change to the app user
USER app

# run entrypoint.sh
ENTRYPOINT ["/home/ap-server/web/entrypoint.sh"]
